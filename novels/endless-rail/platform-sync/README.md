# 番茄自动同步

本目录把 GitHub 仓库定义为正文与发布意图的唯一来源，番茄作为受控同步目标。

## 安全模型

自动化默认关闭。真正写入番茄必须同时满足：

1. `config.json` 中 `sync_enabled=true`；
2. `policy.json` 中 `policy_status=active`；
3. `queue.json` 中存在明确操作；
4. 操作 `authorized=true`；
5. 操作的 `audit.status` 必须为 `passed`。

GitHub-hosted 的 `validate` job 会先读取仓库配置；只有仓库自己的 `sync_enabled=true` 时，才会调度本机 `fanqie` runner。普通章节修改、审计过程、文档修改不会自动覆盖番茄。

## 文件职责

- `config.json`：作品 ID、章节路径和总开关。
- `policy.json`：默认发布时间、每天章数、AI 创作申报等发布策略。
- `queue.json`：机器可执行的授权操作队列。
- `sync-state.json`：最近一次已确认同步的本地内容哈希与操作记录。
- `MANIFEST.md`：历史平台恢复/回填说明，继续保留为人工审计证据。

## 支持的操作

### 新章节

```json
{
  "id": "create-107-126-20260829",
  "action": "create",
  "chapters": "107-126",
  "authorized": true,
  "audit": {
    "status": "passed",
    "commit": "<audited-commit-sha>"
  },
  "status": "pending"
}
```

默认使用 `policy.json` 的 `auto_continue`：先读取番茄现有队列，只处理授权范围内、平台尚未存在的后续章节，然后接在现有排期后继续排。

### 修改已有章节

```json
{
  "id": "update-49-66-20260829",
  "action": "update",
  "chapters": "49,66",
  "authorized": true,
  "audit": {
    "status": "passed",
    "commit": "<audited-commit-sha>"
  },
  "status": "pending"
}
```

修改模式按章节号匹配平台已有章节，替换标题/正文，不主动改变原发布时间。

### 重排全部待发布章节

```json
{
  "id": "reschedule-20260901",
  "action": "reschedule_all",
  "start_date": "2026-09-01",
  "authorized": true,
  "audit": {
    "status": "passed"
  },
  "status": "pending"
}
```

该操作会按 `policy.json` 当前的每天章数与时间点重新安排番茄所有“待发布”章节，因此必须显式授权。

## 本地检查

```text
python shared/tools/fanqie_sync.py validate novels/endless-rail
python shared/tools/fanqie_sync.py plan novels/endless-rail
```

`plan` 只展示会执行什么，不写番茄。

## 一次性本机准备

Windows 上只需要跑一次总引导脚本：

```text
powershell -ExecutionPolicy Bypass -File shared/tools/bootstrap_fanqie_sync.ps1
```

它会依次完成：

1. 把固定版本的 `rockbenben/fanqie-publisher` 安装到用户目录并安装 Playwright Chromium；
2. 打开一次番茄登录流程，登录状态只保存在本机；
3. 下载并配置 GitHub self-hosted runner，标签固定为 `fanqie`；
4. 给当前 Windows 用户注册登录后自动启动 runner 的计划任务，并立即启动本次会话的 runner。

脚本配置 Runner 时会要求一个 GitHub **短期注册 token**。请在仓库 `Settings -> Actions -> Runners -> New self-hosted runner` 页面复制；只在本机脚本提示框中输入，不要发到聊天、不要提交仓库。

完成这一次后，日常不需要再启动发布器、打开番茄后台或手工运行脚本。真正的平台写入只在这个本机 runner 上发生，番茄登录信息不进入 GitHub。

## 自然语言工作流

以后用户只需要表达意图，例如：

- “审计通过后把107～126章排上番茄。”
- “第66章修正版同步番茄。”
- “从明天开始每天4章，10点、14点、18点、21点。”
- “把现有待发布库存重新排到每天两章，上午10点和晚上8点。”

负责维护仓库的助手把意图转成 `policy.json` / `queue.json` 的明确变更；Publisher 只执行已经审计和授权的机器可读任务。
