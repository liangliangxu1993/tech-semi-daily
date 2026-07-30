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

## 六、外部定时触发（cron-job.org，比 GitHub 内置调度可靠）

GitHub 内置 `schedule` 是「尽力而为」，新工作流常漏跑、高峰期延迟。
更可靠的做法：让外部定时服务每天调用 GitHub 的 `workflow_dispatch` API 主动触发。

### 6.1 创建细粒度 PAT（Personal Access Token）

1. GitHub → 右上头像 → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**
2. 关键设置：
   - **Token name**：`tech-semi-daily-dispatch`
   - **Expiration**：按需（如 1 年）
   - **Resource owner**：你的账号
   - **Repository access**：`Only select repositories` → 勾选 `tech-semi-daily`
   - **Permissions → Repository permissions → Actions**：设为 **Read and write**
     （`Metadata: Read-only` 会自动带上，保留即可）
3. **Generate token**，复制那串 `github_pat_xxxxx`（只显示一次，务必保存）。

### 6.2 在 cron-job.org 建定时任务

1. 到 https://cron-job.org 注册登录 → **Create cronjob**
2. 填写：
   - **Title**：`科技半导体日报触发`
   - **URL**：
     ```
     https://api.github.com/repos/liangliangxu1993/tech-semi-daily/actions/workflows/daily.yml/dispatches
     ```
   - **Schedule**：时区选 `Asia/Shanghai`，时间每天 **08:37**
     （若只能填 UTC，则填 **00:37**）
3. 展开 **Advanced**：
   - **Request method**：`POST`
   - **Headers**（逐条添加）：
     ```
     Accept: application/vnd.github+json
     Authorization: Bearer github_pat_你的token
     X-GitHub-Api-Version: 2022-11-28
     Content-Type: application/json
     ```
   - **Request body**：
     ```json
     {"ref":"main"}
     ```
4. 保存。可点 cron-job.org 的 **TEST RUN / 立即执行** 验证——成功时 GitHub 返回 **HTTP 204**（无响应体即正常），随后 Actions 会出现一条 `event = workflow_dispatch` 的运行。

### 6.3 关掉内置 schedule，避免重复推送 ⚠️

外部触发确认可用后，务必删除 `.github/workflows/daily.yml` 里的 `schedule:` 段
（保留 `workflow_dispatch: {}`），否则内置调度一旦也触发就会**一天推送两次**。

```yaml
on:
  workflow_dispatch: {}    # 仅保留手动 / 外部 API 触发
```

### 6.4 排障

- **Actions 里没出现 workflow_dispatch 记录**：多半是 PAT 权限不足（须 Actions: Read and write）或 URL/仓库名写错。
- **cron-job.org 显示失败但其实成功**：GitHub 返回 204 而非 200，部分工具会误判；以 Actions 页面是否出现运行为准。
- **401/403**：token 过期、拼写错误，或没勾选该仓库。

## 七、日常维护

- **调整关注标的 / 新闻关键词**：改 `src/config.py` 的 `WATCHLIST` 和 `NEWS_SOURCES`
- **调整量化阈值**：改 `src/config.py` 的 `THRESHOLDS`
- **更新 FOMC 会议日历**：每年更新 `src/config.py` 的 `FOMC_MEETINGS_2026`
  （来源：https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm）
- 触发链路跑通后每天自动推送并存档到 `reports/`，无需再操作

## 八、本地调试

```bash
cp .env.example .env      # 填入本地密钥
pip install -r requirements.txt
python -m src.main --dry-run          # 只打印报告，不推送
python -m src.main --save report.md   # 额外保存报告到文件
python -m src.main                    # 完整运行并推送
```

> 注意：部分沙箱/受限网络会屏蔽 Google News、限流 Yahoo Finance，
> 本地可能拿不到完整数据；真实数据以 GitHub Actions（美国节点）运行为准。
