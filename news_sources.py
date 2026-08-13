"""News source adapters for NewsAPI and RSS/Atom feeds."""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

import requests

NEWS_API_URL = "https://newsapi.org/v2/everything"
DEFAULT_QUERY = "virus OR outbreak OR pandemic OR epidemic OR 病毒 OR 疫情 OR 感染"
DEFAULT_RSS_URLS = (
    "https://www.ecdc.europa.eu/en/taxonomy/term/323//feed",
    "https://www.ecdc.europa.eu/en/taxonomy/term/2794/feed",
)


def _as_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _find_text(element: ET.Element, *namespaces_and_tags: str) -> str:
    for tag in namespaces_and_tags:
        child = element.find(tag)
        if child is not None and child.text:
            return " ".join(child.text.split())
    return ""


def parse_feed(content: bytes, feed_url: str, *, since: datetime | None = None) -> list[dict[str, Any]]:
    """Parse common RSS 2.0 and Atom fields into the project's article shape."""
    root = ET.fromstring(content)
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
    articles: list[dict[str, Any]] = []
    for item in items:
        title = _find_text(item, "title", "{http://www.w3.org/2005/Atom}title")
        description = _find_text(item, "description", "summary", "content", "{http://www.w3.org/2005/Atom}summary", "{http://www.w3.org/2005/Atom}content")
        url = _find_text(item, "link", "{http://www.w3.org/2005/Atom}link")
        if not url:
            atom_link = item.find("{http://www.w3.org/2005/Atom}link")
            url = (atom_link.get("href", "") if atom_link is not None else "")
        published = _find_text(item, "pubDate", "published", "updated", "{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated")
        published_at = _as_datetime(published)
        if since and published_at and published_at < since:
            continue
        if title and url and urlparse(url).scheme in {"http", "https"}:
            articles.append({
                "title": title,
                "description": description or "暂无摘要",
                "url": url,
                "source": {"name": urlparse(feed_url).netloc},
                "publishedAt": published_at.isoformat() if published_at else "",
            })
    return articles


def fetch_rss_feed(feed_url: str, *, since: datetime | None = None) -> list[dict[str, Any]]:
    response = requests.get(feed_url, timeout=(10, 30), headers={"User-Agent": "daily-news-collector/1.0"})
    response.raise_for_status()
    return parse_feed(response.content, feed_url, since=since)


def fetch_newsapi(api_key: str, *, hours: int = 24, page_size: int = 20) -> list[dict[str, Any]]:
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    response = requests.get(
        NEWS_API_URL,
        params={
            "q": DEFAULT_QUERY,
            "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sortBy": "publishedAt",
            "pageSize": min(max(page_size, 1), 100),
            "apiKey": api_key,
        },
        timeout=(10, 30),
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "NewsAPI 返回失败"))
    return [article for article in data.get("articles", []) if article.get("title") and article.get("url")]


def fetch_articles(news_api_key: str = "", *, hours: int = 24, page_size: int = 20) -> list[dict[str, Any]]:
    """Fetch all configured sources; one failed source does not hide healthy sources."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    sources: list[dict[str, Any]] = []
    errors: list[str] = []
    if news_api_key.strip():
        try:
            sources.extend(fetch_newsapi(news_api_key, hours=hours, page_size=page_size))
        except requests.RequestException as exc:
            errors.append(f"NewsAPI 网络错误：{exc}")
        except (RuntimeError, ValueError) as exc:
            errors.append(f"NewsAPI 返回错误：{exc}")
    rss_config = os.getenv("NEWS_RSS_URLS", "").strip()
    rss_urls = [url.strip() for url in (rss_config.split(",") if rss_config else DEFAULT_RSS_URLS) if url.strip()]
    for feed_url in rss_urls:
        try:
            sources.extend(fetch_rss_feed(feed_url, since=since))
        except (requests.RequestException, ET.ParseError, ValueError) as exc:
            errors.append(f"RSS {feed_url} 失败：{exc}")
    unique: dict[str, dict[str, Any]] = {}
    for article in sources:
        unique[article["url"]] = article
    if not unique and errors:
        raise RuntimeError("所有新闻源均失败：" + "；".join(errors))
    return list(unique.values())[: max(page_size, 1)]


def format_articles(articles: list[dict[str, Any]], limit: int = 10) -> str:
    if not articles:
        return "（近24小时暂无相关新闻）"
    rows = []
    for index, article in enumerate(articles[:limit], 1):
        rows.append(
            f"[{index}] 标题：{article.get('title', '无标题')}\n"
            f"来源：{(article.get('source') or {}).get('name', '未知来源')}\n"
            f"摘要：{article.get('description') or '暂无摘要'}\n"
            f"链接：{article.get('url', '')}"
        )
    return "\n\n".join(rows)
