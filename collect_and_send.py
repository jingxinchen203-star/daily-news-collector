"""Collect recent public-health news, summarize it, and send a daily email."""
from __future__ import annotations

import html

from news_common import (
    call_deepseek,
    fetch_articles,
    format_articles,
    load_settings,
    now_beijing,
    render_report_sections,
    safe_url,
    send_html_email,
)


def build_prompt(news_text: str, date_text: str) -> str:
    return f"""你是一位病毒学与公共卫生信息分析师。请基于下面近24小时的公开新闻，先核对新闻中的时间、地点和数字，再用简体中文生成一份克制、可核查的日报。不要把新闻报道等同于确诊事实；无法确认的内容必须标注“报道未证实”或“暂无数据”。

日期：{date_text}
新闻材料：
{news_text}

请严格使用以下四个分段标题，不要添加其他标题：
【疫情概况】按地区概括主要事件，列出新闻明确提到的病例或死亡数字；没有明确数字时写“暂无数据”。
【动物传染病威胁】只说明有来源支持的动物传人线索，并区分已确认与推测。
【对中国威胁评估】说明是否有直接证据，避免无依据的恐慌性判断。
【专家建议】给出普通读者可执行的、非诊断性的健康信息，并提醒以当地卫生部门和专业医生意见为准。

所有结论都必须严格来自新闻材料；不要补写新闻中没有的事实。"""


def build_html(report: str, articles: list[dict], generated_at: str) -> str:
    links = []
    for article in articles[:10]:
        title = html.escape(article.get("title", "无标题"))
        source = html.escape((article.get("source") or {}).get("name", "未知来源"))
        url = html.escape(safe_url(article.get("url", "")), quote=True)
        links.append(f'<li><a href="{url}">{title}</a>（{source}）</li>')
    sources = "".join(links) or "<li>暂无可用来源</li>"
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="font-family:'Microsoft YaHei',Arial,sans-serif;margin:0;padding:20px;background:#f5f7fb;">
<div style="max-width:680px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);">
<div style="background:linear-gradient(135deg,#1a237e,#0d47a1);padding:20px;text-align:center;">
<h1 style="color:#fff;margin:0;font-size:22px;">每日全球病毒疫情简报</h1>
<p style="color:#bbdefb;margin:8px 0 0;font-size:14px;">{generated_at}</p></div>
<div style="padding:16px;"><p style="font-size:13px;color:#666;margin:0 0 16px;">数据范围：近24小时公开新闻；报告由 AI 辅助整理，仅供信息参考。</p>
<table style="width:100%;border-collapse:collapse;">{render_report_sections(report)}</table>
<h3 style="font-size:16px;color:#1a237e;border-bottom:1px solid #eee;padding-bottom:8px;">原始新闻来源</h3>
<ul style="font-size:13px;line-height:1.8;padding-left:20px;">{sources}</ul></div>
<div style="background:#f8f9fa;padding:12px;text-align:center;font-size:12px;color:#888;">请以当地卫生部门和专业医生的最新意见为准。</div>
</div></body></html>"""


def main() -> None:
    settings = load_settings()
    generated_at = now_beijing().strftime("%Y年%m月%d日 %H:%M（北京时间）")
    print("开始生成每日病毒疫情简报……")
    articles = fetch_articles(settings.news_api_key, hours=24, page_size=20)
    news_text = format_articles(articles, limit=10)
    report = call_deepseek(settings.deepseek_api_key, build_prompt(news_text, generated_at), max_tokens=2200)
    html_body = build_html(report, articles, generated_at)
    plain_body = f"每日全球病毒疫情简报\n{generated_at}\n\n{report}\n\n原始新闻：\n{news_text}"
    send_html_email(settings, f"每日病毒疫情简报 | {now_beijing():%Y-%m-%d}", html_body, plain_body)
    print(f"日报已发送，共处理 {len(articles[:10])} 条新闻。")


if __name__ == "__main__":
    main()
