---
name: create-gold
description: 新しい対象サイトの正解オントロジー（gold/*.yaml）を作る。評価用の正解データを作りたいとき、新しいサイトで精度を測りたいときに使う。
---

# 正解オントロジー（gold）の作成

背景と書式のルール: `docs/adr/0008-evaluation-against-gold.md`。既存の例: `gold/books_toscrape.yaml`。

## 原則

- 正解は生成結果から作らない。先に生成結果を見ると、それに引きずられて評価の意味がなくなる。
  ページそのものを見て作る。
- 「サイトから読み取れること」を正解にする。サイトにないがビジネス上ありそうなもの（Order、Customer など）は
  `optional: true` にするか、入れない。

## 手順

1. ページを集める: 生成の前に `uv run ontogen run` を実行していれば、`out/<slug>/pages.json` を使える
   （このファイルはクロール結果なので見てよい。`fragments/` や `ontology.yaml` は見ない）。
   なければ、主要なページ種別（トップ、一覧、詳細、カートなど）を1〜2件ずつ取得する。

2. Object Type を洗い出す: 詳細ページの表・パンくず・フォームを中心に見る。
   - ボタンやフォームから推定できるもの（例: 「Add to basket」→ Basket）は必須に含める
   - 推定はできるが粒度が決めにくいもの（BasketLine と Basket の直結など）は `optional: true` にする

3. Property を列挙する: 表示されている値を snake_case で書き、よく使われる別名を `|` で並べる。
   ID・URL・通貨など、あっても妥当なものは先頭に `?` を付けて任意にする。

4. Link と Action を書く: Link は `between: [A, B]` で書く。A・B は object_types の `id` と完全に同じ文字列にする。

5. ユーザーにレビューしてもらう: 正解は人が決めるもの。迷った箇所（必須か任意か、エンティティか属性か）を
   列挙して確認してもらう。

6. 保存先は `gold/<slug>.yaml`。冒頭に対象URLと作成日をコメントで書く。
