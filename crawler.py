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

KO_SOURCES = {"yonhap", "hankyung", "mk", "hani"}


def fetch_rss(url: str, timeout: int = 10) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Pebbles/1.0"
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_date(date_str: str) -> str:
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
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def extract_image(entry: ET.Element, ns: dict) -> str:
    media = entry.find("media:content", ns) or entry.find("{http://search.yahoo.com/mrss/}content")
    if media is not None:
        return media.get("url", "")
    thumb = entry.find("media:thumbnail", ns) or entry.find("{http://search.yahoo.com/mrss/}thumbnail")
    if thumb is not None:
        return thumb.get("url", "")
    enc = entry.find("enclosure")
    if enc is not None and "image" in enc.get("type", ""):
        return enc.get("url", "")
    desc = entry.findtext("description") or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc)
    if m:
        return m.group(1)
    return ""


def extract_content(item: ET.Element) -> str:
    """Extract the longest content available from RSS item."""
    candidates = []
    # content:encoded (often has full article)
    for tag in [
        "{http://purl.org/rss/1.0/modules/content/}encoded",
        "content:encoded",
    ]:
        text = item.findtext(tag)
        if text:
            candidates.append(strip_html(text))
    # Atom content
    content_el = item.find("{http://www.w3.org/2005/Atom}content")
    if content_el is not None:
        text = content_el.text or ET.tostring(content_el, encoding="unicode", method="text")
        if text:
            candidates.append(strip_html(text))
    # description / summary
    for tag in ["description", "{http://www.w3.org/2005/Atom}summary"]:
        text = item.findtext(tag)
        if text:
            candidates.append(strip_html(text))
    if not candidates:
        return ""
    # Return the longest one
    return max(candidates, key=len)


def parse_feed(source: dict) -> list[dict]:
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
        "content": "http://purl.org/rss/1.0/modules/content/",
    }

    articles = []
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    for item in items[:ITEMS_PER_SOURCE]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        desc = item.findtext("description") or ""
        pub = item.findtext("pubDate") or item.findtext("pubdate") or ""

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
        content = extract_content(item)
        short_desc = strip_html(desc)[:300] if desc else content[:300]

        articles.append({
            "source": source["id"],
            "sourceName": source["name"],
            "category": source["cat"],
            "title": strip_html(title.strip()),
            "titleOriginal": "",
            "description": short_desc,
            "descriptionOriginal": "",
            "content": content[:2000],
            "contentOriginal": "",
            "link": link.strip(),
            "pubDate": parse_date(pub.strip()),
            "image": image,
        })

    print(f"  [OK] {source['name']}: {len(articles)} articles")
    return articles


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------

def _call_claude(prompt: str, timeout: int = 120) -> str:
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    result = subprocess.run(
        ["claude", "-p", "--model", "claude-haiku-4-5-20251001", prompt],
        capture_output=True, text=True, timeout=timeout, env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:200])
    return result.stdout.strip()


def translate_numbered(texts: list[str], context: str = "뉴스 제목") -> list[str]:
    """Translate a numbered list via Claude. Returns originals on failure."""
    if not texts:
        return []
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
    prompt = (
        f"다음 영어 {context}을(를) 자연스러운 한국어로 번역하세요. "
        "번호와 번역만 출력하세요. 설명이나 부가 텍스트 없이 번역만.\n\n"
        f"{numbered}"
    )
    try:
        raw = _call_claude(prompt, timeout=180)
        lines = raw.strip().splitlines()
        translated = []
        for line in lines:
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
            if cleaned:
                translated.append(cleaned)
        if len(translated) == len(texts):
            return translated
        print(f"    [MISMATCH] expected {len(texts)}, got {len(translated)}")
    except Exception as e:
        print(f"    [ERROR] {e}")
    return texts


def translate_content_batch(contents: list[str]) -> list[str]:
    """Translate longer content paragraphs via Claude."""
    if not contents:
        return []
    separator = "\n===NEXT===\n"
    joined = separator.join(contents)
    prompt = (
        "다음 영어 뉴스 본문들을 자연스러운 한국어로 번역하세요. "
        "각 본문은 ===NEXT=== 로 구분되어 있습니다. "
        "번역도 동일하게 ===NEXT=== 로 구분하여 출력하세요. "
        "설명 없이 번역만 출력.\n\n"
        f"{joined}"
    )
    try:
        raw = _call_claude(prompt, timeout=180)
        parts = raw.split("===NEXT===")
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) == len(contents):
            return parts
        print(f"    [CONTENT MISMATCH] expected {len(contents)}, got {len(parts)}")
    except Exception as e:
        print(f"    [CONTENT ERROR] {e}")
    return contents


def translate_articles(articles: list[dict]):
    """Translate titles, descriptions, and content for all English articles."""
    en_articles = [a for a in articles if a["source"] not in KO_SOURCES]
    print(f"\nTranslating {len(en_articles)} English articles...")

    batch_size = 15

    # 1) Translate titles
    print("\n  [Phase 1] Translating titles...")
    for i in range(0, len(en_articles), batch_size):
        batch = en_articles[i:i + batch_size]
        titles = [a["title"] for a in batch]
        translated = translate_numbered(titles, "뉴스 제목")
        for article, ko in zip(batch, translated):
            article["titleOriginal"] = article["title"]
            article["title"] = ko
        print(f"    Batch {i // batch_size + 1}: {len(batch)} titles")

    # 2) Translate descriptions
    print("\n  [Phase 2] Translating descriptions...")
    for i in range(0, len(en_articles), batch_size):
        batch = en_articles[i:i + batch_size]
        descs = [a["description"] for a in batch if a["description"]]
        batch_with_desc = [a for a in batch if a["description"]]
        if not descs:
            continue
        translated = translate_numbered(descs, "뉴스 요약")
        for article, ko in zip(batch_with_desc, translated):
            article["descriptionOriginal"] = article["description"]
            article["description"] = ko
        print(f"    Batch {i // batch_size + 1}: {len(batch_with_desc)} descriptions")

    # 3) Translate content (longer text, smaller batches)
    print("\n  [Phase 3] Translating content...")
    content_batch_size = 5
    en_with_content = [a for a in en_articles if a["content"] and len(a["content"]) > 50]
    for i in range(0, len(en_with_content), content_batch_size):
        batch = en_with_content[i:i + content_batch_size]
        contents = [a["content"] for a in batch]
        translated = translate_content_batch(contents)
        for article, ko in zip(batch, translated):
            article["contentOriginal"] = article["content"]
            article["content"] = ko
        print(f"    Batch {i // content_batch_size + 1}: {len(batch)} articles")


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

    # Sort by date (newest first), assign IDs
    all_articles.sort(key=lambda a: a["pubDate"], reverse=True)
    for idx, article in enumerate(all_articles):
        article["id"] = idx

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
