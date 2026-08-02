#!/usr/bin/env python3
"""登録済み商品のメイン画像を、ブランド名を刷ったものに差し替える。

brand-packages.py が scripts/output/branded/ に出したものを上げ直す。
seed-products.py を流し直すと productSet が id 無しで走って商品が二重にできるため、
画像だけを入れ替えるこちらを使うこと。

先に新しい画像を足してから古い方を消す。逆順にすると、失敗したときに画像の無い
商品が残る。

使い方:
    .venv/bin/python scripts/update-product-images.py           # 差し替え
    .venv/bin/python scripts/update-product-images.py --dry-run # 対象の確認だけ
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BRANDED_DIR = REPO_ROOT / "scripts" / "output" / "branded"


def seed_products_module():
    """seed-products.py を読み込む。商品一覧と GraphQL の足回りを借りる。

    ファイル名にハイフンが入っていて通常の import ができないので spec 経由で読む。
    """
    path = Path(__file__).with_name("seed-products.py")
    spec = importlib.util.spec_from_file_location("seed_products", path)
    if spec is None or spec.loader is None:
        sys.exit(f"読み込めません: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed = seed_products_module()

PRODUCTS_QUERY = """
query products {
  products(first: 50) {
    nodes {
      id
      title
      handle
      media(first: 20) { nodes { id } }
    }
  }
}
"""

CREATE_MEDIA = """
mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
  productCreateMedia(productId: $productId, media: $media) {
    media { ... on MediaImage { id } }
    mediaUserErrors { field message }
  }
}
"""

DELETE_MEDIA = """
mutation productDeleteMedia($productId: ID!, $mediaIds: [ID!]!) {
  productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
    deletedMediaIds
    mediaUserErrors { field message }
  }
}
"""


def check_media_errors(result: dict, key: str) -> dict:
    errors = result[key].get("mediaUserErrors") or []
    if errors:
        sys.exit(f"{key} でエラー: {errors}")
    return result[key]


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    existing = {p["title"]: p for p in seed.graphql(PRODUCTS_QUERY, {})["products"]["nodes"]}

    for filename, title, *_ in seed.PRODUCTS:
        image_path = BRANDED_DIR / filename
        if not image_path.is_file():
            sys.exit(
                f"{image_path.relative_to(REPO_ROOT)} がありません。"
                "先に brand-packages.py を実行してください。"
            )
        product = existing.get(title)
        if product is None:
            sys.exit(f"ストアに「{title}」が見つかりません。先に seed-products.py を実行してください。")

        old_media = [m["id"] for m in product["media"]["nodes"]]
        print(f"- {title}（既存の画像 {len(old_media)}点）")
        if dry_run:
            continue

        resource_url = seed.upload_image(image_path)
        check_media_errors(
            seed.graphql(CREATE_MEDIA, {
                "productId": product["id"],
                "media": [{
                    "originalSource": resource_url,
                    "mediaContentType": "IMAGE",
                    "alt": title,
                }],
            }),
            "productCreateMedia",
        )

        if old_media:
            check_media_errors(
                seed.graphql(DELETE_MEDIA, {
                    "productId": product["id"],
                    "mediaIds": old_media,
                }),
                "productDeleteMedia",
            )
        print("    差し替え完了")

    print("完了")


if __name__ == "__main__":
    main()
