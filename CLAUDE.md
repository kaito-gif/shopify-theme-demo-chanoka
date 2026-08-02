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
- **既定言語は日本語**（2026-08-02に英語から変更）。`<html lang="ja">` になり、
  Dawnの `locales/ja.json` が効いて画面文言も日本語になっている

### ストア設定（テーマではなく管理画面側にあるもの）

テーマのコードをいくら見ても出てこないので、迷ったらここを見る。

| 項目 | 場所 | 現在の値 |
|---|---|---|
| 既定言語 | 設定 > 言語 | 日本語（「デフォルトを変更」で変更。言語追加ではないのでアプリ導入は不要） |
| ホームページのタイトル | オンラインストア > 各種設定 | `chanoka（茶の香）｜日本茶のオンラインストア` |
| メタディスクリプション | 同上 | 産地・6商品・淹れ方に触れ、末尾でデモかつ架空ブランドである旨を明記 |
| ソーシャル共有画像 | 同上 | **未設定。テーマ設定の既定画像で補っている**（下記） |
| メニュー名称 | コンテンツ > メニュー | ホーム / 茶葉一覧 / お問い合わせ |
| コレクション | 商品管理 > コレクション | `tea`（手動・6商品）と `low-caffeine`（タグ条件の自動）。`scripts/seed-collections.py` が作る |
| 絞り込みの名称 | Search & Discovery アプリ | 「在庫状況」「価格」。既定だと英語で出るため、アプリを入れて改名した。テーマ側では変えられない |
| ストアパスワード | オンラインストア > 各種設定 | 画面に平文で表示される。閲覧用に人へ渡すときはここから確認する |

**管理画面のソーシャル共有画像は設定できない。** 「画像を追加」がネイティブの
ファイルダイアログを開く作りで、AIからは操作不能。そのため
`settings_schema.json` に `default_share_image`（SNS共有時の既定画像）を追加し、
`snippets/meta-tags.liquid` で `page_image` が無いときのフォールバックにしている。
管理画面側で指定されればそちらが優先される。

### 自作したもの（Dawnには無いもの）

| ファイル | 内容 |
|---|---|
| `sections/product-comparison.liquid` | 商品比較表。最大4点、1列目 sticky、`<table>` + `scope` |
| `sections/faq-structured.liquid` | FAQ。**FAQPage の JSON-LD を出力**する（Dawnの `collapsible-content` は出さない） |
| `sections/steps-carousel.liquid` | scroll-snap の横スクロール手順UI。送りボタンは `assets/steps-carousel.js` |
| `sections/footer.liquid`（Dawn改変） | `demo_disclaimer` 設定を追加。デモ・架空ブランド・AI生成の注記を全ページ最下部に出す |
| `snippets/meta-tags.liquid`（Dawn改変） | `og:image` が無いページ向けに、テーマ設定の既定共有画像へフォールバック |

対応するCSSは `assets/section-*.css`。

### スクリプト（テーマには含まれない）

- `scripts/generate-images.py` — 画像生成。`master` / `products` / `lifestyle` / `steps` / `hero`。
  パッケージのラベルは**無地で出す**（文字はAIが崩すため）
- `scripts/brand-packages.py` — 無地のラベルに「茶の香 / chanoka / 品名」を刷る。
  Pillow を使う唯一のスクリプトなので `scripts/requirements.txt` と `.venv` が要る
- `scripts/seed-products.py` — Admin API で商品登録。画像は `branded/` があればそちらを使う
- `scripts/update-product-images.py` — 登録済み商品のメイン画像だけを差し替える。
  `seed-products.py` を流し直すと `productSet` が id 無しで走って商品が二重になる
- `scripts/seed-collections.py` — カフェイン量のタグ付け、コレクション作成（手動の
 `tea` と タグ条件の自動 `low-caffeine`）、オンラインストアへの公開、
 自動生成された `frontpage` の削除。何度流しても同じ結果になる
- `scripts/upload-files.py` — 商品に紐づかない画像（ヒーロー・手順カット等）を
  「コンテンツ > ファイル」へ登録する。テーマ設定からは
  `shopify://shop_images/<ファイル名>` で参照する
- `scripts/output/` — 生成画像。`.gitignore` 済み。
  `scripts/output/branded/` がブランド名を刷った版で、ストアに上がっているのはこちら

```bash
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python scripts/brand-packages.py           # 6点に刷る
.venv/bin/python scripts/brand-packages.py --guide   # ラベル枠の当たりを確認する
```

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
# 注意: --theme にライブテーマIDを渡しているため開発テーマは作られず、
# 編集するたびライブテーマへ直接同期される。「ローカルだけの変更」にはならない。
# 起動したままにせず、検証が終わったら止めること
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
  すべて受託案件で、契約により納品物の著作権が発注者に帰属する。
  **同じ知識を使って書き直すのは問題ない**（似た書き方・似た構造は許容）
