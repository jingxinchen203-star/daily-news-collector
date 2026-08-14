# Daily News Collector

![Daily News Collector project hero](assets/project-hero.png)


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
| `NEWS_API_KEY` | 否 | NewsAPI 的访问密钥；不设置时仍可使用 RSS 新闻源 |
| `DEEPSEEK_API_KEY` | 至少一个模型密钥 | DeepSeek API 密钥 |
| `OPENAI_API_KEY` | 至少一个模型密钥 | OpenAI API 密钥 |
| `ANTHROPIC_API_KEY` | 至少一个模型密钥 | Claude/Anthropic API 密钥 |
| `QQ_EMAIL_PASSWORD` | 是 | QQ 邮箱 SMTP 授权码，不是网页登录密码 |
| `NEWS_SENDER` | 否 | 发件邮箱；不设置时使用旧项目中的默认地址 |
| `NEWS_RECEIVER` | 否 | 收件邮箱；不设置时默认发送给发件邮箱 |

可选的 repository variables：

| 名称 | 默认值 | 说明 |
| --- | --- | --- |
| `NEWS_RSS_URLS` | ECDC 禽流感和猴痘 RSS | 以英文逗号分隔的 RSS/Atom 地址；可替换或增加 WHO、CDC、卫生部门等来源 |
| `AI_FALLBACK_PROVIDERS` | `deepseek,openai,anthropic` | 模型回退顺序；只会尝试已配置密钥的提供商 |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI 模型名称 |
| `ANTHROPIC_MODEL` | `claude-3-5-haiku-latest` | Claude 模型名称 |

其他可选的 repository variables：

| 名称 | 默认值 | 说明 |
| --- | --- | --- |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 使用的 DeepSeek 模型名称 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1/chat/completions` | OpenAI 兼容接口地址；可用于兼容 OpenAI Chat Completions 的服务 |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com/v1/messages` | Anthropic Messages API 地址 |

请不要把密钥写入代码、README、日志或提交记录。若密钥曾经出现在公开仓库中，应立即在对应服务后台撤销并重新生成。

## 扩展新闻源和模型

新闻源分为两类。`NEWS_API_KEY` 可选，用于调用 NewsAPI；`NEWS_RSS_URLS` 可配置任意公开 RSS/Atom 订阅，程序会解析标题、摘要、链接和发布时间，并去重。默认已经配置 ECDC 的禽流感和猴痘 RSS。增加来源时，只需要在仓库变量中填写逗号分隔的地址，例如：

```text
https://www.ecdc.europa.eu/en/taxonomy/term/323//feed,https://example.org/health/feed.xml
```

模型采用自动回退机制。程序按 `AI_FALLBACK_PROVIDERS` 的顺序尝试已配置的密钥；如果 DeepSeek 因余额、额度、限流或接口错误失败，就会继续尝试 OpenAI，再尝试 Claude。OpenAI 使用 Chat Completions 兼容格式，Claude 使用 `/v1/messages` 格式，因此三类提供商可以共用同一个日报和预警流程。

建议至少配置两个模型提供商，这样单一账户额度耗尽时仍能继续生成邮件。模型服务的调用费用、限额和可用模型名称由对应服务商账户决定，项目不会绕过服务商的额度限制。

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
