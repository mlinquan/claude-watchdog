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
# Daemon management
claude-watchdog start              # Start (default: monitor all claude-* sessions)
claude-watchdog stop               # Stop
claude-watchdog restart            # Restart
claude-watchdog status             # Show status + session states

# Log viewer
claude-watchdog log                # Tail -f by default
claude-watchdog log --no-follow    # Show recent N entries, then exit
claude-watchdog log --session claude-tl  # Filter by session

# One-shot check (legacy syntax still works)
claude-watchdog --session claude-tl
claude-watchdog --all --daemon
claude-watchdog --session claude-tl --daemon
claude-watchdog --session claude-tl --daemon --alert-only
claude-watchdog --log
claude-watchdog --log --follow
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
