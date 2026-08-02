#!/usr/bin/env python3
"""生成画像を Shopify の「コンテンツ > ファイル」へアップロードする。

商品画像は seed-products.py が商品に紐づけて登録するが、ヒーローや手順カットは
商品ではなくテーマ設定から参照するため、ファイルとして単体で上げる必要がある。
テーマ設定の image_picker は `shopify://shop_images/<ファイル名>` で解決するので、
アップロード後に表示されるその参照文字列をそのまま index.json に書ける。

使い方:
    python3 scripts/upload-files.py                    # 既定の対象をすべて
    python3 scripts/upload-files.py step-3-wait.png    # 個別に上げ直す
    python3 scripts/upload-files.py --dry-run

同名ファイルが既にある場合、Shopify は上書きせず別名（末尾に連番）で登録する。
上げ直すときは管理画面で古い方を消すこと。消さないと index.json の参照が
古い画像を指したままになる。
"""

from __future__ import annotations

import json
import mimetypes
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

STORE = "chanoka-demo.myshopify.com"
API_VERSION = "2026-07"
GRAPHQL_URL = f"https://{STORE}/admin/api/{API_VERSION}/graphql.json"

REPO_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = REPO_ROOT / "scripts" / "output"
TOKEN_FILE = Path.home() / ".claude" / "portfolio" / "shopify-token"

# (ファイル名, alt)。altはテーマ側で上書きできるが、素のままでも読み上げが成立する値を入れる
TARGETS = [
    ("hero-main.png", "湯呑に注がれた煎茶"),
    ("hero-field.png", "朝もやのかかった茶畑"),
    ("step-1-measure.png", "茶さじで茶葉を量る"),
    ("step-2-cool.png", "湯冷ましにお湯を注ぐ"),
    ("step-3-wait.png", "ふたをした急須と砂時計"),
    ("step-4-pour.png", "2つの湯呑に均等に注ぎ分ける"),
    ("lifestyle-kyusu.png", "急須から湯呑に緑茶を注ぐ"),
    ("lifestyle-tea-field.png", "段々に連なる茶畑"),
    ("lifestyle-table.png", "緑茶と和菓子を並べた食卓"),
]

STAGED_UPLOAD = """
mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets { url resourceUrl parameters { name value } }
    userErrors { field message }
  }
}
"""

FILE_CREATE = """
mutation fileCreate($files: [FileCreateInput!]!) {
  fileCreate(files: $files) {
    files {
      alt
      fileStatus
      ... on MediaImage { id image { url } }
    }
    userErrors { field message }
  }
}
"""


def token() -> str:
    if not TOKEN_FILE.is_file():
        sys.exit(f"トークンがありません: {TOKEN_FILE}")
    return TOKEN_FILE.read_text(encoding="utf-8").strip()


def graphql(query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={"X-Shopify-Access-Token": token(), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as error:
        sys.exit(f"HTTPエラー {error.code}: {error.read().decode('utf-8', 'replace')}")

    # GraphQL は HTTP 200 でもエラーを返すため、必ず中身を見る
    if "errors" in payload:
        sys.exit(f"GraphQLエラー: {json.dumps(payload['errors'], ensure_ascii=False, indent=2)}")
    return payload["data"]


def check_user_errors(result: dict, key: str) -> dict:
    errors = result[key].get("userErrors") or []
    if errors:
        sys.exit(f"{key} でエラー: {json.dumps(errors, ensure_ascii=False, indent=2)}")
    return result[key]


def upload(path: Path) -> str:
    """staged upload に画像を送り、fileCreate に渡せる resourceUrl を返す。"""
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = check_user_errors(
        graphql(STAGED_UPLOAD, {
            "input": [{
                "filename": path.name,
                "mimeType": mime,
                "httpMethod": "POST",
                "resource": "FILE",
                "fileSize": str(path.stat().st_size),
            }]
        }),
        "stagedUploadsCreate",
    )
    target = data["stagedTargets"][0]

    boundary = uuid.uuid4().hex
    buffer = bytearray()
    # パラメータはShopifyが指定した順序でファイルより前に置く必要がある
    for parameter in target["parameters"]:
        buffer += f"--{boundary}\r\n".encode()
        buffer += f'Content-Disposition: form-data; name="{parameter["name"]}"\r\n\r\n'.encode()
        buffer += parameter["value"].encode() + b"\r\n"
    buffer += f"--{boundary}\r\n".encode()
    buffer += f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode()
    buffer += f"Content-Type: {mime}\r\n\r\n".encode()
    buffer += path.read_bytes() + b"\r\n"
    buffer += f"--{boundary}--\r\n".encode()

    request = urllib.request.Request(
        target["url"],
        data=bytes(buffer),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        urllib.request.urlopen(request, timeout=300).read()
    except urllib.error.HTTPError as error:
        sys.exit(f"アップロード失敗 {error.code}: {error.read().decode('utf-8', 'replace')}")

    return target["resourceUrl"]


def main() -> None:
    arguments = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv

    only = set(arguments)
    targets = [t for t in TARGETS if not only or t[0] in only]
    if only and not targets:
        sys.exit(f"該当なし。指定できるのは: {', '.join(name for name, _ in TARGETS)}")

    for filename, alt in targets:
        path = IMAGE_DIR / filename
        if not path.is_file():
            sys.exit(f"画像がありません: {path}")

        print(f"- {filename}")
        if dry_run:
            continue

        result = check_user_errors(
            graphql(FILE_CREATE, {
                "files": [{
                    "originalSource": upload(path),
                    "contentType": "IMAGE",
                    "alt": alt,
                }]
            }),
            "fileCreate",
        )
        created = result["files"][0]
        # 登録直後は fileStatus が UPLOADED で、処理が終わると READY になる。
        # image.url はまだ null のことがあるが、参照は shopify://shop_images/<名前> で足りる
        print(f"    {created['fileStatus']} / shopify://shop_images/{filename}")

    print("完了")


if __name__ == "__main__":
    main()
