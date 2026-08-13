"""Shared configuration, LLM adapters, parsing, rendering, and email helpers."""
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
from typing import Any, Callable
from urllib.parse import urlparse

import requests

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
DEEPSEEK_CHAT_URL = "https://api.deepseek.com/v1/chat/completions"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465
BEIJING = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class Settings:
    news_api_key: str
    deepseek_api_key: str
    openai_api_key: str
    anthropic_api_key: str
    qq_email_password: str
    sender: str
    receiver: str


def load_settings() -> Settings:
    values = {name: os.getenv(name, "").strip() for name in (
        "NEWS_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "QQ_EMAIL_PASSWORD"
    )}
    missing = []
    if not any(values[name] for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")):
        missing.append("至少一个模型密钥（DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY）")
    if not values["QQ_EMAIL_PASSWORD"]:
        missing.append("QQ_EMAIL_PASSWORD")
    if missing:
        raise RuntimeError(f"缺少必要环境变量：{', '.join(missing)}")
    sender = os.getenv("NEWS_SENDER", "3502739363@qq.com").strip()
    receiver = os.getenv("NEWS_RECEIVER", sender).strip()
    if not sender or not receiver:
        raise RuntimeError("NEWS_SENDER 和 NEWS_RECEIVER 不能为空")
    return Settings(values["NEWS_API_KEY"], values["DEEPSEEK_API_KEY"], values["OPENAI_API_KEY"], values["ANTHROPIC_API_KEY"], values["QQ_EMAIL_PASSWORD"], sender, receiver)


def now_beijing() -> datetime:
    return datetime.now(BEIJING)


def _chat_completion(url: str, api_key: str, model: str, prompt: str, *, max_tokens: int, temperature: float) -> str:
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature, "max_tokens": max_tokens},
        timeout=(10, 90),
    )
    response.raise_for_status()
    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("OpenAI 兼容接口返回格式异常") from exc


def _anthropic_completion(api_key: str, model: str, prompt: str, *, max_tokens: int, temperature: float) -> str:
    response = requests.post(
        os.getenv("ANTHROPIC_BASE_URL", ANTHROPIC_MESSAGES_URL),
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": model, "max_tokens": max_tokens, "temperature": temperature, "messages": [{"role": "user", "content": prompt}]},
        timeout=(10, 90),
    )
    response.raise_for_status()
    data = response.json()
    try:
        blocks = data["content"]
        return "\n".join(block["text"] for block in blocks if block.get("type") == "text").strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Anthropic Messages API 返回格式异常") from exc


def call_llm(settings: Settings, prompt: str, *, max_tokens: int = 2000, temperature: float = 0.2) -> str:
    """Call the configured providers in order; continue when quota or API errors occur."""
    configured: dict[str, tuple[str, Callable[..., str]]] = {}
    if settings.deepseek_api_key:
        configured["deepseek"] = (settings.deepseek_api_key, lambda key, model: _chat_completion(DEEPSEEK_CHAT_URL, key, model, prompt, max_tokens=max_tokens, temperature=temperature))
    if settings.openai_api_key:
        configured["openai"] = (settings.openai_api_key, lambda key, model: _chat_completion(os.getenv("OPENAI_BASE_URL", OPENAI_CHAT_URL), key, model, prompt, max_tokens=max_tokens, temperature=temperature))
    if settings.anthropic_api_key:
        configured["anthropic"] = (settings.anthropic_api_key, lambda key, model: _anthropic_completion(key, model, prompt, max_tokens=max_tokens, temperature=temperature))
    order = [item.strip().lower() for item in os.getenv("AI_FALLBACK_PROVIDERS", "deepseek,openai,anthropic").split(",") if item.strip()]
    errors = []
    models = {
        "deepseek": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "openai": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
    }
    for provider in order:
        if provider not in configured:
            continue
        key, caller = configured[provider]
        try:
            print(f"尝试使用模型提供商：{provider}")
            return caller(key, models[provider])
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            errors.append(f"{provider}: {exc}")
            print(f"模型提供商 {provider} 失败，准备回退。")
    raise RuntimeError("所有已配置模型提供商均失败：" + "；".join(errors))


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("AI 未返回 JSON 对象")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("AI 返回的 JSON 不是对象")
    return value


def render_report_sections(text: str) -> str:
    sections = []
    for chunk in text.split("【"):
        if "】" not in chunk:
            continue
        title, content = chunk.split("】", 1)
        safe_title = html.escape(title.strip())
        safe_content = html.escape(content.strip()).replace("\n", "<br>")
        sections.append('<tr><td style="background:#f0f7ff;padding:10px;font-size:16px;font-weight:bold;border-left:4px solid #2196F3;">' + safe_title + '</td></tr>' + '<tr><td style="padding:10px;font-size:14px;line-height:1.6;color:#333;">' + safe_content + '</td></tr>')
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
