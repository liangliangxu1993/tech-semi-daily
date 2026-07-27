# 部署指南

本项目通过 GitHub Actions 每日定时运行，抓取科技/半导体行业资讯并推送到微信。
本文档记录部署、配置与首次触发的完整步骤。

## 一、推送与运行原理

- 定时：`.github/workflows/daily.yml` 中 cron `30 0 * * *`（UTC）= **北京时间 08:30**
  - GitHub 定时任务高峰期可能延迟 5–15 分钟，属正常现象
- 手动：workflow 支持 `workflow_dispatch`，可在 Actions 页面随时手动触发
- 降级：任一数据源（新闻/行情/财报/宏观）失败都不会中断流程；无 LLM key 时自动降级为纯量化报告

## 二、Secrets 配置

仓库 → **Settings → Secrets and variables → Actions → Secrets** 选项卡：

| 名称 | 是否必需 | 说明 |
|---|---|---|
| `SERVERCHAN_SENDKEY` | **推送渠道二选一** | Server酱 sendkey，微信推送。到 https://sct.ftqq.com 登录获取 `SCTxxxxx` |
| `WECOM_WEBHOOK` | **推送渠道二选一** | 企业微信群机器人 webhook URL（群设置→群机器人→添加→复制 Webhook 地址） |
| `ANTHROPIC_API_KEY` | 可选 | 有则启用 LLM 解读；无则降级为纯量化报告 |
| `FRED_API_KEY` | 可选 | 有则取真实联邦基金利率（FEDFUNDS）；无则用 10 年美债收益率（^TNX）代理 |

> **推送渠道至少配一个**，否则报告生成后无处可推，workflow 会返回失败（退出码 1）。

## 三、Variables 配置（可选）

同页面 **Variables** 选项卡，不填则走括号内默认值：

| 名称 | 默认值 | 说明 |
|---|---|---|
| `PUSH_CHANNEL` | `serverchan` | 可选 `serverchan` / `wecom` / `both` |
| `LLM_MODEL` | `claude-haiku-4-5` | LLM 模型 |
| `ENABLE_LLM` | `1` | 设 `0` 可临时关闭 LLM |

> ⚠️ **常见坑**：只配了 `WECOM_WEBHOOK` 却没把 `PUSH_CHANNEL` 设为 `wecom`，
> 默认仍走 serverchan → 推送失败。**用企业微信必须加 `PUSH_CHANNEL=wecom`。**

## 四、首次手动触发

1. 仓库 → **Actions** 标签
2. 左侧选 "科技半导体日报"
3. 右侧 **Run workflow** → 选 `main` 分支 → 绿色 **Run workflow**

## 五、验证清单

点开本次运行 → 展开 **Run daily report** 日志，依次确认：

1. 开头 `[main] 配置: {...}`：`serverchan`/`wecom` 为 `True`，`llm_enabled` 符合预期
2. `[main] 触发信号 N 条`：N>0 说明成功拿到行情数据（GitHub 美国节点不被 Yahoo 限流）
3. 结尾推送渠道返回成功，且**微信/企业微信确实收到日报**
4. 整个 job 结束为绿色 ✓（退出码 0）

若信号为 0 或新闻为空，检查日志中是否有 `数据获取失败`。

## 六、日常维护

- **调整关注标的 / 新闻关键词**：改 `src/config.py` 的 `WATCHLIST` 和 `NEWS_SOURCES`
- **调整量化阈值**：改 `src/config.py` 的 `THRESHOLDS`
- **更新 FOMC 会议日历**：每年更新 `src/config.py` 的 `FOMC_MEETINGS_2026`
  （来源：https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm）
- 首次跑通后 cron 会自动每天推送，无需再操作

## 七、本地调试

```bash
cp .env.example .env      # 填入本地密钥
pip install -r requirements.txt
python -m src.main --dry-run          # 只打印报告，不推送
python -m src.main --save report.md   # 额外保存报告到文件
python -m src.main                    # 完整运行并推送
```

> 注意：部分沙箱/受限网络会屏蔽 Google News、限流 Yahoo Finance，
> 本地可能拿不到完整数据；真实数据以 GitHub Actions（美国节点）运行为准。
