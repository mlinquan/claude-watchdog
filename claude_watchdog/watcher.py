import re
import subprocess
import time

from .rules import RULES
from .logger import log_hit


def get_sessions() -> list[str]:
    """List all running tmux sessions whose name starts with 'claude-'."""
    try:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True, text=True, timeout=5,
        )
        return [s.strip() for s in result.stdout.splitlines() if s.strip().startswith("claude-")]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def session_exists(session: str) -> bool:
    try:
        subprocess.run(
            ["tmux", "has-session", "-t", session],
            capture_output=True, timeout=3, check=True,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def capture_pane(session: str, lines: int = 15) -> str:
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", session, "-p", "-S", f"-{lines}"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def send_keys(session: str, keys: list[str]):
    for key in keys:
        subprocess.run(
            ["tmux", "send-keys", "-t", session, key],
            capture_output=True, timeout=3,
        )


def check_session(session: str, use_notify: bool = False, alert_only: bool = False) -> bool:
    """
    Check a single session for blocked dialogs.
    Returns True if a dialog was detected and cleared.
    """
    output = capture_pane(session)
    if not output:
        return False

    for name, pattern, keys, desc in RULES:
        if re.search(pattern, output, re.MULTILINE):
            if not alert_only:
                send_keys(session, keys)
            log_hit(session, name, desc)
            if use_notify:
                from .notify import send_hit
                send_hit(session, name, desc)
            return True
    return False


def watch_loop(session: str, interval: int = 10, use_notify: bool = False, alert_only: bool = False):
    """Continuously monitor a session until it disappears."""
    while session_exists(session):
        check_session(session, use_notify, alert_only)
        time.sleep(interval)


def watch_all(interval: int = 10, use_notify: bool = False, alert_only: bool = False):
    """Monitor all claude-* sessions in a round-robin."""
    while True:
        sessions = get_sessions()
        if not sessions:
            time.sleep(interval)
            continue
        for s in sessions:
            check_session(s, use_notify, alert_only)
        time.sleep(interval)
