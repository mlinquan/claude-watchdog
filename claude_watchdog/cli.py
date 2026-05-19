#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess
import sys

from .watcher import watch_loop, watch_all, get_sessions
from .logger import read_log

PID_FILE = os.path.expanduser("~/.local/share/claude-watchdog/daemon.pid")


def _find_watchdog_pids() -> list[int]:
    """Find all running claude-watchdog daemon processes (excluding this one)."""
    try:
        r = subprocess.run(
            ["pgrep", "-f", "claude_watchdog\\.cli"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return []
        my_pid = os.getpid()
        return [int(p) for p in r.stdout.strip().split() if p and int(p) != my_pid]
    except Exception:
        return []


def _get_daemon_pid() -> int | None:
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
                # Check if still alive
                os.kill(pid, 0)
                return pid
        except (ValueError, ProcessLookupError, OSError):
            pass
    # Fallback: pgrep
    pids = _find_watchdog_pids()
    if pids:
        return pids[0]
    return None


def _save_pid(pid: int):
    d = os.path.dirname(PID_FILE)
    os.makedirs(d, exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(pid))


def _run_watcher(args):
    """Internal: run the monitoring loop (called from forked child)."""
    if args.session:
        watch_loop(args.session, interval=args.interval, use_notify=args.notify, alert_only=args.alert_only)
    else:
        watch_all(interval=args.interval, use_notify=args.notify, alert_only=args.alert_only)


def _cmd_start(args):
    pids = _find_watchdog_pids()
    if pids:
        print(f"Watchdog already running (PID: {pids[0]}). Use 'stop' first or 'restart'.")
        return

    # Fork the watcher directly
    pid = os.fork()
    if pid > 0:
        # Parent: record PID and return
        _save_pid(pid)
        print(f"Watchdog started (PID: {pid}) — watching {'all claude-* sessions' if not args.session else args.session}")
        return

    # Child: run watcher loop
    _run_watcher(args)


def _cmd_stop(args):
    pid = _get_daemon_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Watchdog stopped (PID: {pid})")
        except ProcessLookupError:
            print("Watchdog not running.")
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return

    pids = _find_watchdog_pids()
    if pids:
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Watchdog stopped (PID: {pid})")
            except ProcessLookupError:
                pass
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    else:
        print("Watchdog not running.")


def _cmd_status(args):
    pid = _get_daemon_pid()
    if pid:
        try:
            r = subprocess.run(
                ["ps", "-p", str(pid), "-o", "%cpu,%mem,rss,etime"],
                capture_output=True, text=True, timeout=5,
            )
            stats = r.stdout.strip().split("\n")[-1] if r.stdout else "?"
            print(f"Watchdog is running (PID: {pid})")
            print(f"  Resources: {stats}")
            print(f"  Log: {os.path.expanduser('~/.local/share/claude-watchdog/hits.log')}")
            return
        except (subprocess.TimeoutExpired, IndexError):
            pass

    pids = _find_watchdog_pids()
    if pids:
        print(f"Watchdog is running (PID: {', '.join(str(p) for p in pids)})")
    else:
        print("Watchdog is not running.")


def _cmd_restart(args):
    _cmd_stop(args)
    _cmd_start(args)


def _cmd_log(args):
    read_log(
        last=args.last,
        follow=not args.no_follow,
        session_filter=args.session,
    )


def main():
    parser = argparse.ArgumentParser(
        prog="claude-watchdog",
        description="Claude Code tmux watchdog — auto-unblock permission dialogs",
    )
    sub = parser.add_subparsers(dest="command", help="Subcommands")

    # ── start ──
    p_start = sub.add_parser("start", help="Start the watchdog daemon")
    p_start.add_argument("--session", "-s", type=str, default=None,
                         help="Monitor specific session (default: all claude-* sessions)")
    p_start.add_argument("--interval", "-i", type=int, default=15,
                         help="Poll interval in seconds (default: 15)")
    p_start.add_argument("--notify", "-n", action="store_true",
                         help="Send notification on hit via hermes-notify")
    p_start.add_argument("--alert-only", action="store_true",
                         help="Log+notify only, do NOT auto-approve dialogs")

    # ── stop ──
    sub.add_parser("stop", help="Stop the watchdog daemon")

    # ── restart ──
    p_restart = sub.add_parser("restart", help="Restart the watchdog daemon")
    p_restart.add_argument("--session", "-s", type=str, default=None)
    p_restart.add_argument("--interval", "-i", type=int, default=15)
    p_restart.add_argument("--notify", "-n", action="store_true")
    p_restart.add_argument("--alert-only", action="store_true")

    # ── status ──
    sub.add_parser("status", help="Show watchdog daemon status")

    # ── log ──
    p_log = sub.add_parser("log", help="View hit log (follows by default, like tail -f)")
    p_log.add_argument("--last", type=int, default=20,
                       help="Last N entries to show on connect (default: 20)")
    p_log.add_argument("--no-follow", action="store_true",
                       help="Print last N entries and exit (don't tail)")
    p_log.add_argument("--session", "-s", type=str, default=None,
                       help="Filter by session name")

    # ── Legacy flags (keep backward compat) ──
    parser.add_argument("--session", "-s", type=str, default=None,
                        help=argparse.SUPPRESS)
    parser.add_argument("--all", "-a", action="store_true",
                        help=argparse.SUPPRESS)
    parser.add_argument("--daemon", "-d", action="store_true",
                        help=argparse.SUPPRESS)
    parser.add_argument("--interval", "-i", type=int, default=15,
                        help=argparse.SUPPRESS)
    parser.add_argument("--notify", "-n", action="store_true",
                        help=argparse.SUPPRESS)
    parser.add_argument("--alert-only", action="store_true",
                        help=argparse.SUPPRESS)
    parser.add_argument("--log", "-l", action="store_true",
                        help=argparse.SUPPRESS)
    parser.add_argument("--last", type=int, default=20,
                        help=argparse.SUPPRESS)
    parser.add_argument("--follow", "-f", action="store_true",
                        help=argparse.SUPPRESS)

    args = parser.parse_args()

    # ── Subcommand dispatch ──
    if args.command == "start":
        _cmd_start(args)
        return
    elif args.command == "stop":
        _cmd_stop(args)
        return
    elif args.command == "status":
        _cmd_status(args)
        return
    elif args.command == "restart":
        _cmd_restart(args)
        return
    elif args.command == "log":
        _cmd_log(args)
        return

    # ── Legacy backward compat ──
    if args.log:
        read_log(last=args.last, follow=args.follow, session_filter=args.session)
        return

    # No subcommand + no legacy flags
    if not args.session and not args.all:
        parser.print_help()
        sys.exit(1)

    # One-shot check
    from .watcher import check_session, session_exists
    if args.all:
        sessions = get_sessions()
        for s in sessions:
            check_session(s, args.notify, args.alert_only)
    elif args.session:
        if not session_exists(args.session):
            print(f"Session '{args.session}' not found.")
            sys.exit(1)
        check_session(args.session, args.notify, args.alert_only)
    return


if __name__ == "__main__":
    main()
