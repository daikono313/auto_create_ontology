# 0011. 検証用サイトを webscraper.io のテスト用ECサイトに変える

- ステータス: 承認
- 日付: 2026-10-23

## コンテキスト

ADR 0003 では、検証用サイトとして Shopify 系の中規模D2Cサイト（例: Allbirds）を挙げていた。
クロールの前に確認したところ、Allbirds の利用規約は自動アクセスを禁止していた。

> Access any of the features of the Platform through any automated means or with any automated features or devices (including use of scripts or web crawlers)

ほかに、スクレイピング練習用として公開されている次のECサイトを確認した（2026-10-23）。

| サイト | 結果 |
|---|---|
| scrapingcourse.com/ecommerce | GA4 のタグと購入まわりのページがあるが、robots.txt で `/ecommerce/*` が禁止されている |
| scrapeme.live/shop | robots.txt では許可されているが、練習用に使ってよいという記載がない。計測タグもない |
| webscraper.io/test-sites/e-commerce/allinone | 「You can use this site for training」と明記されている。GTM のタグがあり、商品の選択肢（HDD 容量）やカテゴリの階層もある |

## 決定

- 開発用の books.toscrape.com（ADR 0003）に加えて、webscraper.io のテスト用ECサイトを2つ目の対象にする。
  正解データは `gold/webscraper_allinone.yaml`。
- Shopify 系サイトでの検証は、クロールを許可しているサイトが見つかるまで保留する。
  顧客のサイトを対象にする場合は、顧客から許可を得たうえで行う。

## 検討した代替案

- Allbirds で実行する: 利用規約に反するので行わない
- scrapingcourse.com を robots.txt を無視して取得する: robots.txt に従うという方針（ADR 0003）に反する
- scrapeme.live を使う: 規約上の禁止は見つからなかったが、練習用に使ってよいという明示もない。スラッグ形式のURLの確認には、取得済みの1ページのリンクだけを使った

## 結果

- 2つ目のサイトで、カートのないサイト（購入フローを補ってはいけない例）を検証できる。
- webscraper.io の商品URLは数字のIDを含む（`/product/60`）ので、スラッグ形式のURLのまとめ方（ADR 0012）は実サイトのクロールではまだ検証できていない。
- GTM のコンテナIDは抽出できたが、ページ内にイベント名の記述はなく、GA4 のイベントからジャーニーを確かめることはできていない。
