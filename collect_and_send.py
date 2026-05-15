import requests, smtplib, os
from email.mime.text import MIMEText
from datetime import datetime

# === 配置 ===
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
QQ_PASS = os.getenv("QQ_EMAIL_PASSWORD")
SENDER = "3502739363@qq.com"
RECEIVER = "3502739363@qq.com"
TODAY = datetime.now().strftime("%Y-%m-%d")

# 1. 抓取24小时内的病毒/疫情新闻（中文源）
news_url = "https://newsapi.org/v2/everything"
params = {
    "q": "virus OR outbreak OR 病毒 OR 疫情 OR 感染 OR 人传人",
    "from": TODAY,
    "sortBy": "popularity",
    "pageSize": 15,
    "language": "zh",
    "apiKey": NEWS_API_KEY
}
try:
    resp = requests.get(news_url, params=params, timeout=15)
    articles = resp.json().get("articles", [])
    news_list = []
    for a in articles[:10]:
        news_list.append(f"📰 {a.get('title','无标题')}\n   {a.get('description','')}\n   来源：{a.get('url','')}")
    news_text = "\n".join(news_list) if news_list else "（今日暂无相关新闻数据）"
except Exception as e:
    news_text = f"新闻获取失败：{str(e)}"

# 2. 调用DeepSeek分析生成报告
prompt = f"""你是一位病毒学与公共卫生专家。以下是今日（{TODAY}）收集到的全球病毒/疫情相关新闻摘要，重点关注与人相关或可能动物传人的疫情：

{news_text}

请按以下要求输出报告：
1️⃣ **疫情概况**：分地区/病毒列出主要事件，尤其关注感染人数超过30人的事件。
2️⃣ **动物传染病威胁**：列出可能由动物传播给人类的病毒或疫情，如禽流感、猴痘、尼帕等。
3️⃣ **对中国的威胁评估**：是否存在直接威胁中国境内的疫情（如输入性病例、新变种传入等）？请明确指出。
4️⃣ **专家建议**：通俗语言告诉普通人当前应该注意什么。

注意：如果新闻中没有任何感染人数数据，请注明。报告语言为中文，保持客观、专业。"""

payload = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.3,
    "max_tokens": 2000
}
try:
    ai_resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=30
    )
    report = ai_resp.json()["choices"][0]["message"]["content"]
except Exception as e:
    report = f"AI分析失败：{str(e)}"

# 3. 发送邮件
msg = MIMEText(report, "plain", "utf-8")
msg["Subject"] = f"每日全球病毒疫情简报 - {TODAY}"
msg["From"] = SENDER
msg["To"] = RECEIVER
with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
    server.login(SENDER, QQ_PASS)
    server.send_message(msg)

print("✅ 病毒日报已发送至邮箱")
