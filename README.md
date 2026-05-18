# claude-watchdog

[English](./README.md) | [中文](./README.zh.md)

Claude Code tmux watchdog — auto-unblock permission dialogs so you
don't have to stare at a blocked session.

Only logs hits (blockage detected and cleared), silent otherwise.

## Install

```bash
pip install claude-watchdog
```

## Usage

```bash
# One-shot check (runs once, exits)
claude-watchdog --session claude-tl

# Monitor continuously
claude-watchdog --session claude-tl --daemon

# Monitor every claude-* session
claude-watchdog --all --daemon

# Alert only — log + notify, don't auto-approve
claude-watchdog --session claude-tl --daemon --alert-only

# View hit log
claude-watchdog --log
claude-watchdog --log --follow       # tail -f mode
claude-watchdog --log --session claude-tl  # filter by session
```

## Notify on hit

When a blockage is detected and cleared, claude-watchdog can notify you.
Pass `--notify` (or `-n`) to enable. Examples:

```bash
# Integrated: via hermes-notify (bus message, silent progress type)
claude-watchdog --session claude-tl --daemon --notify

# DIY: pipe stdout to anything you want

# HTTP webhook (Slack/Telegram/Discord/any API)
claude-watchdog --session claude-tl --daemon | while read line; do
  curl -s -X POST https://hooks.slack.com/services/xxx/yyy/zzz \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$line\"}"

  curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
    -d "chat_id=<CHAT_ID>&text=$line"
done

# MCP notification (Model Context Protocol — tools with notifications)
claude-watchdog --session claude-tl --daemon | while read line; do
  curl -s -X POST http://localhost:8080/mcp/notify \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\": \"2.0\", \"method\": \"notifications/message\", \
         \"params\": {\"severity\": \"warning\", \"message\": \"$line\"}}"
done

# macOS notification
claude-watchdog --session claude-tl --daemon | while read line; do
  osascript -e "display notification \"$line\" with title \"Watchdog\""
done

# WeChat (via notify-hermes.py)
claude-watchdog --session claude-tl --daemon | while read line; do
  ~/.hermes/scripts/notify-hermes.py --type progress "Watchdog: $line"
done
```

The `--notify` flag auto-detects `hermes-notify` if installed. No hard
dependency — without it, `--notify` is a no-op.

## Rules

| Pattern | Keys | Description |
|---------|------|-------------|
| `Do you want to proceed` | 1 + Enter | Tool confirmation dialog |
| `Do you want to (make this edit\|overwrite)` | Down + Enter | Allow all edits this session |
| `accept edits on` | Enter | Accept pending diffs |
| `bypass permissions on` | Enter | Bypass permission dialog |
| `Detected a custom API key` | Up + Enter | Confirm custom API key |
| `Interrupted` | 2 + Enter | Bypass/continue after interruption |
| `Rate this response` / `评价` / `评分` | Escape | Dismiss evaluation dialog |

New patterns can go into `~/.config/claude-watchdog/rules.toml` (future).

## Log

Hits are logged to `~/.local/share/claude-watchdog/hits.log` as JSONL:

```json
{"ts": "2026-05-18 09:15:23", "session": "claude-tl", "rule": "bypass_permissions", "detail": "Permission bypass prompt — confirm bypass"}
```

## Architecture

```
cli.py ── session/daemon/log ──→ watcher.py ── tmux capture-pane
                                        │
                                        ↓ rules.py
                                   pattern match?
                                   ├─ yes → send-keys + log [+ notify]
                                   └─ no  → silent
```
