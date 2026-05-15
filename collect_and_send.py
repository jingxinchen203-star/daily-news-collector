import requests, smtplib, os
from email.mime.text import MIMEText
from datetime import datetime

api_key = os.getenv("DEEPSEEK_API_KEY")
response = requests.post(
    "https://api.deepseek.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": f"今天是{datetime.now().strftime('%Y年%m月%d日')}。请整理今日最重要的5条国内科技新闻，每条用1-2句话概括。按重要性排序。"
            }
        ],
        "temperature": 0.3,
        "max_tokens": 1000
    }
)

try:
    news_content = response.json()["choices"][0]["message"]["content"]
except Exception as e:
    news_content = f"获取新闻失败：{str(e)}\n原始返回：{response.text}"

sender = "3502739363@qq.com"
receiver = "3502739363@qq.com"
password = os.getenv("QQ_EMAIL_PASSWORD")

msg = MIMEText(news_content, "plain", "utf-8")
msg["Subject"] = f"每日科技简报 - {datetime.now().strftime('%Y-%m-%d')}"
msg["From"] = sender
msg["To"] = receiver

try:
    with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)
    print("邮件发送成功 ✓")
except Exception as e:
    print(f"邮件发送失败：{e}")
