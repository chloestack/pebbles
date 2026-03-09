"""Pebbles — Daily world news crawler with Korean translation."""
import json
import os
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

OUTPUT = Path(__file__).parent / "public" / "data" / "news.json"
ITEMS_PER_SOURCE = 8

SOURCES = [
    # World
    {"id": "reuters", "name": "Reuters", "cat": "world", "lang": "en",
     "url": "https://news.google.com/rss/search?q=source:reuters.com+when:1d&hl=en-US&gl=US&ceid=US:en"},
    {"id": "ap", "name": "Associated Press", "cat": "world", "lang": "en",
     "url": "https://news.google.com/rss/search?q=source:apnews.com+when:1d&hl=en-US&gl=US&ceid=US:en"},
    {"id": "bbc", "name": "BBC News", "cat": "world", "lang": "en",
     "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"id": "nyt", "name": "The New York Times", "cat": "world", "lang": "en",
     "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"},
    {"id": "guardian", "name": "The Guardian", "cat": "world", "lang": "en",
     "url": "https://www.theguardian.com/world/rss"},
    # Business
    {"id": "bloomberg", "name": "Bloomberg", "cat": "business", "lang": "en",
     "url": "https://news.google.com/rss/search?q=source:bloomberg.com+when:1d&hl=en-US&gl=US&ceid=US:en"},
    {"id": "ft", "name": "Financial Times", "cat": "business", "lang": "en",
     "url": "https://news.google.com/rss/search?q=source:ft.com+when:1d&hl=en-US&gl=US&ceid=US:en"},
    {"id": "wsj", "name": "The Wall Street Journal", "cat": "business", "lang": "en",
     "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml"},
    {"id": "economist", "name": "The Economist", "cat": "business", "lang": "en",
     "url": "https://news.google.com/rss/search?q=source:economist.com+when:1d&hl=en-US&gl=US&ceid=US:en"},
    {"id": "nikkei", "name": "Nikkei Asia", "cat": "business", "lang": "en",
     "url": "https://news.google.com/rss/search?q=source:asia.nikkei.com+when:1d&hl=en-US&gl=US&ceid=US:en"},
    {"id": "scmp", "name": "South China Morning Post", "cat": "business", "lang": "en",
     "url": "https://news.google.com/rss/search?q=source:scmp.com+when:1d&hl=en-US&gl=US&ceid=US:en"},
    # Korea
    {"id": "yonhap", "name": "연합뉴스", "cat": "korea", "lang": "ko",
     "url": "https://www.yna.co.kr/rss/all.xml"},
    {"id": "hankyung", "name": "한국경제", "cat": "korea", "lang": "ko",
     "url": "https://www.hankyung.com/feed/all-news"},
    {"id": "mk", "name": "매일경제", "cat": "korea", "lang": "ko",
     "url": "https://www.mk.co.kr/rss/30000001/"},
    {"id": "hani", "name": "한겨레신문", "cat": "korea", "lang": "ko",
     "url": "https://www.hani.co.kr/rss/headline/"},
    # Tech
    {"id": "techcrunch", "name": "TechCrunch", "cat": "tech", "lang": "en",
     "url": "https://techcrunch.com/feed/"},
    {"id": "verge", "name": "The Verge", "cat": "tech", "lang": "en",
     "url": "https://www.theverge.com/rss/index.xml"},
    {"id": "wired", "name": "Wired", "cat": "tech", "lang": "en",
     "url": "https://www.wired.com/feed/rss"},
]


