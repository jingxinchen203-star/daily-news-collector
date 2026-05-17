import requests, smtplib, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
QQ_PASS = os.getenv("QQ_EMAIL_PASSWORD")
SENDER = "3502739363@qq.com"
RECEIVER = "3502739363@qq.com"
TODAY = datetime.now().strftime("%Y-%m-%d")
TODAY_CN = datetime.now().strftime("%Y年%m月%d日")

# 1. 抓新闻
params = {
    "q": "virus OR outbreak OR 病毒 OR 疫情 OR 感染 OR 人传人",
    "from": TODAY,
    "sortBy": "popularity",
    "pageSize": 15,
    "language": "zh",
    "apiKey": NEWS_API_KEY
}
try:
    resp = requests.get("https://newsapi.org/v2/everything", params=params, timeout=15)
    articles = resp.json().get("articles", [])
    news_list = []
    for a in articles[:10]:
        news_list.append(f"📰 {a.get('title','无标题')}\n   {a.get('description','')}\n   来源：{a.get('url','')}")
    news_text = "\n".join(news_list) if news_list else "（暂无相关新闻）"
except Exception as e:
    news_text = f"新闻获取失败：{str(e)}"

# 2. AI分析
prompt = f"""你是一位病毒学与公共卫生专家。以下是今日（{TODAY_CN}）全球病毒/疫情新闻摘要：

{news_text}

请严格按以下格式输出（不要改变结构，不要加额外说明）：

【疫情概况】
分地区列出主要疫情，重点标注感染>30人的事件。

【动物传染病威胁】
可能由动物传人的病毒风险。

【对中国威胁评估】
是否存在直接威胁。

【专家建议】
通俗建议。

注意：如无数据请注明。用中文。"""
payload = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.3, "max_tokens": 2000
}
try:
    ai_resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
        json=payload, timeout=30
    )
    raw = ai_resp.json()["choices"][0]["message"]["content"]
    # 解析AI输出为HTML
    sections = raw.split("【")
    html_body = ""
    for s in sections:
        s = s.strip()
        if not s: continue
        if "】" in s:
            title, content = s.split("】", 1)
            html_body += f"""
            <tr><td colspan="2" style="background-color:#f0f7ff;padding:10px;font-size:16px;font-weight:bold;border-left:4px solid #2196F3;">
                🦠 {title}
            </td></tr>
            <tr><td colspan="2" style="padding:10px;font-size:14px;line-height:1.6;color:#333;">
                {content.replace(chr(10),'<br>')}
            </td></tr>"""
except Exception as e:
    html_body = f"<tr><td>AI分析失败：{str(e)}</td></tr>"

# 3. 组装HTML邮件
html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:'Microsoft YaHei',Arial,sans-serif;margin:0;padding:20px;background-color:#f5f5f5;">
<div style="max-width:680px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
<div style="background:linear-gradient(135deg,#1a237e,#0d47a1);padding:20px;text-align:center;">
    <h1 style="color:#fff;margin:0;font-size:22px;">🦠 每日全球病毒疫情简报</h1>
    <p style="color:#90caf9;margin:5px 0 0;font-size:14px;">{TODAY_CN}（周六）</p >
</div>
<div style="padding:16px;">
    <p style="font-size:13px;color:#666;margin:0 0 12px;">⏱ 更新时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}（北京时间）</p >
    <p style="font-size:13px;color:#666;margin:0 0 16px;">📊 数据来源：NewsAPI、DeepSeek AI 分析</p >
    <table style="width:100%;border-collapse:collapse;">
        {html_body}
    </table>
</div>
<div style="background:#f8f9fa;padding:12px;text-align:center;font-size:12px;color:#999;">
    本邮件由 AI 自动监测生成 · 数据仅供参考 · {TODAY}
</div>
</div>
</body>
</html>"""

msg = MIMEMultipart("alternative")
msg["Subject"] = f"🦠 每日病毒疫情简报 | {TODAY_CN}"
msg["From"] = SENDER
msg["To"] = RECEIVER
msg.attach(MIMEText("请使用支持HTML的邮箱客户端查看", "plain", "utf-8"))
msg.attach(MIMEText(html, "html", "utf-8"))

with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
    server.login(SENDER, QQ_PASS)
    server.send_message(msg)

print("✅ HTML日报已发送")
