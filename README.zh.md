# claude-watchdog

> ⚠️ **已废弃** — 由 [claude-tmux-dog (cdog)](https://github.com/SnowAIGirl/claude-tmux-dog) 替代

**cdog** 是功能更全面的 Claude Code 进程管理器：
- 无人值守 7×24 运行（auto-nudge + auto-recovery）
- 双层上下文防御（主动 pane watcher + 被动 log watcher）
- 跨 Agent 消息总线
- 桌面通知 + 交互操作
- API 错误分类 + 差异化阈值
- 熔断器防止死循环失败

```bash
npm install claude-tmux-dog -g
cdog start ./cdog.json
```

完整文档见 [github.com/SnowAIGirl/claude-tmux-dog](https://github.com/SnowAIGirl/claude-tmux-dog)
