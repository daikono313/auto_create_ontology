# Architecture Decision Records

設計上の判断と、その理由を残す。新しく書くときは `template.md` をコピーするか、`/write-adr` スキルを使う。

- ファイル名は `NNNN-kebab-case-title.md`（連番）
- ステータスは `提案` / `承認` / `却下` / `廃止` / `置換（→ NNNN）`
- 一度承認したADRの本文は書き換えない。判断が変わったら新しいADRを書き、古いほうのステータスを `置換` にする

| No. | タイトル | ステータス |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | ADRで設計判断を記録する | 承認 |
| [0002](0002-discovery-draft-from-website.md) | Webサイトを入力に、ディスカバリー用の叩き台を出力する | 承認 |
| [0003](0003-target-sites.md) | 開発・検証の対象サイト | 承認 |
| [0004](0004-llm-via-claude-code-headless.md) | LLM は Claude Code のヘッドレスモードで呼ぶ | 承認 |
| [0005](0005-foundry-style-schema-as-source-of-truth.md) | Foundry 風の独自スキーマで定義し、表示用の形式はそこから生成する | 承認 |
| [0006](0006-two-stage-generation-by-url-pattern.md) | URLパターン単位の2段階生成 | 承認 |
| [0007](0007-evidence-required-and-verified.md) | すべての要素に根拠引用を必須にし、機械的に照合する | 承認 |
| [0008](0008-evaluation-against-gold.md) | 人手の正解データで定量評価する | 承認 |
