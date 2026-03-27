"""
browser.py - Chrome 瀏覽器安裝與啟動管理

對外介面:
  ensure_installed()              確認 Chromium 已安裝，否則安裝
  ensure_running(cdp_url, ext_dir) 確認 Chrome 已啟動，否則啟動
  get_session_path()              取得 Chrome session 目錄路徑
"""

import glob, os, subprocess, time, urllib.request
from pathlib import Path

_CDP_PORT = int(os.environ.get("LINE_PERSONAL_CDP_PORT", "9222"))
_DISPLAY  = os.environ.get("LINE_PERSONAL_DISPLAY", ":99")


def ensure_installed() -> None:
    if _find_chrome():
        return
    print(">>> 安裝 Chromium...")
    subprocess.run(
        ["uv", "run", "--with", "playwright",
         "python3", "-m", "playwright", "install", "chromium"],
        check=True)


def ensure_running(cdp_url: str, ext_dir: Path) -> None:
    _ensure_display()
    if _is_up(cdp_url):
        return
    print(">>> Chrome 未啟動，正在啟動...")
    session = get_session_path()
    _start(cdp_url, session, ext_dir)


def get_session_path() -> str:
    if val := os.environ.get("LINE_PERSONAL_SESSION"):
        return val
    logos_root = os.environ.get("LOGOS_ROOT", "")
    if logos_root:
        r = subprocess.run(
            ["bash", f"{logos_root}/internal-control/scripts/get-secret.sh",
             "line-personal-session", "liaison/switchboard"],
            capture_output=True, text=True, check=True)
        return r.stdout.strip()
    raise RuntimeError("需設定 LINE_PERSONAL_SESSION 或 LOGOS_ROOT")


# ── 私有 ──────────────────────────────────────────────────────────

def _ensure_display() -> None:
    import shutil
    if not shutil.which("Xvfb"):
        return  # 非 Linux headless 環境，略過
    r = subprocess.run(["pgrep", "-f", f"Xvfb.*{_DISPLAY}"], capture_output=True)
    if r.returncode == 0:
        return
    print(f">>> Xvfb {_DISPLAY} 未啟動，正在啟動...")
    subprocess.Popen(
        ["Xvfb", _DISPLAY, "-screen", "0", "1280x720x24"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1)


def _find_chrome() -> str | None:
    candidates = [
        "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
        *reversed(sorted(glob.glob(
            str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux64/chrome")))),
    ]
    import shutil
    for c in candidates:
        if Path(c).is_file() and os.access(c, os.X_OK):
            return c
        if shutil.which(c):
            return c
    return None


def _is_up(cdp_url: str) -> bool:
    try:
        urllib.request.urlopen(cdp_url + "/json/version", timeout=2)
        return True
    except Exception:
        return False


def _start(cdp_url: str, session: str, ext_dir: Path) -> None:
    chrome = _find_chrome()
    port = cdp_url.rsplit(":", 1)[-1]
    Path(session, "Default", "LOCK").unlink(missing_ok=True)

    subprocess.Popen(
        [chrome,
         f"--remote-debugging-port={port}",
         f"--user-data-dir={session}",
         "--profile-directory=Default",
         f"--load-extension={ext_dir}",
         "--no-sandbox", "--disable-dev-shm-usage",
         "--disable-gpu", "--no-first-run"],
        env={**os.environ, "DISPLAY": _DISPLAY},
        stdout=open("/tmp/chrome-line.log", "w"),
        stderr=subprocess.STDOUT,
    )
    for _ in range(15):
        time.sleep(1)
        if _is_up(cdp_url):
            return
    raise RuntimeError("Chrome 啟動逾時，請查看 /tmp/chrome-line.log")
