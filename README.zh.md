# claude-watchdog

Claude Code tmux 看门狗 — 自动解除权限弹窗卡住，不用你盯着。

仅在有弹窗被检测到并处理时输出日志，平时静默。

## 安装

```bash
pip install claude-watchdog
```

## 用法

```bash
# 管理守护进程
claude-watchdog start              # 启动（默认监控所有 claude-* session）
claude-watchdog stop               # 停止
claude-watchdog restart            # 重启
claude-watchdog status             # 查看状态 + 各 session 状态

# 查看日志
claude-watchdog log                # 默认 tail -f 实时追踪
claude-watchdog log --no-follow    # 只看最近 N 条
claude-watchdog log --session claude-tl  # 按 session 过滤

# 单次检查（旧语法仍兼容）
claude-watchdog --session claude-tl
claude-watchdog --all --daemon
claude-watchdog --session claude-tl --daemon
claude-watchdog --session claude-tl --daemon --alert-only
claude-watchdog --log
claude-watchdog --log --follow
```

## 通知方式

检测到弹窗时可以通知你。加 `--notify` 启用内置信使通知，或用管道接任意脚本：

```bash
# 内置信使通知（接 hermes-notify，总线静默推送）
claude-watchdog --session claude-tl --daemon --notify

# 管道接任何你想用的方式

# HTTP Webhook（Slack/Telegram/任意 API）
claude-watchdog --session claude-tl --daemon | while read line; do
  curl -s -X POST https://hooks.slack.com/services/xxx/yyy/zzz \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$line\"}"

  curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
    -d "chat_id=<CHAT_ID>&text=$line"
done

# MCP 通知（Model Context Protocol）
claude-watchdog --session claude-tl --daemon | while read line; do
  curl -s -X POST http://localhost:8080/mcp/notify \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\": \"2.0\", \"method\": \"notifications/message\", \
         \"params\": {\"severity\": \"warning\", \"message\": \"$line\"}}"
done

# macOS 系统通知
claude-watchdog --session claude-tl --daemon | while read line; do
  osascript -e "display notification \"$line\" with title \"Watchdog\""
done

# 微信 / 总线（通过 notify-hermes.py）
claude-watchdog --session claude-tl --daemon | while read line; do
  ~/.hermes/scripts/notify-hermes.py --type progress "Watchdog: $line"
done
```

`--notify` 会自动检测 `hermes-notify` 是否安装。无硬依赖——没装时不生效。

## 规则

| 弹窗内容 | 按键 | 说明 |
|---------|------|------|
| `Do you want to proceed` | 1 + Enter | 工具确认弹窗，选 Yes |
| `Do you want to (make this edit\|overwrite)` | Down + Enter | 允许本次 session 的所有编辑 |
| `accept edits on` | Enter | 接受待处理的 diff 改动 |
| `bypass permissions on` | Enter | 绕过权限拦截 |
| `Detected a custom API key` | Up + Enter | 确认使用自定义 API key |
| `Interrupted` | 2 + Enter | 被中断后选 Bypass/Continue |
| `Rate this response` / `How was this` | Escape | 关掉评价弹窗 |

## 日志

命中记录保存在 `~/.local/share/claude-watchdog/hits.log`，JSONL 格式：

```json
{"ts": "2026-05-18 09:15:23", "session": "claude-tl", "rule": "bypass_permissions", "detail": "Permission bypass prompt — confirm bypass"}
```

## 架构

```
cli.py ── session/daemon/log ──→ watcher.py ── tmux capture-pane
                                        │
                                        ↓ rules.py
                                   正则匹配？
                                   ├─ 是 → 按键 + 日志 [+ 通知]
                                   └─ 否 → 静默
```
