"""Optional notify integration — bridges to hermes-notify if available."""
import shutil
import subprocess
import shlex


def _notify_cmd() -> str | None:
    """Return notify CLI path if installed."""
    return shutil.which("hermes-notify") or shutil.which("notify")


def send_hit(session: str, rule_name: str, detail: str):
    cmd = _notify_cmd()
    if not cmd:
        return  # notify not installed, silent skip
    try:
        text = shlex.quote(f"[watchdog] {session}: {detail}")
        subprocess.run(
            f"{cmd} send --type progress --text {text}",
            shell=True,
            timeout=5,
            capture_output=True,
        )
    except Exception:
        pass  # notify failure is non-critical
