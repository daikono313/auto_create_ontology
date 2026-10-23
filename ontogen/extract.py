"""HTMLから、オントロジー抽出に効く要素（見出し・表・フォーム・構造化データなど）を要約する。"""

import json
import re

from bs4 import BeautifulSoup, Comment

MAX_TEXT_CHARS = 1500
MAX_LINK_TEXTS = 40
MAX_CLASS_HINTS = 40


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def tracking(html: str) -> dict:
    """計測タグ（GTM・GA4）の ID と、スクリプトが送信しているイベント名を抜き出す（ADR 0010）。"""
    events = set(re.findall(r"""gtag\(\s*['"]event['"]\s*,\s*['"]([\w.-]+)['"]""", html))
    for push in re.findall(r"dataLayer\.push\(([^;]{0,500})", html):
        events.update(re.findall(r"""['"]?event['"]?\s*:\s*['"]([\w.-]+)['"]""", push))
    # Shopify のカスタムピクセルなど、analytics.subscribe("product_viewed", ...) の形
    events.update(re.findall(r"""analytics\.subscribe\(\s*['"]([\w.-]+)['"]""", html))
    return {
        "gtm_container_ids": sorted(set(re.findall(r"\bGTM-[A-Z0-9]{4,}\b", html))),
        "ga4_measurement_ids": sorted(set(re.findall(r"\bG-[A-Z0-9]{6,}\b", html))),
        "events": sorted(events),
    }


def page_text(html: str) -> str:
    """根拠引用の検証に使う、ページ全体の可視テキスト。"""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    return _clean(soup.get_text(" "))


def digest(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    tags = tracking(html)

    json_ld = []
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            json_ld.append(json.loads(s.string or ""))
        except json.JSONDecodeError:
            pass

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()

    breadcrumb = soup.select_one(".breadcrumb, nav[aria-label*=readcrumb], [itemtype*=BreadcrumbList]")
    if breadcrumb:
        items = [t for li in breadcrumb.find_all("li") if (t := _clean(li.get_text(" ")))]
        breadcrumb = " > ".join(items) if items else _clean(breadcrumb.get_text(" "))

    tables = []
    for table in soup.find_all("table")[:5]:
        rows = []
        for tr in table.find_all("tr")[:30]:
            cells = [_clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
            if any(cells):
                rows.append(cells)
        tables.append(rows)

    forms = []
    for form in soup.find_all("form")[:10]:
        fields = [f.get("name") or f.get("type") for f in form.find_all(["input", "select", "textarea"])]
        buttons = [_clean(b.get_text(" ")) or b.get("value", "") for b in form.find_all(["button", "input"]) if b.name == "button" or b.get("type") == "submit"]
        forms.append({"action": form.get("action"), "method": form.get("method", "get"), "fields": [f for f in fields if f], "buttons": buttons})
    # 同じフォームが商品ごとに繰り返されるので重複を除く
    forms = [json.loads(f) for f in dict.fromkeys(json.dumps(f, ensure_ascii=False) for f in forms)]

    link_texts = list(dict.fromkeys(t for a in soup.find_all("a") if (t := _clean(a.get_text(" ")))))

    main = soup.find("main") or soup.find(id="content") or soup.find(role="main") or soup.body or soup
    # 星評価や在庫状態など、テキストではなく class や alt に値が入っていることがある
    class_hints = list(dict.fromkeys(" ".join(e["class"]) for e in main.find_all(class_=True) if len(e["class"]) >= 2))
    images = list(dict.fromkeys(f"alt={img.get('alt', '')!r} src={img.get('src', '')}" for img in main.find_all("img")))
    itemprops = list(dict.fromkeys(f"{e['itemprop']}={_clean(e.get('content') or e.get_text(' '))[:80]}" for e in soup.find_all(itemprop=True)))

    return {
        "url": url,
        "title": _clean(soup.title.get_text()) if soup.title else "",
        "breadcrumb": breadcrumb,
        "headings": [f"{h.name}: {_clean(h.get_text(' '))}" for h in soup.find_all(["h1", "h2", "h3"])][:30],
        "tables": tables,
        "forms": forms,
        "json_ld": json_ld,
        "tracking": tags if any(tags.values()) else None,
        "itemprops": itemprops[:MAX_CLASS_HINTS],
        "class_hints": class_hints[:MAX_CLASS_HINTS],
        "images": images[:5],
        "link_texts": link_texts[:MAX_LINK_TEXTS],
        "main_text": _clean(main.get_text(" "))[:MAX_TEXT_CHARS],
    }
