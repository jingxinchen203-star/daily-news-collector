# Daily News Collector

这是一个基于 GitHub Actions 的公共卫生新闻监测工具。它从 NewsAPI 获取近 24 小时的病毒与疫情相关新闻，调用 DeepSeek 进行中文整理，并通过 QQ 邮箱发送每日简报；另一个工作流每 30 分钟检查是否出现需要人工复核的高风险事件。

> 本项目是信息整理工具，不是医疗诊断、疫情预测或官方预警系统。所有结论都应回到原始新闻、当地卫生部门和专业医生进行核查。

## 功能

| 模块 | 作用 | 默认频率 |
| --- | --- | --- |
| `collect_and_send.py` | 生成带原始链接的中文日报并发送邮件 | 每天北京时间 08:30 |
| `alert_check.py` | 判断是否满足“明确感染人数超过 30 人”或“直接威胁中国”这两个条件 | 每 30 分钟 |
| `news_common.py` | 统一处理配置、HTTP 请求、AI 返回解析、HTML 转义和 SMTP 发送 | 共享模块 |

## 配置 Secrets

在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 中配置以下 Secrets：

| 名称 | 必填 | 说明 |
| --- | --- | --- |
| `NEWS_API_KEY` | 是 | NewsAPI 的访问密钥 |
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API 密钥 |
| `QQ_EMAIL_PASSWORD` | 是 | QQ 邮箱 SMTP 授权码，不是网页登录密码 |
| `NEWS_SENDER` | 否 | 发件邮箱；不设置时使用旧项目中的默认地址 |
| `NEWS_RECEIVER` | 否 | 收件邮箱；不设置时默认发送给发件邮箱 |

可选的 repository variable：

| 名称 | 默认值 | 说明 |
| --- | --- | --- |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 使用的 DeepSeek 模型名称 |

请不要把密钥写入代码、README、日志或提交记录。若密钥曾经出现在公开仓库中，应立即在对应服务后台撤销并重新生成。

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export NEWS_API_KEY='your-newsapi-key'
export DEEPSEEK_API_KEY='your-deepseek-key'
export QQ_EMAIL_PASSWORD='your-qq-smtp-password'
python collect_and_send.py
python alert_check.py
```

脚本使用带连接和读取超时的 HTTP 请求，并会在 NewsAPI、DeepSeek 或 SMTP 失败时返回明确错误。正式运行前，建议先用 GitHub Actions 的 **workflow_dispatch** 手动触发，确认密钥、发件邮箱授权码和收件地址均正确。

## 主要改进

原项目把两套脚本中的请求、密钥和邮件逻辑重复写在一起，并且没有统一检查 HTTP 状态码，AI 返回 JSON 失败时也容易直接崩溃。当前版本将共享逻辑集中到 `news_common.py`，使用 UTC 时间窗口抓取近 24 小时数据，固定依赖版本范围，增加 HTML 转义和原始来源链接，改进 AI JSON 解析，并在工作流中加入权限最小化、运行超时和并发控制。

## 免责声明

新闻来源可能存在延迟、误报、重复报道或信息不完整的情况。AI 输出只用于辅助阅读，不能替代官方通报、流行病学调查、医疗建议或应急决策。
