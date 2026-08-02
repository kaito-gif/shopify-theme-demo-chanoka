#!/usr/bin/env python3
"""chanoka（架空の日本茶D2C）のデモ商品を Shopify Admin API で登録する。

生成済みの画像（scripts/output/）をアップロードし、商品6点を作る。
画面から手で登録してもよいが、作り直しのたびに手作業になるためスクリプトにした。

使い方:
    python3 scripts/seed-products.py           # 登録
    python3 scripts/seed-products.py --dry-run # 送信内容だけ確認

トークンは ~/.claude/portfolio/shopify-token を読む（git管理外）。

画像は staged upload 経由で渡す。REST の画像アップロードは扱いが楽だが、
Admin API の商品系エンドポイントは GraphQL が正であり、REST は非推奨のため使わない。
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

# (画像ファイル名, 商品名, 価格, 説明, 産地, 味わい, カフェイン, おすすめの飲み方)
PRODUCTS = [
    ("product-sencha.png", "煎茶 やぶきた", "1200",
     "毎日の一杯に。すっきりとした渋みと後に残る甘みのバランスが取れた、いちばん基本の煎茶です。",
     "静岡・牧之原", "すっきり", "やや多い", "70〜80℃で60秒"),
    ("product-fukamushi.png", "深蒸し煎茶", "1400",
     "長めに蒸すことで渋みがやわらぎ、濃い緑の水色に。粉が多く出るため、短時間でもしっかり味が出ます。",
     "静岡・掛川", "コクと甘み", "やや多い", "70℃で40秒"),
    ("product-gyokuro.png", "玉露", "2800",
     "覆いをかけて育てた茶葉ならではの、厚みのある旨み。少量のぬるま湯でゆっくり淹れてください。",
     "京都・宇治", "旨みが濃い", "多い", "50〜60℃で120秒"),
    ("product-hojicha.png", "ほうじ茶", "900",
     "強めに焙じた香ばしい一杯。カフェインが少なく、食後や就寝前にも向きます。",
     "静岡・掛川", "香ばしい", "少なめ", "95℃で30秒"),
    ("product-genmaicha.png", "玄米茶", "1000",
     "炒った玄米の香りと緑茶の軽やかさ。食事に合わせやすく、飲み飽きしません。",
     "静岡・牧之原", "軽やか", "少なめ", "90℃で30秒"),
    ("product-matcha.png", "抹茶", "2400",
     "石臼で挽いた粉末茶。そのまま点てても、ラテや菓子づくりにも使えます。",
     "京都・宇治", "濃厚", "多い", "80℃で点てる"),
]


def image_path(filename: str) -> Path:
    """アップロードする画像を選ぶ。

    brand-packages.py がブランド名を刷った版を branded/ に出す。ラベルが無地のままの
    原本を上げると店頭の見え方が戻ってしまうため、刷った版があれば必ずそちらを使う。
    """
    branded = IMAGE_DIR / "branded" / filename
    return branded if branded.is_file() else IMAGE_DIR / filename


def caffeine_tag(caffeine: str) -> str:
    """カフェイン量の表記をタグに変換する。

    自動コレクションの条件と絞り込みに使う。日本語のタグはURLに出るとパーセント
    エンコードされて読めなくなるため、ローマ字に寄せる。seed-collections.py も
    この関数を読むので、定義を増やすときは両方の挙動を確認すること。
    """
    return {"少なめ": "caffeine-low", "やや多い": "caffeine-medium", "多い": "caffeine-high"}[caffeine]


def token() -> str:
    if not TOKEN_FILE.is_file():
        sys.exit(f"トークンがありません: {TOKEN_FILE}")
    return TOKEN_FILE.read_text(encoding="utf-8").strip()


def graphql(query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={
            "X-Shopify-Access-Token": token(),
            "Content-Type": "application/json",
        },
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


STAGED_UPLOAD = """
mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets { url resourceUrl parameters { name value } }
    userErrors { field message }
  }
}
"""

PRODUCT_SET = """
mutation productSet($input: ProductSetInput!) {
  productSet(synchronous: true, input: $input) {
    product { id title handle onlineStoreUrl }
    userErrors { field message }
  }
}
"""


def check_user_errors(result: dict, key: str) -> dict:
    errors = result[key].get("userErrors") or []
    if errors:
        sys.exit(f"{key} でエラー: {json.dumps(errors, ensure_ascii=False, indent=2)}")
    return result[key]


def upload_image(path: Path) -> str:
    """staged upload に画像を送り、productSet に渡せる resourceUrl を返す。"""
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = check_user_errors(
        graphql(STAGED_UPLOAD, {
            "input": [{
                "filename": path.name,
                "mimeType": mime,
                "httpMethod": "POST",
                "resource": "IMAGE",
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
        sys.exit(f"画像アップロード失敗 {error.code}: {error.read().decode('utf-8', 'replace')}")

    return target["resourceUrl"]


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    for filename, title, price, description, origin, taste, caffeine, brewing in PRODUCTS:
        path = image_path(filename)
        if not path.is_file():
            sys.exit(f"画像がありません: {path}")

        print(f"- {title}")
        if dry_run:
            print(f"    価格 {price} / 画像 {path.relative_to(REPO_ROOT)}")
            continue

        resource_url = upload_image(path)

        body = (
            f"<p>{description}</p>"
            "<ul>"
            f"<li>産地: {origin}</li>"
            f"<li>味わい: {taste}</li>"
            f"<li>カフェイン: {caffeine}</li>"
            f"<li>おすすめの淹れ方: {brewing}</li>"
            "</ul>"
            "<p><small>※ このストアはポートフォリオ用のデモです。架空のブランドで、"
            "商品画像はAIで生成しています。</small></p>"
        )

        result = check_user_errors(
            graphql(PRODUCT_SET, {
                "input": {
                    "title": title,
                    "descriptionHtml": body,
                    "productType": "日本茶",
                    "vendor": "chanoka",
                    # productSet はタグを差し替えるため、ここから外すと
                    # カフェイン控えめの自動コレクションが空になる
                    "tags": ["demo", "chanoka", caffeine_tag(caffeine)],
                    "status": "ACTIVE",
                    "files": [{"originalSource": resource_url, "contentType": "IMAGE", "alt": title}],
                    "productOptions": [{
                        "name": "内容量",
                        "values": [{"name": "100g"}],
                    }],
                    "variants": [{
                        "price": price,
                        "optionValues": [{"optionName": "内容量", "name": "100g"}],
                    }],
                }
            }),
            "productSet",
        )
        print(f"    登録: {result['product']['handle']}")

    print("完了")


if __name__ == "__main__":
    main()
