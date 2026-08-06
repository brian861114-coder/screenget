"""
browser_bridge.py - 瀏覽器 Native Messaging 橋接
Native Host 只寫入狀態檔，由主程式套用到 tracker，避免雙重計時。
並在啟動時自動註冊 Chrome / Edge Native Messaging Host。
"""

import json
import os
import sys
import logging
import winreg
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

HOST_NAME = "com.screenget.host"
DEFAULT_EXTENSION_ID = "eociggeoliljeoidbbhkeoelaainhkcp"


def get_app_data_dir() -> str:
    path = os.path.join(os.getenv("APPDATA", ""), "ScreenGet")
    os.makedirs(path, exist_ok=True)
    return path


def bridge_state_path() -> str:
    return os.path.join(get_app_data_dir(), "browser_bridge.json")


def extract_domain(url: str) -> str:
    """從 URL 提取顯示用網域"""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        if parsed.scheme in ("chrome", "edge", "about", "chrome-extension", "brave", "opera"):
            host = parsed.netloc or "internal"
            return f"{parsed.scheme}://{host}"
        if parsed.netloc:
            return parsed.netloc.removeprefix("www.")
        return url[:80]
    except Exception:
        return url[:80]


def write_bridge_event(event_type: str, url: str = "", title: str = "") -> None:
    """Native Host 寫入最新瀏覽器事件（原子寫入）"""
    payload = {
        "type": event_type,
        "url": url or "",
        "title": title or "",
        "domain": extract_domain(url) if url else "",
        "timestamp": datetime.now().isoformat(),
        "seq": int(datetime.now().timestamp() * 1000),
    }
    path = bridge_state_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, path)


def read_bridge_event() -> Optional[Dict[str, Any]]:
    path = bridge_state_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read bridge state: {e}")
        return None


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _native_messaging_dir() -> str:
    return os.path.join(_project_root(), "native_messaging")


def _python_for_host() -> str:
    """Native host 需要有主控台的 python，避免 stdin 問題；優先 python.exe"""
    exe = sys.executable
    if exe.lower().endswith("pythonw.exe"):
        candidate = exe[:-11] + "python.exe"
        if os.path.exists(candidate):
            return candidate
    return exe


def ensure_host_files(extension_id: str = DEFAULT_EXTENSION_ID) -> str:
    """
    產生/更新 run_host.bat 與 com.screenget.host.json，回傳 json 路徑。
    """
    nm_dir = _native_messaging_dir()
    os.makedirs(nm_dir, exist_ok=True)

    host_py = os.path.join(nm_dir, "native_host.py")
    bat_path = os.path.join(nm_dir, "run_host.bat")
    json_path = os.path.join(nm_dir, "com.screenget.host.json")
    python_exe = _python_for_host()

    bat_content = (
        "@echo off\r\n"
        f"\"{python_exe}\" -u \"{host_py}\" %*\r\n"
    )
    with open(bat_path, "w", encoding="utf-8", newline="") as f:
        f.write(bat_content)

    origin = f"chrome-extension://{extension_id}/"
    manifest = {
        "name": HOST_NAME,
        "description": "ScreenGet Native Messaging Host",
        "path": bat_path.replace("/", "\\"),
        "type": "stdio",
        "allowed_origins": [origin],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4, ensure_ascii=False)

    return json_path


def register_native_host(extension_id: str = DEFAULT_EXTENSION_ID) -> bool:
    """註冊 Chrome / Edge Native Messaging Host 到 HKCU"""
    if sys.platform != "win32":
        return False
    try:
        json_path = ensure_host_files(extension_id)
        for base in (
            r"Software\Google\Chrome\NativeMessagingHosts",
            r"Software\Microsoft\Edge\NativeMessagingHosts",
        ):
            key_path = f"{base}\\{HOST_NAME}"
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, json_path)
        logger.info(f"Native messaging host registered: {json_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to register native host: {e}", exc_info=True)
        return False


class BrowserBridgeWatcher:
    """輪詢 bridge 狀態檔，將頁面事件套用到 tracker"""

    def __init__(self, on_page: Callable[[str, str, str], None],
                 poll_interval_ms: int = 1000):
        """
        on_page(event_type, url, title)
        """
        self.on_page = on_page
        self.poll_interval_ms = poll_interval_ms
        self._last_seq: Optional[int] = None
        self._timer = None

    def start(self, parent=None):
        from PyQt6.QtCore import QTimer
        self._timer = QTimer(parent)
        self._timer.timeout.connect(self.poll)
        self._timer.start(self.poll_interval_ms)
        # 初始化時讀取但不套用舊事件，避免重播
        event = read_bridge_event()
        if event:
            self._last_seq = event.get("seq")

    def stop(self):
        if self._timer:
            self._timer.stop()

    def poll(self):
        event = read_bridge_event()
        if not event:
            return
        seq = event.get("seq")
        if seq is None or seq == self._last_seq:
            return
        self._last_seq = seq
        try:
            self.on_page(
                event.get("type", ""),
                event.get("url", ""),
                event.get("title", ""),
            )
        except Exception as e:
            logger.error(f"Bridge page handler error: {e}", exc_info=True)

    @staticmethod
    def is_connected(max_age_seconds: float = 120.0) -> bool:
        """依狀態檔時間戳判斷擴充套件是否近期有回報"""
        event = read_bridge_event()
        if not event or not event.get("timestamp"):
            return False
        try:
            ts = datetime.fromisoformat(event["timestamp"])
            return (datetime.now() - ts).total_seconds() <= max_age_seconds
        except Exception:
            return False
