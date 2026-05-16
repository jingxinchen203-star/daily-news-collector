import requests, smtplib, os, json
from email.mime.text import MIMEText
from datetime import datetime

# === 配置 ===
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
QQ_PASS = os.getenv("QQ_EMAIL_PASSWORD")
SENDER = "3502739363@qq.com"
RECEIVER = "3502739363@qq.com"



print("开始执行90分钟紧急检查...")
now = datetime.now()
# 1. 获取最新病毒相关新闻（过去24小时内，按时间排序）
today = now.strftime("%Y-%m-%d")
news_url = "https://newsapi.org/v2/everything"
params = {
    "q": "virus OR outbreak OR 病毒 OR 疫情 OR 感染 OR 人传人 OR 动物传人",
    "from": today,
    "sortBy": "publishedAt",
    "pageSize": 10,
    "language": "zh",
    "apiKey": NEWS_API_KEY
}
try:
    resp = requests.get(news_url, params=params, timeout=15)
    articles = resp.json().get("articles", [])
    if not articles:
        print("无新新闻，跳过")
        exit(0)
    news_text = ""
    for a in articles:
        news_text += f"{a.get('title','')} {a.get('description','')}\n"
except Exception as e:
    print(f"新闻获取失败：{e}")
    exit(1)

# 2. 调用DeepSeek判断是否触发警报（返回JSON）
prompt = f"""根据以下最新病毒/疫情新闻，判断是否存在需要紧急关注的严重事件。严重事件定义为：
- **感染人数超过30人** 或
- **直接威胁中国境内安全**（如新变异株传入、输入性病例大规模爆发、动物疫情可能传入中国）

请只输出一个JSON对象，不要附加任何其他文字：
{{"alert": false, "reason": "", "infections": 0, "threat_to_china": false}}
- alert：true表示需要预警，false表示不需要
- reason：简要说明原因
- infections：新闻中提到的最高感染人数（若无则填0）
- threat_to_china：是否直接威胁中国

新闻内容：
{news_text}"""

payload = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.1,
    "max_tokens": 500
}
try:
    ai_resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=30
    )
    result = json.loads(ai_resp.json()["choices"][0]["message"]["content"])
except Exception as e:
    print(f"AI分析失败：{e}")
    exit(1)

if result.get("alert") == True:
    # 3. 发送紧急预警邮件
    msg_body = f"""⚠️ 病毒疫情紧急预警

时间：{now.strftime('%Y-%m-%d %H:%M')}

触发原因：{result.get('reason', '未知')}
感染人数参考：{result.get('infections', 0)}
是否威胁中国：{'是' if result.get('threat_to_china') else '否'}

请尽快查阅新闻详情，采取应对措施。
（此邮件由AI自动预警系统生成）"""

    msg = MIMEText(msg_body, "plain", "utf-8")
    msg["Subject"] = f"🚨 紧急预警：病毒疫情更新 - {now.strftime('%Y-%m-%d %H:%M')}"
    msg["From"] = SENDER
    msg["To"] = RECEIVER
    with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
        server.login(SENDER, QQ_PASS)
        server.send_message(msg)
    print("✅ 预警邮件已发送")
else:
    print("无需预警，一切正常")
