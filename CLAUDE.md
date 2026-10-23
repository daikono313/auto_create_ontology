# ontogen

Webサイトを解析して、ディスカバリー用のオントロジー叩き台（Palantir Foundry 風）を自動生成するプロトタイプ。
概要と使い方は `README.md`、設計判断は `docs/adr/` を参照。

## 開発

- Python は uv で管理する: `uv sync`、`uv run ontogen ...`
- LLM は `claude -p` を子プロセスで呼ぶ（ADR 0004）。生成には数分かかるので、Bash の timeout は長めにとる
- 出力は `out/`（git 管理外）

## ルール

- 設計判断をしたら `docs/adr/` に ADR を書く（`/write-adr`）
- `ontogen/schema.py` を変えるときは ADR 0005 を確認する。LLM キャッシュ・gold・評価コードにも影響する
- プロンプトや前処理を変えたら、前後で評価を比べる（`/evaluate-ontology`）
- 正解データ（`gold/`）は生成結果を見ずに作り、点数を上げる目的で黙って書き換えない（`/create-gold`）
- クロールの前に robots.txt と利用規約を確認する（ADR 0003）
- 日本語のドキュメントは [natural-japanese](https://github.com/coji/natural-japanese) の規則に沿って書く。比喩や英語の直訳のような言い回し（「外向けの顔」「正とする」など）を使わず、何が起きるかをふだんの言葉で書く

## スキル

| スキル | 用途 |
|---|---|
| `/generate-ontology` | サイトを指定して叩き台を生成し、レビューする |
| `/create-gold` | 新しいサイトの正解データを作る |
| `/evaluate-ontology` | 正解と比べて評価する（変更の前後比較を含む） |
| `/write-adr` | 設計判断を ADR に残す |
