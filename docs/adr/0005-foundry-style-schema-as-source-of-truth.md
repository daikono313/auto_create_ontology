# 0005. Foundry 風の独自スキーマで定義し、表示用の形式はそこから生成する

- ステータス: 承認
- 日付: 2026-10-23

## コンテキスト

用途はディスカバリー用の叩き台（ADR 0002）であり、実データにはつながない。
したがって出力に求められるのは、次の3点である。

- 人が読んでレビュー・修正しやすいこと
- 顧客に見せられる形（図）に変換できること
- 根拠（URL・引用）を要素ごとに持てること

## 決定

- オントロジーは Pydantic で定義した独自スキーマ（`ontogen/schema.py`）で表し、ほかの形式はすべてここから生成する。
  語彙は Palantir Foundry に合わせ、`object_types` / `properties` / `link_types` / `action_types` とする。
  これに `open_questions` と、要素ごとの `evidence` を加える。
- 保存形式は YAML（`ontology.yaml`）。表示用に Mermaid ER図（`ontology.mmd`）と Markdown レポート（`report.md`）を生成する。
- 同じ Pydantic モデルを、LLM の構造化出力のスキーマにも使う（ADR 0004）。

## 検討した代替案

- LinkML: YAML から OWL・SQL DDL・JSON Schema を生成できて便利だが、Action を表す仕組みがない。必要になったらエクスポータを追加する
- OWL/RDF: 叩き台にしては記述量が多く、顧客との会話に向かない
- Foundry の実際の定義形式: Foundry に実際に載せる予定がないため、そこまで合わせる必要はない

## 結果

- スキーマを1か所で管理でき、LLM 出力の検証・保存・描画のすべてに同じ定義を使える。
- スキーマを変えると LLM キャッシュが無効になり、gold や評価コードにも影響する。変更時はこの ADR を更新する。
- 他の形式（LinkML / OWL / Foundry）が必要になったら、`render.py` にエクスポータを追加する。
