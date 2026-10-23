import argparse
import json
from pathlib import Path

from .crawl import crawl
from .evaluate import evaluate
from .extract import digest, page_text
from .generate import generate, verify_evidence
from .render import to_html, to_mermaid, to_report, to_yaml
from .schema import Ontology


def cmd_run(args) -> None:
    out = Path(args.out)
    pages_file = out / "pages.json"
    out.mkdir(parents=True, exist_ok=True)

    if pages_file.exists() and not args.recrawl:
        print(f"[1/3] クロール結果を再利用: {pages_file}")
        pages = json.loads(pages_file.read_text())
    else:
        print(f"[1/3] クロール: {args.url}")
        raw = crawl(args.url, max_pages=args.max_pages, per_pattern=args.per_pattern, delay=args.delay)
        pages = [{"url": p.url, "pattern": p.pattern, "digest": digest(p.url, p.html), "text": page_text(p.html)}
                 for p in raw]
        pages_file.write_text(json.dumps(pages, ensure_ascii=False, indent=1))

    print(f"[2/3] オントロジー生成（{len(pages)} ページ, {len({p['pattern'] for p in pages})} パターン）")
    onto = generate(pages, out, lang=args.lang, model=args.model)

    print("[3/3] 書き出し")
    check = verify_evidence(onto, {p["url"]: p["text"] + "\n" + json.dumps(p["digest"], ensure_ascii=False) for p in pages})
    (out / "ontology.yaml").write_text(to_yaml(onto))
    (out / "ontology.mmd").write_text(to_mermaid(onto))
    (out / "report.md").write_text(to_report(onto, check, args.url))
    (out / "viewer.html").write_text(to_html(onto, args.url, len(pages), len({p["pattern"] for p in pages})))
    print(f"  完了: {out}/viewer.html, {out}/report.md（根拠一致 {check['verified']}/{check['checked']}）")

    if args.gold:
        _print_eval(onto, args.gold)


def _print_eval(onto: Ontology, gold: str) -> None:
    result = evaluate(onto, gold)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_eval(args) -> None:
    import yaml
    onto = Ontology.model_validate(yaml.safe_load(open(args.ontology)))
    _print_eval(onto, args.gold)


def main() -> None:
    parser = argparse.ArgumentParser(prog="ontogen", description="Webサイトからオントロジーの叩き台を生成する")
    sub = parser.add_subparsers(required=True)

    run = sub.add_parser("run", help="クロールから生成・書き出しまで実行")
    run.add_argument("url")
    run.add_argument("--out", required=True, help="出力ディレクトリ")
    run.add_argument("--max-pages", type=int, default=40)
    run.add_argument("--per-pattern", type=int, default=3, help="同じURLパターンから取得する最大ページ数")
    run.add_argument("--delay", type=float, default=0.5, help="リクエスト間隔（秒）")
    run.add_argument("--lang", default="Japanese", help="説明文の言語")
    run.add_argument("--model", default=None, help="claude -p に渡すモデル名")
    run.add_argument("--recrawl", action="store_true", help="キャッシュ済みのクロール結果を使わない")
    run.add_argument("--gold", help="正解YAML（指定すると評価も行う）")
    run.set_defaults(func=cmd_run)

    ev = sub.add_parser("eval", help="生成済みオントロジーを正解と比較")
    ev.add_argument("ontology")
    ev.add_argument("gold")
    ev.set_defaults(func=cmd_eval)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
