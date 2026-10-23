"""2段階でオントロジーを生成する。

1. ページパターン（テンプレート）ごとに概念候補を抽出する
2. 候補を統合・名寄せして、サイト全体のオントロジーにまとめる
"""

import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from importlib.resources import files
from pathlib import Path

from .llm import call_structured
from .schema import Ontology

GUIDELINES = """\
# Goal
You are a data architect building a *discovery draft* of a business ontology (Palantir Foundry style:
Object Types, Properties, Link Types, Action Types) from a company's website. The draft will be used
before the first client meeting, so it must be grounded and honest about uncertainty.

# Rules
- Model business entities that would become tables/objects in a data platform (e.g. Product, Order,
  Customer, Store). Do NOT model UI artifacts (pages, menus, banners, pagination) as object types.
- Model values that are attributes (price, rating, color) as properties, not object types, unless they
  clearly have their own identity and attributes.
- Infer Action Types from forms, buttons and described processes (e.g. "Add to basket" -> AddToBasket).
  An action may imply an object type that is not displayed (e.g. Basket); include it, and say in its
  description that it is inferred.
- Every object type, link type and action type needs at least one evidence item. `quote` must be copied
  verbatim from the given page data (short, <= 100 chars). Never invent quotes.
- If the page data has `tracking` (GTM / GA4 tags and the event names the page sends), treat those events as
  operations that really happen on this site.
- Put anything you cannot decide from the website (internal processes, data owners, ambiguous
  granularity, missing entities you expect to exist) into `open_questions`.
- IDs are English (ObjectType/ActionType: PascalCase singular; property/link: snake_case).
- Write all descriptions, the summary and open_questions in {lang}.
"""


def _page_type_prompt(pattern: str, digests: list[dict], lang: str) -> str:
    return (
        GUIDELINES.format(lang=lang)
        + f"\n# Task\nThe pages below share the URL pattern `{pattern}` (same page template). "
        "Extract the candidate ontology elements visible on this page type.\n\n# Page data\n"
        + json.dumps(digests, ensure_ascii=False, indent=1)
    )


JOURNEY_GUIDELINES = """\
# Journeys and state machines
- Build `journeys`: the flows a user goes through to reach a goal (e.g. sign in -> view item -> add to wishlist
  -> add to cart -> check out -> purchase complete). Order the steps as they happen. Each step references an
  action_types id; add missing actions (and the objects they create, e.g. Order) as inferred elements.
- Mark a step `observed: true` only when the website shows it (a page, form, button or tracking event). Steps you
  add from typical {domain_hint} flows are `observed: false` and need no evidence. Add an open question for the
  important unobserved steps (e.g. whether guests can check out).
- Set `ga4_event` on actions and steps using the GA4 recommended events below when one matches; otherwise null.
  GA4 event parameters (transaction_id, shipping, tax, items[].item_variant, ...) can suggest properties.
- Build `state_machines` for objects whose lifecycle matters (e.g. Basket, Order, Payment): states, the initial
  state, and which action moves the object between states. Mark `observed` the same way as steps.

# GA4 recommended events (reference vocabulary)
{ga4}
"""


def _merge_prompt(site_map: list[dict], fragments: list[Ontology], lang: str) -> str:
    ga4 = files("ontogen").joinpath("references/ga4_events.yaml").read_text()
    return (
        GUIDELINES.format(lang=lang)
        + "\n# Task\nBelow are candidate ontologies extracted separately from each page type of one website. "
        "Merge them into ONE coherent ontology:\n"
        "- Unify synonyms and duplicates (same concept under different names) into one ID.\n"
        "- Merge properties; drop properties that are really UI noise.\n"
        "- Make sure every link/action references existing object type IDs.\n"
        "- Keep the strongest evidence items (max 3 per element).\n"
        "- Consolidate and deduplicate open_questions; add questions about the business as a whole.\n\n"
        + JOURNEY_GUIDELINES.format(domain_hint="e-commerce", ga4=ga4)
        + "\n"
        "# Site map (URL patterns crawled)\n"
        + json.dumps(site_map, ensure_ascii=False, indent=1)
        + "\n\n# Candidate ontologies\n"
        + json.dumps([f.model_dump() for f in fragments], ensure_ascii=False, indent=1)
    )


def generate(pages: list[dict], work_dir: Path, lang: str = "Japanese", model: str | None = None,
             samples_per_pattern: int = 2, concurrency: int = 4) -> Ontology:
    """pages: [{"url", "pattern", "digest"}]"""
    cache_dir = work_dir / "llm_cache"
    groups: dict[str, list[dict]] = defaultdict(list)
    for p in pages:
        groups[p["pattern"]].append(p)

    site_map = [{"pattern": pat, "pages_crawled": len(ps), "example_titles": [p["digest"]["title"] for p in ps[:3]]}
                for pat, ps in groups.items()]

    def extract(item):
        pattern, ps = item
        prompt = _page_type_prompt(pattern, [p["digest"] for p in ps[:samples_per_pattern]], lang)
        print(f"  extract: {pattern}")
        return call_structured(prompt, Ontology, cache_dir, model)

    with ThreadPoolExecutor(concurrency) as pool:
        fragments = list(pool.map(extract, groups.items()))

    frag_dir = work_dir / "fragments"
    frag_dir.mkdir(parents=True, exist_ok=True)
    for (pattern, _), frag in zip(groups.items(), fragments):
        name = re.sub(r"[^A-Za-z0-9]+", "_", pattern).strip("_") or "root"
        (frag_dir / f"{name}.json").write_text(frag.model_dump_json(indent=2))

    print("  merge")
    return call_structured(_merge_prompt(site_map, fragments, lang), Ontology, cache_dir, model)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def verify_evidence(onto: Ontology, page_texts: dict[str, str]) -> dict:
    """引用が実際にページ本文（またはLLMに渡したページデータ）に存在するかを確認する（ハルシネーション検知）。"""
    norm_texts = {url: _norm(t) for url, t in page_texts.items()}
    all_text = "\n".join(norm_texts.values())
    checked, unverified = 0, []

    elements = [(f"object:{o.id}", o.evidence) for o in onto.object_types]
    elements += [(f"property:{o.id}.{p.name}", p.evidence) for o in onto.object_types for p in o.properties]
    elements += [(f"link:{l.id}", l.evidence) for l in onto.link_types]
    elements += [(f"action:{a.id}", a.evidence) for a in onto.action_types]
    elements += [(f"journey:{j.id}[{i}]", st.evidence) for j in onto.journeys for i, st in enumerate(j.steps, 1)]
    for label, evidence in elements:
        for ev in evidence:
            checked += 1
            quote = _norm(ev.quote).strip(".…")
            if quote not in norm_texts.get(ev.url, all_text) and quote not in all_text:
                unverified.append({"element": label, "url": ev.url, "quote": ev.quote})

    return {"checked": checked, "verified": checked - len(unverified), "unverified": unverified}
