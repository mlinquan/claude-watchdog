#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess
import sys

from .watcher import watch_loop, watch_all, get_sessions
from .logger import read_log


def _find_watchdog_pids() -> list[int]:
    """Find all running claude-watchdog daemon processes (excluding this one)."""
    try:
        r = subprocess.run(
            ["pgrep", "-f", "claude-watchdog"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return []
        my_pid = os.getpid()
        return [int(p) for p in r.stdout.strip().split() if p and int(p) != my_pid]
    except Exception:
        return []


def _do_restart(args):
    pids = _find_watchdog_pids()
    if pids:
        print(f"Stopping existing watchdog (PID: {', '.join(str(p) for p in pids)})...")
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        # Wait for them to die
        try:
            subprocess.run(["sleep", "1"], timeout=3)
        except Exception:
            pass

    # Default: --all --daemon if no specific session given
    cmd = [sys.executable, "-m", "claude_watchdog.cli"]
    if args.session:
        cmd += ["--session", args.session]
    else:
        cmd += ["--all"]
    cmd += ["--daemon", "--interval", str(args.interval or 15)]
    if args.notify:
        cmd += ["--notify"]
    if args.alert_only:
        cmd += ["--alert-only"]

    print(f"Starting: {' '.join(cmd)}")
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    print("OK. (run 'claude-watchdog --log --follow' to see activity)")


def main():
    parser = argparse.ArgumentParser(
        prog="claude-watchdog",
        description="Claude Code tmux watchdog — auto-unblock permission dialogs",
    )

    # Restart mode
    parser.add_argument("restart", nargs="?", const=False, default=False,
                        help="Restart the watchdog daemon")

    # Monitor mode
    parser.add_argument("--session", "-s", type=str, default=None,
                        help="Session name to monitor (e.g. claude-tl)")
    parser.add_argument("--all", "-a", action="store_true",
                        help="Monitor all claude-* sessions")
    parser.add_argument("--daemon", "-d", action="store_true",
                        help="Run continuously until session ends")
    parser.add_argument("--interval", "-i", type=int, default=15,
                        help="Poll interval in seconds (default: 15)")
    parser.add_argument("--notify", "-n", action="store_true",
                        help="Send notification on hit via hermes-notify")
    parser.add_argument("--alert-only", action="store_true",
                        help="Log+notify only, do NOT auto-approve dialogs")

    # Log mode
    parser.add_argument("--log", "-l", action="store_true",
                        help="View hit log")
    parser.add_argument("--last", type=int, default=20,
                        help="Last N log entries (default: 20)")
    parser.add_argument("--follow", "-f", action="store_true",
                        help="Tail -f the log")

    args = parser.parse_args()

    # ── restart mode ──
    if args.restart is not False or os.path.basename(sys.argv[0]) == "claude-watchdog-restart":
        _do_restart(args)
        return

    # ── log mode ──
    if args.log:
        read_log(last=args.last, follow=args.follow, session_filter=args.session)
        return

    # ── daemon without --session or --all: auto-detect ──
    if args.daemon and not args.session and not args.all:
        sessions = get_sessions()
        if not sessions:
            print("No claude-* tmux sessions found.")
            sys.exit(1)
        if len(sessions) == 1:
            args.session = sessions[0]
        else:
            print(f"Multiple sessions found: {', '.join(sessions)}. Use --session or --all.")
            sys.exit(1)

    # Validate
    if not args.session and not args.all:
        parser.print_help()
        sys.exit(1)

    # One-shot check
    if not args.daemon:
        from .watcher import check_session
        if args.all:
            sessions = get_sessions()
            for s in sessions:
                check_session(s, args.notify, args.alert_only)
        else:
            from .watcher import session_exists
            if not session_exists(args.session):
                print(f"Session '{args.session}' not found.")
                sys.exit(1)
            check_session(args.session, args.notify, args.alert_only)
        return

    # Daemon mode
    if args.all:
        print(f"Watching all claude-* sessions (interval={args.interval}s)")
        watch_all(interval=args.interval, use_notify=args.notify, alert_only=args.alert_only)
    else:
        print(f"Watching session '{args.session}' (interval={args.interval}s)")
        watch_loop(args.session, interval=args.interval, use_notify=args.notify, alert_only=args.alert_only)


if __name__ == "__main__":
    main()
