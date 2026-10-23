"""生成したオントロジーを人手の正解（gold）と比較する。

gold の書式は gold/*.yaml を参照。名前は `|` 区切りで別名を書け、optional: true の要素
（プロパティは名前の先頭に `?`）は、生成されなくても再現率を下げず、生成されても適合率を下げない。
properties を書いていない Object はプロパティを採点しない。
推定の要素（inferred が true）は、gold と一致すれば正解として数え、
一致しなければ適合率の分母に入れず inferred として件数だけ出す（ADR 0009）。
"""

import difflib
import re

import yaml

from .schema import Ontology

FUZZY_THRESHOLD = 0.85


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _matches(name: str, alternatives: str) -> bool:
    n = _norm(name)
    return any(n == _norm(a) or difflib.SequenceMatcher(None, n, _norm(a)).ratio() >= FUZZY_THRESHOLD
               for a in alternatives.split("|"))


def _find(name: str, gold_items: list[dict], exact: bool = False) -> dict | None:
    return next((g for g in gold_items if (name == g["id"] if exact else _matches(name, g["id"]))), None)


def _pr(tp: int, n_pred: int, n_gold: int) -> dict:
    return {"precision": round(tp / n_pred, 3) if n_pred else None,
            "recall": round(tp / n_gold, 3) if n_gold else None,
            "tp": tp, "predicted": n_pred, "gold": n_gold}


def _is_inferred(element) -> bool:
    return element.inferred


def _score(pred_ids: list[str], gold_items: list[dict], exact: bool = False,
           inferred: set[str] = frozenset()) -> tuple[dict, dict[str, str]]:
    """要素名リストを gold と突き合わせ、指標と「予測ID → gold ID」の対応を返す。"""
    mapping = {p: g["id"] for p in pred_ids if (g := _find(p, gold_items, exact))}
    required = {g["id"] for g in gold_items if not g.get("optional")}
    matched = set(mapping.values())
    tp = len(matched & required)
    # optional な gold と一致した予測は適合率の分母から外す
    optional = {g["id"] for g in gold_items if g.get("optional")}
    # gold と一致しなかった推定の要素も、適合率の分母から外す
    unmatched_inferred = sorted(p for p in pred_ids if p not in mapping and p in inferred)
    n_pred = sum(1 for p in pred_ids if mapping.get(p) not in optional and p not in unmatched_inferred)
    result = _pr(tp, n_pred, len(required))
    result["missing"] = sorted(required - matched)
    result["extra"] = sorted(p for p in pred_ids if p not in mapping and p not in inferred)
    result["inferred"] = unmatched_inferred
    return result, mapping


def evaluate(onto: Ontology, gold_path: str) -> dict:
    gold = yaml.safe_load(open(gold_path))

    objects, obj_map = _score([o.id for o in onto.object_types], gold["object_types"],
                              inferred={o.id for o in onto.object_types if _is_inferred(o)})

    prop_tp = prop_gold = prop_pred = 0
    prop_missing = {}
    for o in onto.object_types:
        g = next((g for g in gold["object_types"] if g["id"] == obj_map.get(o.id)), None)
        if not g or "properties" not in g:
            continue
        gold_props = [{"id": p.lstrip("?"), "optional": p.startswith("?")} for p in g["properties"]]
        r, _ = _score([p.name for p in o.properties], gold_props)
        prop_tp, prop_gold, prop_pred = prop_tp + r["tp"], prop_gold + r["gold"], prop_pred + r["predicted"]
        if r["missing"]:
            prop_missing[o.id] = r["missing"]
    properties = _pr(prop_tp, prop_pred, prop_gold) | {"missing": prop_missing}

    # Link は向きを問わず、両端の Object（gold ID に対応付けたもの）の組み合わせで完全一致比較する
    def pair(a: str, b: str) -> str:
        return "~".join(sorted([a, b]))

    gold_links = [{"id": pair(*l["between"]), "optional": l.get("optional", False)} for l in gold["link_types"]]
    link_pairs = {id(l): pair(obj_map.get(l.source, l.source), obj_map.get(l.target, l.target)) for l in onto.link_types}
    links, _ = _score(list(link_pairs.values()), gold_links, exact=True,
                      inferred={link_pairs[id(l)] for l in onto.link_types if _is_inferred(l)})

    actions, _ = _score([a.id for a in onto.action_types], gold["action_types"],
                        inferred={a.id for a in onto.action_types if _is_inferred(a)})

    return {"object_types": objects, "properties": properties, "link_types": links, "action_types": actions}
