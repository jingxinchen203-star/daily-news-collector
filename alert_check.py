"""Check recent public-health news and send an alert only when criteria are met."""
from __future__ import annotations

import html

from news_common import (
    call_deepseek,
    fetch_articles,
    format_articles,
    load_settings,
    now_beijing,
    parse_json_response,
    safe_url,
    send_html_email,
)


def build_prompt(news_text: str) -> str:
    return f"""你是公共卫生信息审核员。请根据以下近24小时新闻，判断是否有需要人工紧急复核的事件。

触发条件仅包括：新闻明确提到感染人数超过30人，或存在对中国境内的直接安全威胁。不要根据标题猜测，不要把“可能”“担忧”“计划检测”当作已发生事实。若信息不足，alert 必须为 false。

只输出一个 JSON 对象，不要 Markdown，不要解释：
{{"alert": false, "reason": "", "infections": 0, "threat_to_china": false}}

新闻材料：
{news_text}"""


def build_alert_html(reason: str, infections: int, threat: bool, articles: list[dict], published_at: str) -> str:
    source_rows = []
    for article in articles[:10]:
        title = html.escape(article.get("title", "无标题"))
        url = html.escape(safe_url(article.get("url", "")), quote=True)
        source_rows.append(f'<li><a href="{url}">{title}</a></li>')
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="font-family:'Microsoft YaHei',Arial,sans-serif;margin:0;padding:20px;background:#fff5f5;">
<div style="max-width:620px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:2px solid #e53935;">
<div style="background:linear-gradient(135deg,#b71c1c,#e53935);padding:20px;text-align:center;"><h1 style="color:#fff;margin:0;font-size:24px;">病毒疫情紧急预警</h1><p style="color:#ffcdd2;margin:8px 0 0;">{published_at}</p></div>
<div style="padding:20px;"><table style="width:100%;border-collapse:collapse;">
<tr><td style="padding:10px;border-bottom:1px solid #eee;font-weight:bold;color:#b71c1c;">触发原因</td><td style="padding:10px;border-bottom:1px solid #eee;">{html.escape(str(reason))}</td></tr>
<tr><td style="padding:10px;border-bottom:1px solid #eee;font-weight:bold;">感染人数参考</td><td style="padding:10px;border-bottom:1px solid #eee;">{html.escape(str(infections))}</td></tr>
<tr><td style="padding:10px;font-weight:bold;">是否威胁中国</td><td style="padding:10px;">{'是，需人工复核' if threat else '暂无直接证据'}</td></tr>
</table><p style="margin-top:16px;padding:12px;background:#fff3e0;border-radius:8px;font-size:13px;color:#e65100;">此邮件仅表示需要尽快人工核查，不构成医疗或公共卫生结论。</p>
<h3 style="font-size:16px;color:#b71c1c;">相关来源</h3><ul style="font-size:13px;line-height:1.8;">{''.join(source_rows) or '<li>暂无来源</li>'}</ul></div></div></body></html>"""


def main() -> None:
    settings = load_settings()
    print("开始执行紧急检查……")
    articles = fetch_articles(settings.news_api_key, hours=24, page_size=20)
    if not articles:
        print("近24小时无可用新闻，跳过预警。")
        return
    result = parse_json_response(call_deepseek(settings.deepseek_api_key, build_prompt(format_articles(articles, limit=20)), max_tokens=500, temperature=0.1))
    alert = result.get("alert") is True
    if not alert:
        print("未达到预警条件。")
        return
    reason = str(result.get("reason") or "AI 未提供原因")
    try:
        infections = max(0, int(result.get("infections") or 0))
    except (TypeError, ValueError):
        infections = 0
    threat = result.get("threat_to_china") is True
    published_at = now_beijing().strftime("%Y-%m-%d %H:%M（北京时间）")
    html_body = build_alert_html(reason, infections, threat, articles, published_at)
    plain_body = f"病毒疫情紧急预警\n触发原因：{reason}\n感染人数参考：{infections}\n是否威胁中国：{'是' if threat else '暂无直接证据'}"
    send_html_email(settings, f"紧急预警：病毒疫情更新 | {published_at}", html_body, plain_body)
    print("预警邮件已发送。")


if __name__ == "__main__":
    main()
