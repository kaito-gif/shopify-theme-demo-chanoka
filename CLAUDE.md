# chanoka-demo（副業ポートフォリオ用デモストア）

## この案件の前提

- **副業案件を獲得するためのポートフォリオ用デモストア**。クライアント案件ではない
- ブランド `chanoka`（茶の香）は**架空の日本茶D2C**。実在企業ではない
- 商品画像はすべて **OpenAI の画像生成モデルで作ったAI生成物**
- 発注者に見せる前提の成果物なので、**素のDawnからの差分がそのまま「手を動かした範囲」の証明**になる

上位の計画（なぜ作るか、どこへ公開するか、守秘義務の線引き）は
`~/.claude/plans/staged-squishing-bumblebee.md` と、その保全用の写しである
Notionページ「副業ポートフォリオ構築計画（Shopify中心）」を参照。

## 構成

- ストア: `chanoka-demo.myshopify.com`（Shopify Partners `Katayama` 組織 / Plus / 開発ストア）
- ライブテーマ: **`Dawn 15.5.0 baseline`（ID `190188192061`）**
- `Horizon`（ID `190188060989`）は未公開テーマとして保持（第2弾でHorizon版を作る場合に使う）
- ストアのパスワード保護は開発ストアの仕様で外せない。閲覧にはストアパスワードが要る
- ストア設定は日本仕様（通貨JPY / メートル法 / グラム / GMT+09:00）

### 自作したもの（Dawnには無いもの）

| ファイル | 内容 |
|---|---|
| `sections/product-comparison.liquid` | 商品比較表。最大4点、1列目 sticky、`<table>` + `scope` |
| `sections/faq-structured.liquid` | FAQ。**FAQPage の JSON-LD を出力**する（Dawnの `collapsible-content` は出さない） |
| `sections/steps-carousel.liquid` | scroll-snap の横スクロール手順UI。送りボタンは `assets/steps-carousel.js` |

対応するCSSは `assets/section-*.css`。

### スクリプト（テーマには含まれない）

- `scripts/generate-images.py` — 画像生成。`master` / `products` / `lifestyle` / `steps` / `hero`
- `scripts/seed-products.py` — Admin API で商品登録
- `scripts/upload-files.py` — 商品に紐づかない画像（ヒーロー・手順カット等）を
  「コンテンツ > ファイル」へ登録する。テーマ設定からは
  `shopify://shop_images/<ファイル名>` で参照する
- `scripts/output/` — 生成画像。`.gitignore` 済み

## 認証情報の置き場所

**すべて `~/.claude/portfolio/` 配下（git管理外・`chmod 600`）。リポジトリに置かない。**

| ファイル | 用途 |
|---|---|
| `~/.claude/portfolio/openai-key` | 画像生成 |
| `~/.claude/portfolio/shopify-token` | Admin API（`shpat_`） |
| `~/.claude/portfolio/ng-words.txt` | 公開前リーク検査用（122語） |
| `~/.claude/portfolio/pricing.md` | 単価基準・回答テンプレート |

Shopifyトークンのスコープ: `read/write_products`, `read/write_files`,
`read/write_publications`。

## よく使うコマンド

```bash
# ローカルプレビュー（ストアパスワードが要る。省くと対話プロンプトで止まる）
shopify theme dev --store chanoka-demo.myshopify.com --theme 190188192061 \
  --store-password <ストアパスワード>

# ライブテーマへ反映（--allow-live が無いと確認プロンプトで止まる）
shopify theme push --store chanoka-demo.myshopify.com --theme 190188192061 --allow-live

# 構文・規約チェック
shopify theme check

# 画像生成（1点だけ作り直すこともできる）
python3 scripts/generate-images.py products hojicha
```

## 検証

コードを変えたら、完了と報告する前に必ず以下を通す。

1. `shopify theme check` — **エラー0件**（警告8件はDawn由来の既存分なので許容）
2. `shopify theme dev` を起動し、`curl -s http://127.0.0.1:9292/` で
   `Liquid error` が0件、対象セクションのマークアップが出ていることを確認
3. **実ブラウザで操作する。** `theme check` では表示崩れを検出できない。
   実際に過去2件（CSS詳細度の取り違え、プレースホルダー画像のサイズ）が
   ブラウザ確認でしか見つからなかった
4. コンソールエラーが0件であること
5. テーマエディタから設定変更が効くことも確認する（発注者はここを見る）

## 触ってはいけないもの

- **`~/Coding/` の他のShopifyリポジトリからファイル・スニペットをコピーしない。**
  すべて受託案件で、受託契約により納品物の著作権が発注者に帰属する。
  **同じ知識を使って書き直すのは問題ない**（似た書き方・似た構造は許容）
- クライアント名・ストア名・ドメインを、コード・コメント・コミットメッセージに残さない
- `scripts/output/` の生成画像をコミットしない
- 開発ストアの `Horizon` テーマを削除しない

## ハマったところ（再発防止）

- **`shopify theme push` はテーマエディタで加えた設定を上書きする**
  （`config/settings_data.json`、各テンプレートのJSON）。
  エディタ側で設定を変えたら、push前に `shopify theme pull` で取り込む
- **`status: ACTIVE` は「オンラインストアに公開」ではない。**
  API で作成した商品は販売チャネルに自動追加されないため、
  `publishablePublish` で Online Store publication に明示的に公開する。
  踏まないと管理画面では有効なのにストアフロントで解決されない
- **テーマ設定の商品参照は GID ではなく handle 文字列。** GIDを入れても無言で空になる
- **Shopifyが自動生成する handle は日本語になる。** URLがパーセントエンコードされるため
  `productUpdate` でローマ字に振り直す
- **画像生成の「文字を入れるな」は一度書くだけでは効かない。**
  否定を具体的に列挙して繰り返す。ラベル色だけ変える指示にすると中身が破綻し、
  中身を指示すると今度は背景が変わる。3点まとめて固定する必要がある
- **WebP変換は不要。** Shopify CDN が自動でWebP/AVIFを配信する
- **`scroll-snap-type: x mandatory` は送りボタンを殺すことがある。**
  最後の項目の開始位置が最大スクロール量を超える幅構成だと、到達できる
  スナップ位置が先頭しか無くなる。さらに Chrome は smooth の
  `scrollBy` / `scrollTo` を現在のスナップ位置へ巻き戻す。
  最後の項目に `scroll-snap-align: end` を与え、JS 側は送り先を明示する
  `scrollTo` にすること
- **画像の連番カットは1点でも色が揃わないと使えない。** 手順カットも商品画像と
  同じく基準画像からの派生にする。テキストで「同じ器」と書くだけでは揃わない
- **Chrome DevTools 経由での検証時、対象が画面外だと smooth スクロールが
  動かない。** カルーセルの動作確認は `scrollIntoView` してから行う。
  画面外のまま計測して「動かない」と誤診しかけた

## Shopify CLI のバージョン

4.6.0。`shopify theme list` 等の実行時に自動アップグレードされることがある。