- クライアント名・ストア名・ドメインを、コード・コメント・コミットメッセージに残さない。
  **このファイル自身も公開対象**なので、ここにも書かない
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
- **既定言語を日本語にしても、テンプレートのJSONへ直接保存されている文言は
 英語のまま残る。** `locales/ja.json` は効かない。フッターの登録欄・共有ボタン・
 関連商品・コレクション一覧の見出しが該当した。`templates/*.json` と
 `sections/*-group.json` を英語文字列で検索して洗い出すこと
- **`collectionCreate` の `ruleSet` は非推奨。** `collection: CollectionCreateInput`
 の `sources` を使う。タグ条件は `productTag` の `TAGGED_WITH`。
 作成直後は未公開なので `publishablePublish` が要る（商品と同じ）
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
- **パッケージのブランド名は画像生成に描かせず、あとから合成する。**
 6点それぞれに字形も位置も違うものが出るうえ、色まで振り出しに戻る。
 ラベルは無地で出し、`brand-packages.py` が Pillow で刷る。ラベルの矩形は
 マスターからの派生なので全点ほぼ同一で、固定値（`LABEL`）で足りる。
 淡いラベル（玄米茶）だけ地のクラフト紙と色が近く、明度で検出させると外すため
 検出はやめた。文字色は明度で墨と生成りを切り替える
- **画像の連番カットは1点でも色が揃わないと使えない。** 手順カットも商品画像と
  同じく基準画像からの派生にする。テキストで「同じ器」と書くだけでは揃わない
- **Chrome DevTools 経由での検証時、対象が画面外だと smooth スクロールが
  動かない。** カルーセルの動作確認は `scrollIntoView` してから行う。
  画面外のまま計測して「動かない」と誤診しかけた
- **横スクロールコンテナの中の `position: absolute` は、包含ブロックが
  コンテナの外にあるとクリップを抜けてページ全体に横スクロールを起こす。**
  Dawn の `.visually-hidden` を横スクロール内で使うときは、項目側に
  `position: relative` を入れること。狭い画面ほど顕著に出る。
  検出は `document.documentElement.scrollWidth > clientWidth` を見て、
  子要素を1つずつ `display:none` にして切り分けるのが速い
- **Lighthouseは `http://127.0.0.1:9292`（theme dev）で測ってはいけない。**
  devサーバーは未圧縮配信・キャッシュヘッダ無し・プロキシ遅延のため
  Performance 77 / Best Practices 77 まで落ち、`server-response 750ms`・
  `unminified CSS/JS`・`is-on-https` 失格はいずれもdev環境固有の失格になる。
  実ストア（`https://chanoka-demo.myshopify.com/`）を測ること。
  ストアはパスワード保護されているので、**シークレットウィンドウで先にストア
  パスワードを通してから**計測する（でないとパスワード画面を測る）。
  シークレットでも「シークレットモードでの実行を許可」が有効な拡張機能は動くため、
  `chrome://extensions/?id=<ID>` で個別にオフにする
- **セクションのCSSは `stylesheet_tag` により `<link>` がbody内に出力される。**
  ブラウザ上でCSSを差し替えて検証するとき、`<head>` に `<style>` を差すと
  後勝ちで負けて**何も変わらない**。body末尾に差すこと。効いたかどうかは
  `getComputedStyle` の実値で毎回確かめる
- **Notion の画像ブロックは差し替えられない。** 本文を取得すると画像は
 署名付きURL付きの `![](...)` で返るが、この署名は取得のたびに変わる。
 `update_content` の `old_str` は完全一致なので、取得直後に投げても当たらない。
 新しい画像を隣に差し込んで、古い方は手で消してもらうのが現実的
- **ストアフロントは `X-Frame-Options: DENY` かつ `frame-ancestors 'none'`。**
  iframe に読み込んで実機幅を測ることはできない。ポップアップもブロックされる。
  macOSのChromeはウィンドウ幅500px未満にできないため、**390px等の実機幅は
  この環境では再現できない**。狭い幅の確認はDevToolsのデバイスモードか実機で行う

## 別セッションから再開するとき

1. このファイルと `~/.claude/plans/staged-squishing-bumblebee.md` の「現在地」を読む
2. `git log --oneline` で直近の作業を確認する
3. Step 2（デモストア構築）完了。Lighthouse計測・構造化データ検証も完了。
   **Step 3（案件獲得用ページの作成・公開）も完了。** 公開URLは
   `docs/context.md` の「進捗」にある。本文を直すときは
   `docs/portfolio-page.md` と Notion の両方を更新すること
4. 未着手で残っているのは `docs/context.md` の「未決の事項」2件のみ。
   どちらも判断待ちなので、こちらから進めずに確認すること

ブラウザ検証を伴う作業をするなら `claude --chrome` で起動する。
ストアフロントはパスワード保護されているため、**AIからパスワードは入力しない**。
ユーザーにブラウザでパスワードを入れてもらってから検証に入る。

## Shopify CLI のバージョン

4.6.0。`shopify theme list` 等の実行時に自動アップグレードされることがある。
