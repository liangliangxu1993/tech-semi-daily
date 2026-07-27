# 科技半导体产业每日资讯自动推送

每天早上 **08:30（北京时间）** 自动抓取 **美国 / 韩国 / 中国** 科技半导体产业资讯，
综合上市企业财报、技术进展、全球局势、美联储政策、国际油价等，
结合 **量化规则 + Claude LLM** 生成产业综述与科技持股投资建议，推送到**微信**。

> ⚠️ 所有投资建议均由 AI 依据公开数据自动生成，**仅供参考，不构成投资意见**。

---

## 功能概览

| 模块 | 内容 |
|---|---|
| 分区资讯 | Google News RSS 抓取美/韩/中 + 全球宏观新闻 |
| 财报追踪 | 关注标的即将披露日期 + 最近一期 EPS 超预期/不及预期 |
| 行情技术面 | 股价、日/周涨跌幅、MA20/MA50、RSI14 |
| 宏观 | WTI/布伦特油价、费城半导体指数 ^SOX、纳指、美债 10Y、联邦基金利率、FOMC 日程 |
| 量化信号 | 财报超预期、均线金叉死叉、RSI 超买超卖、油价异动、议息临近、板块情绪 |
| LLM 解读 | Claude 综合以上生成中文简报 + 分标的/板块持股建议（附免责声明） |
| 推送 | Server酱 Turbo（主）/ 企业微信机器人（备选） |

关注标的、新闻关键词、量化阈值都在 [`src/config.py`](src/config.py) 里，可自行增删。

---

## 快速开始（本地测试）

```bash
cd tech-semi-daily
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # 填入你的 SendKey / API Key

# 只生成报告打印到终端，不推送（推荐先跑这个验证数据）
python -m src.main --dry-run

# 生成并保存到文件
python -m src.main --dry-run --save report.md

# 真实推送
python -m src.main
```

即使不填 `ANTHROPIC_API_KEY`（或设 `ENABLE_LLM=0`），系统也能运行——会自动降级为
「纯量化 + 资讯汇总」报告，不会中断推送。

---

## 部署到 GitHub Actions（免服务器）

1. 新建一个 GitHub 仓库，把本项目推上去。
2. 进入仓库 **Settings → Secrets and variables → Actions**，添加 **Secrets**：
   - `SERVERCHAN_SENDKEY`：Server酱 Turbo 的 SendKey（[获取地址](https://sct.ftqq.com)）
   - `ANTHROPIC_API_KEY`：Claude API Key（[控制台](https://console.anthropic.com)）
   - `WECOM_WEBHOOK`：（可选）企业微信群机器人 Webhook
   - `FRED_API_KEY`：（可选）美联储数据 [免费 Key](https://fred.stlouisfed.org/docs/api/api_key.html)
3. 如需切换渠道/模型，在同页 **Variables** 里加：
   - `PUSH_CHANNEL` = `serverchan` / `wecom` / `both`
   - `LLM_MODEL` = `claude-haiku-4-5`（默认，低成本）或 `claude-sonnet-5`（更高质量）
   - `ENABLE_LLM` = `1` / `0`
4. 到 **Actions** 页面，选中「科技半导体日报」工作流，点 **Run workflow** 手动跑一次验证。
5. 之后每天 08:30（北京）自动运行。

### 关于定时精度
GitHub Actions 的 cron 在高峰时段**可能延迟 5–15 分钟**，做不到分秒级 08:30。
若你需要精确到点，可把仓库部署到一台 VPS，用系统 crontab：

```cron
30 8 * * *  cd /path/to/tech-semi-daily && /path/to/.venv/bin/python -m src.main >> run.log 2>&1
```

---

## 获取推送渠道凭证

### Server酱 Turbo（推荐，微信服务号推送）
1. 打开 https://sct.ftqq.com ，用微信扫码登录。
2. 复制 **SendKey**（形如 `SCTxxxxxx...`），填入 `SERVERCHAN_SENDKEY`。
3. 关注它引导的微信服务号即可在微信收到消息。

### 企业微信群机器人（可选）
1. 在企业微信群 → 右上角 → 群机器人 → 添加。
2. 复制生成的 **Webhook 地址**，填入 `WECOM_WEBHOOK`。

---

## 目录结构

```
tech-semi-daily/
├── .github/workflows/daily.yml   # 定时任务
├── src/
│   ├── config.py                 # 标的/新闻/阈值配置
│   ├── collectors/               # news / prices / earnings / macro
│   ├── analysis/                 # rules(量化) / llm(Claude)
│   ├── render.py                 # Markdown 报告
│   ├── push/                     # serverchan / wecom
│   └── main.py                   # 编排入口
├── requirements.txt
├── .env.example
└── README.md
```

## 数据来源说明
- 新闻：Google News RSS（免费、无鉴权）
- 行情/财报/油价/指数：[yfinance](https://github.com/ranaroussi/yfinance)（Yahoo Finance 公开数据）
- 美联储利率：[FRED API](https://fred.stlouisfed.org)（可选，未配置时用 10Y 美债收益率代理）

数据均来自公开渠道，可能存在延迟或缺失；系统对单点失败做了容错，不会因某个源挂掉而中断。
