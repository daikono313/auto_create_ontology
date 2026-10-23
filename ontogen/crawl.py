"""同一ホスト内をBFSでクロールする。URLパターンごとに取得数を絞り、代表ページだけを集める。

範囲の限定とスラッグURLのまとめ方は ADR 0012 を参照。
"""

import posixpath
import re
import time
import urllib.robotparser
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "ontogen/0.1 (+ontology discovery prototype)"
# 同じ親パスの下に、これ以上の種類の子が見つかったら、子のセグメントを * にまとめる
SIBLING_THRESHOLD = 5


@dataclass
class Page:
    url: str
    pattern: str
    html: str


def url_pattern(url: str, children: dict[str, set[str]] | None = None) -> str:
    """同じテンプレートのページを1つのパターンにまとめる。

    数字を含むセグメントは * にする（/catalogue/a-light-in-the-attic_1000/ など）。
    children（親パス → 見つかった子のセグメント）を渡すと、子が SIBLING_THRESHOLD 種類以上ある親の下の
    最後のセグメントも * にする（/products/<スラッグ> など）。トップ直下のセグメントはまとめない。
    """
    path = urlparse(url).path or "/"
    segments = path.rstrip("/").split("/")
    pattern = ["*" if re.search(r"\d", s) else s for s in segments]
    parent = "/".join(segments[:-1])
    if children is not None and len(segments) > 2 and len(children.get(parent, ())) >= SIBLING_THRESHOLD:
        pattern[-1] = "*"
    trailing = "/" if path.endswith("/") and path != "/" else ""
    return ("/".join(pattern) or "/") + trailing


def default_scope(start_url: str) -> str:
    """開始URLのパス（ファイル名で終わるならそのディレクトリ）を、クロールの範囲にする。"""
    path = urlparse(start_url).path or "/"
    if "." in path.rsplit("/", 1)[-1]:
        path = posixpath.dirname(path)
    return path.rstrip("/") or "/"


def _in_scope(url: str, scope: str) -> bool:
    path = urlparse(url).path or "/"
    return scope == "/" or path == scope or path.startswith(scope + "/")


def _normalize(url: str) -> str:
    """フラグメントとクエリ文字列を除く（並べ替え・絞り込み・バリエーション指定のURLを同じページとみなす）。"""
    return urlparse(url)._replace(query="", fragment="").geturl()


def _load_robots(start_url: str, client: httpx.Client) -> urllib.robotparser.RobotFileParser:
    parsed = urlparse(start_url)
    robots = urllib.robotparser.RobotFileParser()
    try:
        resp = client.get(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
        robots.parse(resp.text.splitlines() if resp.status_code == 200 else [])
    except httpx.HTTPError:
        robots.parse([])
    return robots


def crawl(start_url: str, max_pages: int = 40, per_pattern: int = 3, delay: float = 0.5,
          scope: str | None = None) -> list[Page]:
    host = urlparse(start_url).netloc
    scope = scope or default_scope(start_url)
    print(f"  範囲: {host}{scope}")
    pages: list[Page] = []
    pattern_counts: dict[str, int] = {}
    children: dict[str, set[str]] = defaultdict(set)
    queue = [start_url]
    seen = {start_url}

    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=20) as client:
        robots = _load_robots(start_url, client)
        while queue and len(pages) < max_pages:
            url = queue.pop(0)
            pattern = url_pattern(url, children)
            if pattern_counts.get(pattern, 0) >= per_pattern or not robots.can_fetch(USER_AGENT, url):
                continue
            try:
                resp = client.get(url)
            except httpx.HTTPError as e:
                print(f"  skip {url}: {e}")
                continue
            if resp.status_code != 200 or "text/html" not in resp.headers.get("content-type", ""):
                continue

            pages.append(Page(url=str(resp.url), pattern=pattern, html=resp.text))
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            print(f"  [{len(pages)}/{max_pages}] {url}")

            for a in BeautifulSoup(resp.text, "lxml").find_all("a", href=True):
                link = _normalize(urljoin(str(resp.url), a["href"]))
                if urlparse(link).netloc != host or not _in_scope(link, scope) or link in seen:
                    continue
                seen.add(link)
                queue.append(link)
                segments = (urlparse(link).path or "/").rstrip("/").split("/")
                children["/".join(segments[:-1])].add(segments[-1])
            time.sleep(delay)

    return pages
