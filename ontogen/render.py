"""オントロジーを YAML / Mermaid ER図 / Markdownレポート / HTMLビューアに書き出す。"""

import html
import json
import re
from importlib.resources import files
from urllib.parse import urlparse

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


def _label(s: str) -> str:
    return s.replace('"', "#quot;")


def journey_mermaid(journey) -> str:
    """ジャーニーのフローチャート。サイトで確認できなかったステップは破線にする。"""
    lines = ["flowchart LR"]
    for i, st in enumerate(journey.steps, 1):
        ga4 = f"<br/>{st.ga4_event}" if st.ga4_event else ""
        lines.append(f'  s{i}["{i}. {_label(st.action)}{_label(ga4)}"]')
    lines += [f"  s{i} --> s{i + 1}" for i in range(1, len(journey.steps))]
    inferred = [f"s{i}" for i, st in enumerate(journey.steps, 1) if not st.observed]
    if inferred:
        lines += ["  classDef inferred stroke-dasharray: 5 4", f"  class {','.join(inferred)} inferred"]
    return "\n".join(lines)


def state_mermaid(sm) -> str:
    lines = ["stateDiagram-v2", f"  [*] --> {_ident(sm.initial_state)}"]
    lines += [f"  {_ident(t.from_state)} --> {_ident(t.to_state)} : {t.action}" for t in sm.transitions]
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
    out += ["", "## Action Types", "", "| Action | 実行者 | 影響する Object | GA4 イベント | 説明 |", "|---|---|---|---|---|"]
    out += [f"| `{a.id}` | {a.actor or '-'} | {', '.join(a.affects)} | {a.ga4_event or '-'} | {a.description} |"
            for a in onto.action_types]

    if onto.journeys:
        out += ["", "## ユーザージャーニー", "", "「確認」が × のステップは、サイトでは確認できず、典型的な流れから補ったもの。"]
        for j in onto.journeys:
            out += ["", f"### {j.name}", "", f"- 実行者: {j.actor}", f"- 目的: {j.goal}", "",
                    "```mermaid", journey_mermaid(j), "```", "",
                    "| # | Action | GA4 イベント | 確認 | 内容 |", "|---|---|---|---|---|"]
            out += [f"| {i} | `{st.action}` | {st.ga4_event or '-'} | {'○' if st.observed else '×'} | {st.description} |"
                    for i, st in enumerate(j.steps, 1)]
    if onto.state_machines:
        out += ["", "## 状態遷移"]
        for sm in onto.state_machines:
            mark = "" if sm.observed else "【推定】"
            out += ["", f"### {sm.object_type}.{sm.state_property}{mark}", "", sm.description, "",
                    "```mermaid", state_mermaid(sm), "```"]

    out += ["", "## ヒアリングで確認すべき事項", ""] + [f"- [ ] {q}" for q in onto.open_questions]

    out += ["", "## 根拠の検証", "", f"引用 {evidence_check['checked']} 件中 {evidence_check['verified']} 件がページ本文と一致しました。"]
    if evidence_check["unverified"]:
        out += ["", "一致しなかった引用（要確認）:", ""]
        out += [f"- {u['element']}: 「{u['quote']}」 ({u['url']})" for u in evidence_check["unverified"]]
    return "\n".join(out) + "\n"


def to_html(onto: Ontology, site_url: str, n_pages: int, n_patterns: int) -> str:
    """ブラウザで直接開けるビューア。ER図の描画には CDN の mermaid を使う。"""
    template = files("ontogen").joinpath("templates/viewer.html").read_text()
    payload = onto.model_dump()
    payload["diagrams"] = {
        "journeys": {j.id: journey_mermaid(j) for j in onto.journeys},
        "states": {f"{sm.object_type}.{sm.state_property}": state_mermaid(sm) for sm in onto.state_machines},
    }
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return (template
            .replace("__TITLE__", html.escape(f"{urlparse(site_url).netloc} オントロジー"))
            .replace("__MMD__", html.escape(to_mermaid(onto)))
            .replace("__SITE__", html.escape(site_url))
            .replace("__CRAWL__", f"{n_pages} ページ（{n_patterns} 種類のURLパターン）")
            .replace("__DATA__", data))
