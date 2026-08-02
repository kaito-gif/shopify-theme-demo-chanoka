#!/usr/bin/env python3
"""コレクションを整備する。タグ付け → コレクション作成 → 公開 → 既定コレクション削除。

ストア作成時に Shopify が自動生成する「Home page」しかコレクションが無い状態だと、
メニューの遷移先が /collections/all（疑似コレクション）になる。疑似コレクションは
説明文・画像・SEO・手動の並び順を持てないため、テーマ側で用意している
「コレクションの説明を表示」などの設定が空回りする。実体のあるコレクションを作る。

自動コレクション（条件で商品が入る方式）はタグを条件にするため、先に商品へ
カフェイン量のタグを付ける。タグの定義は seed-products.py に持たせて一本化した。

使い方:
    python3 scripts/seed-collections.py           # 実行
    python3 scripts/seed-collections.py --dry-run # 送信内容だけ確認

何度実行しても同じ結果になるようにしてある。既にあるものは作り直さない。
"""

from __future__ import annotations

import importlib.util
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

STORE = "chanoka-demo.myshopify.com"
API_VERSION = "2026-07"
GRAPHQL_URL = f"https://{STORE}/admin/api/{API_VERSION}/graphql.json"

TOKEN_FILE = Path.home() / ".claude" / "portfolio" / "shopify-token"

# 自動生成されたまま使われていないコレクション。メニューもテーマも参照していない
DEFAULT_COLLECTION_HANDLE = "frontpage"

TEA_HANDLE = "tea"
LOW_CAFFEINE_HANDLE = "low-caffeine"
LOW_CAFFEINE_TAG = "caffeine-low"


