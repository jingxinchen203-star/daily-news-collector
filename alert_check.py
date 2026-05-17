import requests, smtplib, os, json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
QQ_PASS = os.getenv("QQ_EMAIL_PASSWORD")
SENDER = "3502739363@qq.com"
RECEIVER = "3502739363@qq.com"
now = datetime.now()

print("开始执行紧急检查...")
today = now.strftime("%Y-%m-%d")
params = {
    "q": "virus OR outbreak OR pandemic OR 病毒 OR 疫情 OR 感染",
    "from": today, "sortBy": "publishedAt", "pageSize": 10,
    # 不限语言
    "apiKey": NEWS_API_KEY
}
try:
    resp = requests.get("https://newsapi.org/v2/everything", params=params, timeout=15)
    articles = resp.json().get("articles", [])
    if not articles:
        print("无新新闻，跳过")
        exit(0)
    news_text = ""
    for a in articles:
        news_text += f"{a.get('title','')} {a.get('description','')}\n"
except Exception as e:
    print(f"新闻获取失败：{e}"); exit(1)

prompt = f"""注意：以下新闻可能包含英文内容，请先翻译成中文再判断。reason字段用中文描述。

根据以下最新病毒/疫情新闻，判断是否存在需要紧急关注的严重事件。严重事件定义为：感染人数超过30人，或直接威胁中国境内安全。

请只输出一个JSON对象，不要附加任何其他文字：
{{"alert": false, "reason": "", "infections": 0, "threat_to_china": false}}

新闻内容：
{news_text}"""
payload = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.1, "max_tokens": 500
}
try:
    ai_resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
        json=payload, timeout=30
    )
    result = json.loads(ai_resp.json()["choices"][0]["message"]["content"])
except Exception as e:
    print(f"AI分析失败：{e}"); exit(1)

if result.get("alert") == True:
    reason = result.get("reason", "未知")
    infections = result.get("infections", 0)
    threat = result.get("threat_to_china", False)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:'Microsoft YaHei',sans-serif;margin:0;padding:20px;background:#fff5f5;">
<div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:2px solid #e53935;">
<div style="background:linear-gradient(135deg,#b71c1c,#e53935);padding:20px;text-align:center;">
    <h1 style="color:#fff;margin:0;font-size:24px;">🚨 病毒疫情紧急预警</h1>
    <p style="color:#ffcdd2;margin:5px 0 0;">{now.strftime('%Y-%m-%d %H:%M')} 发布</p >
</div>
<div style="padding:20px;">
    <table style="width:100%;border-collapse:collapse;">
        <tr><td style="padding:10px;border-bottom:1px solid #eee;font-weight:bold;color:#b71c1c;">⚠️ 触发原因</td><td style="padding:10px;border-bottom:1px solid #eee;">{reason}</td></tr>
        <tr><td style="padding:10px;border-bottom:1px solid #eee;font-weight:bold;">🧑‍🤝‍🧑 感染人数参考</td><td style="padding:10px;border-bottom:1px solid #eee;">{infections}</td></tr>
        <tr><td style="padding:10px;font-weight:bold;">🌍 是否威胁中国</td><td style="padding:10px;">{'<span style="color:#e53935;font-weight:bold;">是，需密切关注</span>' if threat else '否'}</td></tr>
    </table>
    <p style="margin-top:16px;padding:12px;background:#fff3e0;border-radius:8px;font-size:13px;color:#e65100;">
        📌 请尽快查阅新闻详情，采取应对措施。此邮件由AI自动预警系统生成。
    </p >
</div>
</div></body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚨 紧急预警：病毒疫情更新 | {now.strftime('%Y-%m-%d %H:%M')}"
    msg["From"] = SENDER
    msg["To"] = RECEIVER
    msg.attach(MIMEText("请使用支持HTML的邮箱客户端查看", "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
        server.login(SENDER, QQ_PASS)
        server.send_message(msg)
    print("✅ 预警邮件已发送")
else:
    print("无需预警，一切正常")
