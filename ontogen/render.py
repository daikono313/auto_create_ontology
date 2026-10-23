"""オントロジーを YAML / Mermaid ER図 / Markdownレポートに書き出す。"""

import re

import yaml

from .schema import Ontology

MERMAID_CARDINALITY = {
    "one_to_one": "||--||",
    "one_to_many": "||--o{",
    "many_to_one": "}o--||",
    "many_to_many": "}o--o{",
}


def to_yaml(onto: Ontology) -> str:
    return yaml.safe_dump(onto.model_dump(), allow_unicode=True, sort_keys=False, width=120)


def _ident(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def to_mermaid(onto: Ontology) -> str:
    lines = ["erDiagram"]
    for o in onto.object_types:
        lines.append(f"  {_ident(o.id)} {{")
        for p in o.properties:
            key = " PK" if p.name == o.primary_key else ""
            lines.append(f"    {p.type} {_ident(p.name)}{key}")
        lines.append("  }")
    for l in onto.link_types:
        lines.append(f"  {_ident(l.source)} {MERMAID_CARDINALITY[l.cardinality]} {_ident(l.target)} : {_ident(l.id)}")
    return "\n".join(lines)


def to_report(onto: Ontology, evidence_check: dict, site_url: str) -> str:
    out = [f"# オントロジー叩き台: {onto.domain}", "", f"対象サイト: {site_url}", "", onto.summary, ""]
    out += ["## ER図", "", "```mermaid", to_mermaid(onto), "```", ""]

    out += ["## Object Types", ""]
    for o in onto.object_types:
        out += [f"### {o.id}", "", o.description, ""]
        if o.properties:
            out += ["| Property | Type | 説明 |", "|---|---|---|"]
            for p in o.properties:
                pk = " (PK)" if p.name == o.primary_key else ""
                enum = f"（値: {', '.join(p.enum_values)}）" if p.enum_values else ""
                out.append(f"| `{p.name}`{pk} | {p.type} | {p.description}{enum} |")
            out.append("")
        out += [f"- 根拠: [{e.quote}]({e.url})" for e in o.evidence] + [""]

    out += ["## Link Types", "", "| Link | Source | Target | 多重度 | 説明 |", "|---|---|---|---|---|"]
    out += [f"| `{l.id}` | {l.source} | {l.target} | {l.cardinality} | {l.description} |" for l in onto.link_types]
    out += ["", "## Action Types", "", "| Action | 実行者 | 影響する Object | 説明 |", "|---|---|---|---|"]
    out += [f"| `{a.id}` | {a.actor or '-'} | {', '.join(a.affects)} | {a.description} |" for a in onto.action_types]

    out += ["", "## ヒアリングで確認すべき事項", ""] + [f"- [ ] {q}" for q in onto.open_questions]

    out += ["", "## 根拠の検証", "", f"引用 {evidence_check['checked']} 件中 {evidence_check['verified']} 件がページ本文と一致しました。"]
    if evidence_check["unverified"]:
        out += ["", "一致しなかった引用（要確認）:", ""]
        out += [f"- {u['element']}: 「{u['quote']}」 ({u['url']})" for u in evidence_check["unverified"]]
    return "\n".join(out) + "\n"
