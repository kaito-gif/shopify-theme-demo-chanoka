# chanoka — Shopify テーマ実装のデモストア

Shopify のテーマ実装力を示すために作った、架空の日本茶ショップのデモストアです。
案件の獲得を目的としたポートフォリオであり、クライアントの納品物ではありません。

- デモストア: https://chanoka-demo.myshopify.com/
- 実装の解説: [Shopify テーマ構築・カスタマイズ](https://app.notion.com/p/3b032860c0bd81369c52f1fc7e587f78)

デモストアはShopifyの開発ストアで、仕様上パスワード保護を外せません。
閲覧用のパスワードは上記の解説ページに記載しています。

> ブランド「chanoka（茶の香）」は架空です。実在する企業・商品ではありません。
> 商品画像はすべて画像生成AIで作成したもので、注文を受け付けるものではありません。

## このリポジトリの読み方

**初期コミット `25f15eb` が素の [Dawn 15.5.0](https://github.com/Shopify/dawn) です。**
そこからの差分が、そのまま手を動かした範囲になります。

```bash
git diff 25f15eb HEAD -- assets sections snippets config/settings_schema.json
```

テーマ関連の追加・変更はおよそ 1,300 行です。

## 自作したもの

Dawn には無いセクションです。いずれもテーマエディタから設定・並べ替えできます。

| ファイル | 内容 |
|---|---|
| `sections/product-comparison.liquid` | 商品比較表。最大4点、1列目 sticky、`table` + `scope` によるマークアップ |
| `sections/faq-structured.liquid` | FAQ。FAQPage の JSON-LD を出力する（Dawn の `collapsible-content` は出さない） |
| `sections/steps-carousel.liquid` | スクロールスナップの横スクロール手順UI。送りボタンは `assets/steps-carousel.js` |

Dawn からの改変は次の2点です。

| ファイル | 内容 |
|---|---|
| `sections/footer.liquid` | デモ・架空ブランド・AI生成である旨の注記を全ページ最下部に出す設定を追加 |
| `snippets/meta-tags.liquid` | `og:image` が無いページ向けに、テーマ設定の既定共有画像へフォールバック |

対応するCSSは `assets/section-*.css` にあります。

## スクリプト

テーマには含まれない、構築時に使ったものです。

| ファイル | 内容 |
|---|---|
| `scripts/generate-images.py` | 商品・ヒーロー・手順カットの画像生成 |
| `scripts/seed-products.py` | Admin API による商品登録 |
| `scripts/upload-files.py` | 商品に紐づかない画像を「コンテンツ > ファイル」へ登録 |

APIキーはリポジトリに含めていません。実行時にローカルの管理外ディレクトリから読みます。

## 計測結果

Lighthouse（モバイル / シークレットウィンドウ / 拡張機能なし / 本番ストアで計測）

| カテゴリ | スコア |
|---|---|
| パフォーマンス | 99 |
| ユーザー補助 | 100 |
| おすすめの方法 | 100 |
| SEO | 100 |

ローカルの開発サーバーで測ると未圧縮配信とキャッシュヘッダ無しの影響で
パフォーマンスが70点台まで落ちるため、この数値は本番ストアで計測しています。

FAQPage の構造化データは Schema Markup Validator でエラー0件・警告0件です。

## ドキュメント

- `CLAUDE.md` — 構成、検証手順、実装中に踏んだ落とし穴
- `docs/context.md` — 背景と判断の記録
- `docs/portfolio-page.md` — 上記の解説ページの原稿

## ライセンス

Dawn 由来のコードは Shopify の MIT ライセンスに従います（`LICENSE.md`）。