def seed_products_module():
    """seed-products.py を読み込む。

    商品一覧とタグの変換規則をあちこちに書くと片方だけ直して食い違うため、定義は
    商品側の1か所に置き、ここから借りる。ファイル名にハイフンが入っていて通常の
    import ができないので spec 経由で読み込む。
    """
    path = Path(__file__).with_name("seed-products.py")
    spec = importlib.util.spec_from_file_location("seed_products", path)
    if spec is None or spec.loader is None:
        sys.exit(f"読み込めません: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


PRODUCTS_QUERY = """
query products {
  products(first: 50) {
    nodes { id title handle tags }
  }
}
"""

COLLECTION_BY_HANDLE = """
query collectionByHandle($handle: String!) {
  collectionByHandle(handle: $handle) { id title handle }
}
"""

PUBLICATIONS_QUERY = """
query publications {
  publications(first: 20) { nodes { id name } }
}
"""

TAGS_ADD = """
mutation tagsAdd($id: ID!, $tags: [String!]!) {
  tagsAdd(id: $id, tags: $tags) {
    userErrors { field message }
  }
}
"""

COLLECTION_CREATE = """
mutation collectionCreate($collection: CollectionCreateInput!) {
  collectionCreate(collection: $collection) {
    collection { id title handle }
    userErrors { field message }
  }
}
"""

COLLECTION_DELETE = """
mutation collectionDelete($input: CollectionDeleteInput!) {
  collectionDelete(input: $input) {
    deletedCollectionId
    userErrors { field message }
  }
}
"""

PUBLISHABLE_PUBLISH = """
mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    userErrors { field message }
  }
}
"""


def online_store_publication_id() -> str:
    """オンラインストアの publication ID を返す。

    status: ACTIVE は「オンラインストアに公開」ではない。販売チャネルへの追加は
    別操作なので、作ったコレクションはここへ明示的に公開する必要がある。
    """
    nodes = graphql(PUBLICATIONS_QUERY, {})["publications"]["nodes"]
    for node in nodes:
        if node["name"] == "Online Store":
            return node["id"]
    sys.exit(f"オンラインストアの販売チャネルが見つかりません: {[n['name'] for n in nodes]}")


def tag_products(dry_run: bool) -> None:
    print("■ 商品にカフェイン量のタグを付ける")
    seed = seed_products_module()
    wanted = {title: seed.caffeine_tag(caffeine) for _, title, _, _, _, _, caffeine, _ in seed.PRODUCTS}

    for product in graphql(PRODUCTS_QUERY, {})["products"]["nodes"]:
        tag = wanted.get(product["title"])
        if tag is None:
            print(f"  - {product['title']}: 対象外")
            continue
        if tag in product["tags"]:
            print(f"  - {product['title']}: {tag}（付与済み）")
            continue

        print(f"  - {product['title']}: {tag} を付与")
        if dry_run:
            continue
        # tagsAdd は追加のみで既存タグを消さないため、繰り返し流しても安全
        check_user_errors(graphql(TAGS_ADD, {"id": product["id"], "tags": [tag]}), "tagsAdd")


def create_collection(collection: dict, publication_id: str, dry_run: bool) -> None:
    handle = collection["handle"]
    existing = graphql(COLLECTION_BY_HANDLE, {"handle": handle})["collectionByHandle"]
    if existing:
        print(f"  - {handle}: 既にあります")
        return

    print(f"  - {handle}: 作成")
    if dry_run:
        print(f"      {json.dumps(collection, ensure_ascii=False)}")
        return

    created = check_user_errors(
        graphql(COLLECTION_CREATE, {"collection": collection}), "collectionCreate"
    )["collection"]

    check_user_errors(
        graphql(PUBLISHABLE_PUBLISH, {
            "id": created["id"],
            "input": [{"publicationId": publication_id}],
        }),
        "publishablePublish",
    )
    print(f"      作成して公開: /collections/{created['handle']}")


def delete_default_collection(dry_run: bool) -> None:
    print("■ 自動生成された既定コレクションを削除する")
    existing = graphql(COLLECTION_BY_HANDLE, {"handle": DEFAULT_COLLECTION_HANDLE})["collectionByHandle"]
    if not existing:
        print(f"  - {DEFAULT_COLLECTION_HANDLE}: ありません")
        return

    print(f"  - {existing['title']}（{DEFAULT_COLLECTION_HANDLE}）を削除")
    if dry_run:
        return
    # コレクションを消しても、中に入っていた商品自体は消えない
    check_user_errors(graphql(COLLECTION_DELETE, {"input": {"id": existing["id"]}}), "collectionDelete")


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    tag_products(dry_run)

    print("■ コレクションを作る")
    publication_id = "" if dry_run else online_store_publication_id()

    product_ids = [
        {"productId": node["id"]}
        for node in graphql(PRODUCTS_QUERY, {})["products"]["nodes"]
    ]

    create_collection({
        "title": "茶葉一覧",
        "handle": TEA_HANDLE,
        "descriptionHtml": (
            "<p>産地と製法の異なる6種類をそろえました。"
            "はじめての方は、渋みのおだやかな深蒸し煎茶かほうじ茶からどうぞ。</p>"
        ),
        "seo": {
            "title": "茶葉一覧｜chanoka（茶の香）",
            "description": (
                "煎茶・深蒸し煎茶・玉露・ほうじ茶・玄米茶・抹茶の6種類。"
                "産地と味わい、カフェイン量から選べます。ポートフォリオ用のデモストアです。"
            ),
        },
        # 手動で選んだ順に並べたいので MANUAL。価格順などに変えるのは管理画面からできる
        "sortOrder": "MANUAL",
        "sources": [{"source": {
            "title": "手動で選んだ商品",
            "inclusion": {"selections": product_ids},
        }}],
    }, publication_id, dry_run)

    create_collection({
        "title": "カフェイン控えめ",
        "handle": LOW_CAFFEINE_HANDLE,
        "descriptionHtml": (
            "<p>夕方や就寝前にも飲みやすい、カフェインの少ない茶葉です。"
            "タグを条件にした自動コレクションなので、該当する商品を追加すればひとりでに並びます。</p>"
        ),
        "seo": {
            "title": "カフェイン控えめの茶葉｜chanoka（茶の香）",
            "description": (
                "ほうじ茶と玄米茶など、カフェインの少ない茶葉をまとめました。"
                "ポートフォリオ用のデモストアです。"
            ),
        },
        "sortOrder": "PRICE_ASC",
        "sources": [{"source": {
            "title": f"{LOW_CAFFEINE_TAG} タグの商品",
            "inclusion": {
                "matchType": "ALL",
                "conditions": [{"productTag": {
                    "relation": "TAGGED_WITH",
                    "values": [LOW_CAFFEINE_TAG],
                    "matchType": "ANY",
                }}],
            },
        }}],
    }, publication_id, dry_run)

    delete_default_collection(dry_run)

    print("完了")


if __name__ == "__main__":
    main()
