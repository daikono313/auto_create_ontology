"""同一ホスト内をBFSでクロールする。URLパターンごとに取得数を絞り、代表ページだけを集める。"""

import re
import time
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "ontogen/0.1 (+ontology discovery prototype)"


@dataclass
class Page:
    url: str
    pattern: str
    html: str


def url_pattern(url: str) -> str:
    """数字を含むパスセグメントを * に置き換えて、同じテンプレートのページをまとめる。"""
    path = urlparse(url).path or "/"
    segments = ["*" if re.search(r"\d", s) else s for s in path.split("/")]
    return "/".join(segments)


def _load_robots(start_url: str, client: httpx.Client) -> urllib.robotparser.RobotFileParser:
    parsed = urlparse(start_url)
    robots = urllib.robotparser.RobotFileParser()
    try:
        resp = client.get(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
        robots.parse(resp.text.splitlines() if resp.status_code == 200 else [])
    except httpx.HTTPError:
        robots.parse([])
    return robots


def crawl(start_url: str, max_pages: int = 40, per_pattern: int = 3, delay: float = 0.5) -> list[Page]:
    host = urlparse(start_url).netloc
    pages: list[Page] = []
    pattern_counts: dict[str, int] = {}
    queue = [start_url]
    seen = {start_url}

    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=20) as client:
        robots = _load_robots(start_url, client)
        while queue and len(pages) < max_pages:
            url = queue.pop(0)
            pattern = url_pattern(url)
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
                link = urldefrag(urljoin(str(resp.url), a["href"]))[0]
                if urlparse(link).netloc == host and link not in seen:
                    seen.add(link)
                    queue.append(link)
            time.sleep(delay)

    return pages
