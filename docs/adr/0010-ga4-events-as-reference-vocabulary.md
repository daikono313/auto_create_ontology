# 0010. GA4 の推奨イベントを参照語彙にし、ページ内の計測タグも手がかりにする

- ステータス: 承認
- 日付: 2026-10-23

## コンテキスト

ジャーニー（ADR 0009）を組み立てるには、ECでよくある操作の一覧が要る。
GA4 には EC 向けの推奨イベントが定義されており（`view_item`、`add_to_cart`、`begin_checkout`、`purchase` など）、
イベントごとのパラメータ（`transaction_id`、`shipping`、`tax`、`items[].item_variant` など）は、
Order や商品の Property の候補にもなる。多くのECサイトが GA4 を入れているので、顧客との会話でも通じやすい。

また、GTM（Google タグマネージャー）や gtag.js を入れているサイトでは、ページのHTMLに
`dataLayer.push({event: "add_to_cart", ...})` や `gtag("event", "view_item", ...)` が書かれていることがある。
これは、そのサイトが実際に計測している操作の手がかりになる。

## 決定

- GA4 の推奨イベントを `ontogen/references/ga4_events.yaml` に置き、統合（2段階目）のプロンプトに参照語彙として渡す。
  出典は https://developers.google.com/analytics/devguides/collection/ga4/reference/events （2026-10-23 に確認）。
- Action Type とジャーニーのステップに `ga4_event`（対応する GA4 のイベント名）を持たせる。対応するものがなければ空にする。
- ページ要約（`extract.digest`）で、スクリプトから次を抜き出す。
  - GTM のコンテナID（`GTM-XXXX`）と GA4 の測定ID（`G-XXXX`）
  - `dataLayer.push` と `gtag("event", ...)` で送っているイベント名
- 計測タグから見つかったイベントは、そのサイトで実際に起きる操作として扱い、ステップを `observed: true` にしてよい。

## 検討した代替案

- GTM のコンテナ（`googletagmanager.com/gtm.js?id=GTM-XXXX`）を取得して、タグとトリガーの定義を読む:
  情報は多いが、対象サイト以外のホストへのリクエストになる。まずはページ内の記述だけを使い、必要になったら検討する
- 独自の語彙を作る: 顧客と共有しにくく、網羅性も確かめにくい

## 結果

- ジャーニーのステップ名が GA4 のイベント名とそろうので、顧客の GA4 のデータと突き合わせやすくなる。
- GA4 の推奨イベントは EC とリード獲得が中心で、予約・申し込みなど他の業種の操作は少ない。EC以外のサイトでは語彙を追加する必要がある。
- books.toscrape.com には計測タグがないため、計測タグからの抽出は Shopify 系サイトで検証する。
