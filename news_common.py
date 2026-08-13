"""Shared helpers for the daily news report and urgent alert jobs."""
from __future__ import annotations

import html
import json
import os
import re
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any
from urllib.parse import urlparse

import requests

NEWS_API_URL = "https://newsapi.org/v2/everything"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465
DEFAULT_QUERY = "virus OR outbreak OR pandemic OR epidemic OR 病毒 OR 疫情 OR 感染"
BEIJING = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class Settings:
    news_api_key: str
    deepseek_api_key: str
    qq_email_password: str
    sender: str
    receiver: str


def load_settings() -> Settings:
    """Load and validate secrets without printing their values."""
    values = {
        "NEWS_API_KEY": os.getenv("NEWS_API_KEY", "").strip(),
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY", "").strip(),
        "QQ_EMAIL_PASSWORD": os.getenv("QQ_EMAIL_PASSWORD", "").strip(),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(f"缺少必要环境变量：{', '.join(missing)}")
    sender = os.getenv("NEWS_SENDER", "3502739363@qq.com").strip()
    receiver = os.getenv("NEWS_RECEIVER", sender).strip()
    if not sender or not receiver:
        raise RuntimeError("NEWS_SENDER 和 NEWS_RECEIVER 不能为空")
    return Settings(values["NEWS_API_KEY"], values["DEEPSEEK_API_KEY"], values["QQ_EMAIL_PASSWORD"], sender, receiver)


def now_beijing() -> datetime:
    return datetime.now(BEIJING)


def fetch_articles(api_key: str, *, hours: int = 24, page_size: int = 20) -> list[dict[str, Any]]:
    """Fetch recent articles and fail loudly on provider/API errors."""
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    params = {
        "q": DEFAULT_QUERY,
        "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sortBy": "publishedAt",
        "pageSize": min(max(page_size, 1), 100),
        "apiKey": api_key,
    }
    response = requests.get(NEWS_API_URL, params=params, timeout=(10, 30))
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "NewsAPI 返回失败"))
    return [article for article in data.get("articles", []) if article.get("title") and article.get("url")]


def format_articles(articles: list[dict[str, Any]], limit: int = 10) -> str:
    if not articles:
        return "（近24小时暂无相关新闻）"
    rows = []
    for index, article in enumerate(articles[:limit], 1):
        title = article.get("title", "无标题")
        description = article.get("description") or "暂无摘要"
        source = (article.get("source") or {}).get("name", "未知来源")
        url = article.get("url", "")
        rows.append(f"[{index}] 标题：{title}\n来源：{source}\n摘要：{description}\n链接：{url}")
    return "\n\n".join(rows)


def call_deepseek(api_key: str, prompt: str, *, max_tokens: int = 2000, temperature: float = 0.2) -> str:
    payload = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = requests.post(
        DEEPSEEK_API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=(10, 90),
    )
    response.raise_for_status()
    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("DeepSeek 返回格式异常") from exc


def parse_json_response(text: str) -> dict[str, Any]:
    """Accept plain JSON or a JSON object wrapped in a Markdown code fence."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("AI 未返回 JSON 对象")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("AI 返回的 JSON 不是对象")
    return value


def render_report_sections(text: str) -> str:
    """Convert the model's 【标题】 sections to escaped email rows."""
    sections = []
    for chunk in text.split("【"):
        if "】" not in chunk:
            continue
        title, content = chunk.split("】", 1)
        safe_title = html.escape(title.strip())
        safe_content = html.escape(content.strip()).replace("\n", "<br>")
        sections.append(
            '<tr><td style="background:#f0f7ff;padding:10px;font-size:16px;'
            f'font-weight:bold;border-left:4px solid #2196F3;">{safe_title}</td></tr>'
            f'<tr><td style="padding:10px;font-size:14px;line-height:1.6;color:#333;">{safe_content}</td></tr>'
        )
    return "".join(sections) or '<tr><td style="padding:10px;">AI 未生成可识别的报告分段。</td></tr>'


def safe_url(url: str) -> str:
    parsed = urlparse(url)
    return url if parsed.scheme in {"http", "https"} else "#"


def send_html_email(settings: Settings, subject: str, html_body: str, plain_body: str) -> None:
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.sender
    message["To"] = settings.receiver
    message.attach(MIMEText(plain_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.login(settings.sender, settings.qq_email_password)
        server.send_message(message)
