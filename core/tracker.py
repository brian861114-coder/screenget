"""
tracker.py - 前景視窗追蹤引擎
使用 Windows API 偵測當前前景視窗，記錄各程式的使用時間。
"""

import ctypes
import ctypes.wintypes
import time
import threading
import logging
from datetime import datetime
from typing import Optional, Callable

import psutil

from core.database import UsageDatabase
from core.process_filter import ProcessFilter

logger = logging.getLogger(__name__)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GetForegroundWindow = user32.GetForegroundWindow
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetWindowThreadProcessId = user32.GetWindowThreadProcessId

BROWSER_PROCESS_NAMES = frozenset({
    "Google Chrome", "Microsoft Edge", "Mozilla Firefox",
    "Brave", "Opera", "Vivaldi", "Arc",
})


def get_foreground_window_info() -> Optional[dict]:
    """取得當前前景視窗的資訊"""
    try:
        hwnd = GetForegroundWindow()
        if not hwnd:
            return None

        length = GetWindowTextLengthW(hwnd)
        if length == 0:
            return None
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value

        if not title.strip():
            return None

        pid = ctypes.wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        pid_value = pid.value

        if pid_value == 0:
            return None

        try:
            proc = psutil.Process(pid_value)
            process_name = proc.name()
            exe_path = proc.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None

        return {
            "hwnd": hwnd,
            "title": title,
            "pid": pid_value,
            "process_name": process_name,
            "exe_path": exe_path,
        }
    except Exception as e:
        logger.error(f"Error getting foreground window: {e}")
        return None


