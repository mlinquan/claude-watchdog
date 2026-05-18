"""Optional notify integration — bridges to hermes-notify if available."""
import shutil
import subprocess


def _notify_cmd() -> str | None:
    """Return notify CLI path if installed."""
    return shutil.which("notify-hermes") or shutil.which("hermes-notify")


def send_hit(session: str, rule_name: str, detail: str):
    cmd = _notify_cmd()
    if not cmd:
        return  # notify not installed, silent skip
    try:
        text = f"[watchdog] {session}: {detail}"
        subprocess.run(
            [cmd, "--to", "hermes-bus", "--type", "progress", text],
            timeout=5,
            capture_output=True,
        )
    except Exception:
        pass  # notify failure is non-critical
