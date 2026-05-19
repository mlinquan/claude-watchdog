import json
import os
import time
from datetime import datetime

LOG_DIR = os.path.expanduser("~/.local/share/claude-watchdog")
LOG_FILE = os.path.join(LOG_DIR, "hits.log")


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def log_hit(session: str, rule_name: str, detail: str):
    _ensure_log_dir()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = json.dumps({"ts": ts, "session": session, "rule": rule_name, "detail": detail})
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    # Also print to stdout so --daemon runner sees it
    print(f"[{ts}] ⛔ [{session}] {detail}")


def _format_entry(entry: dict) -> str:
    ts = entry.get("ts", "?")
    session = entry.get("session", "?")
    detail = entry.get("detail", "")
    return f"[{ts}] ⛔ [{session}] {detail}"


def read_log(last: int = 20, follow: bool = False, session_filter: str | None = None):
    _ensure_log_dir()
    if not os.path.exists(LOG_FILE):
        print("No hits yet.")
        return

    if follow:
        # Python tail -f with formatted output
        try:
            with open(LOG_FILE) as f:
                # Seek to end for follow mode
                lines = f.readlines()
                for line in lines[-last:]:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if session_filter and entry.get("session") != session_filter:
                            continue
                        print(_format_entry(entry))
                    except json.JSONDecodeError:
                        print(line)

                # Watch for new lines
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.5)
                        continue
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if session_filter and entry.get("session") != session_filter:
                            continue
                        print(_format_entry(entry))
                    except json.JSONDecodeError:
                        print(line)
        except KeyboardInterrupt:
            pass
        return

    lines = []
    with open(LOG_FILE) as f:
        for line in f:
            lines.append(line)

    for line in lines[-last:]:
        try:
            entry = json.loads(line)
            if session_filter and entry.get("session") != session_filter:
                continue
            print(_format_entry(entry))
        except json.JSONDecodeError:
            print(line.strip())