class UsageTracker:
    """使用量追蹤器 - 在背景執行緒中追蹤前景視窗"""

    def __init__(self, db: UsageDatabase, poll_interval: float = 1.0):
        self.db = db
        self.poll_interval = poll_interval
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._current_session_id: Optional[int] = None
        self._current_app: Optional[str] = None
        self._current_title: Optional[str] = None
        self._current_app_type: Optional[str] = None
        self._current_exe_path: Optional[str] = None
        self._bridge_domain: Optional[str] = None
        # RLock：避免 pause() 持鎖時呼叫 _end_current_session() 造成死鎖
        self._lock = threading.RLock()
        self._on_app_change: Optional[Callable] = None

    def set_on_app_change(self, callback: Callable):
        """設定視窗切換時的回呼函式（可能在背景執行緒呼叫）"""
        self._on_app_change = callback

    def start(self):
        """開始追蹤"""
        if self._running:
            return
        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._thread.start()
        logger.info("Tracker started")

    def stop(self):
        """停止追蹤"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._end_current_session()
        logger.info("Tracker stopped")

    def pause(self, end_time: Optional[datetime] = None):
        """暫停追蹤（閒置或手動）。可指定 session 結束時間以排除閒置時段。"""
        with self._lock:
            if not self._paused:
                self._paused = True
                self._end_current_session(end_time=end_time)
                logger.info("Tracker paused")

    def resume(self):
        """恢復追蹤"""
        with self._lock:
            if self._paused:
                self._paused = False
                logger.info("Tracker resumed")

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_running(self) -> bool:
        return self._running

    def _tracking_loop(self):
        """追蹤主迴圈：暫停時不持鎖 sleep，避免卡住 resume/bridge。"""
        while self._running:
            try:
                with self._lock:
                    paused = self._paused
                if paused:
                    time.sleep(self.poll_interval)
                    continue

                info = get_foreground_window_info()
                if info:
                    self._handle_window_change(info)

            except Exception as e:
                logger.error(f"Tracking error: {e}")

            time.sleep(self.poll_interval)

    def _handle_window_change(self, info: dict):
        """處理視窗切換事件"""
        process_name = info["process_name"]
        window_title = info["title"]
        exe_path = info["exe_path"]

        if not ProcessFilter.should_track(process_name, exe_path):
            if self._current_app is not None:
                self._end_current_session()
                with self._lock:
                    self._current_app = None
                    self._current_title = None
                    self._current_app_type = None
                    self._current_exe_path = None
                    self._bridge_domain = None
            return

        display_name = ProcessFilter.get_display_name(process_name, window_title)
        app_type = ProcessFilter.get_app_type(process_name, exe_path)

        with self._lock:
            if self._paused:
                return

            # 仍在同一個瀏覽器進程：標題變更不重開 session，交給 bridge 切網域
            if (
                app_type == "browser"
                and self._current_app_type == "browser"
                and display_name in BROWSER_PROCESS_NAMES | {self._current_app}
                and (
                    self._bridge_domain is not None
                    or self._current_app == display_name
                    or self._current_exe_path == exe_path
                )
            ):
                if self._current_exe_path and exe_path and self._current_exe_path != exe_path:
                    pass
                else:
                    if window_title != self._current_title:
                        self._current_title = window_title
                        if self._current_session_id is not None:
                            try:
                                self.db.update_session_url(
                                    self._current_session_id,
                                    url="",
                                    window_title=window_title,
                                )
                            except Exception:
                                pass
                    return

            if display_name == self._current_app and window_title == self._current_title:
                return

        self._end_current_session()

        with self._lock:
            # pause 可能在 end_session 期間發生
            if self._paused:
                return

            self._current_app = display_name
            self._current_title = window_title
            self._current_app_type = app_type
            self._current_exe_path = exe_path
            self._bridge_domain = None
            try:
                self._current_session_id = self.db.start_session(
                    app_name=display_name,
                    window_title=window_title,
                    exe_path=exe_path,
                    app_type=app_type,
                )
            except Exception as e:
                logger.error(f"Failed to start session: {e}")
                self._current_session_id = None
                return

            logger.debug(f"New session: {display_name} - {window_title}")

            if app_type == "browser":
                try:
                    from core.browser_bridge import read_bridge_event, extract_domain
                    event = read_bridge_event()
                    if event and event.get("type") == "page_start" and event.get("url"):
                        domain = extract_domain(event["url"])
                        if domain:
                            old_id = self._current_session_id
                            if old_id is not None:
                                self.db.end_session(old_id)
                            self._current_app = domain
                            self._current_title = event.get("title") or domain
                            self._bridge_domain = domain
                            self._current_session_id = self.db.start_session(
                                app_name=domain,
                                window_title=self._current_title,
                                exe_path=exe_path,
                                app_type="browser",
                                url=event.get("url", ""),
                            )
                            display_name = domain
                            window_title = self._current_title
                except Exception as e:
                    logger.error(f"Failed to apply pending bridge state: {e}")

            self._emit_app_change(display_name, window_title, app_type)

    def _emit_app_change(self, app_name: str, title: str, app_type: str):
        if not self._on_app_change:
            return
        try:
            self._on_app_change(app_name, title, app_type)
        except Exception as e:
            logger.error(f"App change callback error: {e}")

    def _end_current_session(self, end_time: Optional[datetime] = None):
        """結束當前 session。若提供 end_time，以該時間結束（閒置排除）。"""
        with self._lock:
            if self._current_session_id is not None:
                try:
                    if end_time is not None:
                        self.db.end_session_at(self._current_session_id, end_time)
                    else:
                        self.db.end_session(self._current_session_id)
                except Exception as e:
                    logger.error(f"Error ending session: {e}")
                self._current_session_id = None

    def update_browser_url(self, url: str, title: str = ""):
        """更新當前瀏覽器 session 的 URL（由瀏覽器擴充套件呼叫）"""
        with self._lock:
            if self._current_session_id is not None:
                try:
                    self.db.update_session_url(self._current_session_id, url, title)
                except Exception as e:
                    logger.error(f"Error updating URL: {e}")

    def apply_browser_page(self, url: str, title: str = "") -> bool:
        """
        套用瀏覽器橋接的頁面事件：
        若目前前景是瀏覽器，將 session 以網域重新命名／切分。
        """
        from core.browser_bridge import extract_domain

        domain = extract_domain(url)
        if not domain:
            return False

        with self._lock:
            if self._paused or self._current_app_type != "browser":
                return False

            if self._bridge_domain == domain and self._current_session_id is not None:
                self._current_title = title or self._current_title
                try:
                    self.db.update_session_url(
                        self._current_session_id, url, title or ""
                    )
                except Exception as e:
                    logger.error(f"Error updating browser URL: {e}")
                return True

            old_id = self._current_session_id
            exe_path = self._current_exe_path or ""
            if old_id is not None:
                try:
                    self.db.end_session(old_id)
                except Exception as e:
                    logger.error(f"Error ending browser session: {e}")
                self._current_session_id = None

            self._current_app = domain
            self._current_title = title or domain
            self._bridge_domain = domain
            self._current_app_type = "browser"
            try:
                self._current_session_id = self.db.start_session(
                    app_name=domain,
                    window_title=title or domain,
                    exe_path=exe_path,
                    app_type="browser",
                    url=url,
                )
            except Exception as e:
                logger.error(f"Failed to start browser session: {e}")
                self._current_session_id = None
                return False

            logger.info(f"Browser bridge session: {domain}")
            self._emit_app_change(domain, title or domain, "browser")
            return True

    @property
    def current_app_type(self) -> Optional[str]:
        return self._current_app_type