def fetch_rss(url: str, timeout: int = 10) -> str:
    """Fetch RSS XML content."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Pebbles/1.0"
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_date(date_str: str) -> str:
    """Parse various date formats to ISO string."""
    if not date_str:
        return datetime.now(timezone.utc).isoformat()
    try:
        return parsedate_to_datetime(date_str).isoformat()
    except Exception:
        pass
    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(date_str, fmt).isoformat()
        except ValueError:
            continue
    return datetime.now(timezone.utc).isoformat()


def strip_html(text: str) -> str:
    """Remove HTML tags."""
    return re.sub(r"<[^>]+>", "", text).strip()


def extract_image(entry: ET.Element, ns: dict) -> str:
    """Try to extract image URL from RSS item."""
    # media:content
    media = entry.find("media:content", ns) or entry.find("{http://search.yahoo.com/mrss/}content")
    if media is not None:
        return media.get("url", "")
    # media:thumbnail
    thumb = entry.find("media:thumbnail", ns) or entry.find("{http://search.yahoo.com/mrss/}thumbnail")
    if thumb is not None:
        return thumb.get("url", "")
    # enclosure
    enc = entry.find("enclosure")
    if enc is not None and "image" in enc.get("type", ""):
        return enc.get("url", "")
    # description img tag
    desc = entry.findtext("description") or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc)
    if m:
        return m.group(1)
    return ""


def parse_feed(source: dict) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    try:
        xml_text = fetch_rss(source["url"])
    except Exception as e:
        print(f"  [FAIL] {source['name']}: {e}")
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        print(f"  [FAIL] {source['name']}: XML parse error")
        return []

    ns = {
        "media": "http://search.yahoo.com/mrss/",
        "atom": "http://www.w3.org/2005/Atom",
        "dc": "http://purl.org/dc/elements/1.1/",
    }

    articles = []

    # RSS 2.0
    items = root.findall(".//item")
    # Atom
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    for item in items[:ITEMS_PER_SOURCE]:
        # RSS 2.0
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        desc = item.findtext("description") or ""
        pub = item.findtext("pubDate") or item.findtext("pubdate") or ""
        # Atom fallback
        if not title:
            title = item.findtext("{http://www.w3.org/2005/Atom}title") or ""
        if not link:
            link_el = item.find("{http://www.w3.org/2005/Atom}link")
            if link_el is not None:
                link = link_el.get("href", "")
        if not pub:
            pub = (item.findtext("{http://www.w3.org/2005/Atom}published")
                   or item.findtext("{http://www.w3.org/2005/Atom}updated")
                   or item.findtext("{http://purl.org/dc/elements/1.1/}date")
                   or "")

        if not title.strip():
            continue

        image = extract_image(item, ns)

        articles.append({
            "source": source["id"],
            "sourceName": source["name"],
            "category": source["cat"],
            "title": strip_html(title.strip()),
            "titleOriginal": "",
            "description": strip_html(desc)[:200],
            "link": link.strip(),
            "pubDate": parse_date(pub.strip()),
            "image": image,
        })

    print(f"  [OK] {source['name']}: {len(articles)} articles")
    return articles


def translate_batch(titles: list[str]) -> list[str]:
    """Translate a batch of English titles to Korean using Claude CLI."""
    if not titles:
        return []

    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
    prompt = (
        "다음 영어 뉴스 제목을 자연스러운 한국어 뉴스 제목으로 번역하세요. "
        "번호와 번역만 출력하세요. 설명이나 부가 텍스트 없이 번역만.\n\n"
        f"{numbered}"
    )

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)

    try:
        result = subprocess.run(
            ["claude", "-p", "--model", "claude-haiku-4-5-20251001", prompt],
            capture_output=True, text=True, timeout=120, env=env,
        )
        if result.returncode != 0:
            print(f"  [TRANSLATE FAIL] {result.stderr[:200]}")
            return titles  # Return originals on failure

        lines = result.stdout.strip().splitlines()
        translated = []
        for line in lines:
            # Remove numbering: "1. 번역문" → "번역문"
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
            if cleaned:
                translated.append(cleaned)

        if len(translated) == len(titles):
            return translated
        else:
            print(f"  [TRANSLATE MISMATCH] Expected {len(titles)}, got {len(translated)}")
            return titles
    except Exception as e:
        print(f"  [TRANSLATE ERROR] {e}")
        return titles


def translate_articles(articles: list[dict]):
    """Translate all English articles in batches of 20."""
    en_articles = [a for a in articles if a["source"] not in
                   ("yonhap", "hankyung", "mk", "hani")]

    print(f"\nTranslating {len(en_articles)} English articles...")

    for i in range(0, len(en_articles), 20):
        batch = en_articles[i:i + 20]
        titles = [a["title"] for a in batch]
        translated = translate_batch(titles)

        for article, ko_title in zip(batch, translated):
            article["titleOriginal"] = article["title"]
            article["title"] = ko_title

        print(f"  Batch {i // 20 + 1}: {len(batch)} titles translated")


def main():
    print("=== Pebbles News Crawler ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sources: {len(SOURCES)}\n")

    all_articles = []
    for source in SOURCES:
        articles = parse_feed(source)
        all_articles.extend(articles)

    print(f"\nTotal articles fetched: {len(all_articles)}")

    translate_articles(all_articles)

    # Sort by date (newest first)
    all_articles.sort(key=lambda a: a["pubDate"], reverse=True)

    # Save
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "articles": all_articles,
        "updated": datetime.now(timezone.utc).isoformat(),
        "sourceCount": len(SOURCES),
    }
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {len(all_articles)} articles to {OUTPUT}")


if __name__ == "__main__":
    main()
