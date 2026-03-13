"""
tracker.py - 前景視窗追蹤引擎
使用 Windows API 偵測當前前景視窗，記錄各程式的使用時間。
"""

import ctypes
import ctypes.wintypes
import time
import threading
import logging
from typing import Optional, Callable

import psutil

from core.database import UsageDatabase
from core.process_filter import ProcessFilter

logger = logging.getLogger(__name__)

# Windows API 定義
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GetForegroundWindow = user32.GetForegroundWindow
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetWindowThreadProcessId = user32.GetWindowThreadProcessId


def get_foreground_window_info() -> Optional[dict]:
    """取得當前前景視窗的資訊"""
    try:
        hwnd = GetForegroundWindow()
        if not hwnd:
            return None

        # 取得視窗標題
        length = GetWindowTextLengthW(hwnd)
        if length == 0:
            return None
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value

        if not title.strip():
            return None

        # 取得程序 ID
        pid = ctypes.wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        pid_value = pid.value

        if pid_value == 0:
            return None

        # 取得程序資訊
        try:
            proc = psutil.Process(pid_value)
            process_name = proc.name()
            exe_path = proc.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None

        return {
            'hwnd': hwnd,
            'title': title,
            'pid': pid_value,
            'process_name': process_name,
            'exe_path': exe_path,
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
        self._lock = threading.Lock()
        self._on_app_change: Optional[Callable] = None

    def set_on_app_change(self, callback: Callable):
        """設定視窗切換時的回呼函式"""
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

    def pause(self):
        """暫停追蹤（閒置時呼叫）"""
        with self._lock:
            if not self._paused:
                self._paused = True
                self._end_current_session()
                logger.info("Tracker paused (idle)")

    def resume(self):
        """恢復追蹤（使用者恢復操作時呼叫）"""
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
        """追蹤主迴圈"""
        while self._running:
            try:
                with self._lock:
                    if self._paused:
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
        process_name = info['process_name']
        window_title = info['title']
        exe_path = info['exe_path']

        # 檢查是否應該追蹤此程式
        if not ProcessFilter.should_track(process_name, exe_path):
            # 如果切換到了不追蹤的程式，結束當前 session
            if self._current_app is not None:
                self._end_current_session()
                self._current_app = None
                self._current_title = None
            return

        # 取得顯示名稱和程式類型
        display_name = ProcessFilter.get_display_name(process_name, window_title)
        app_type = ProcessFilter.get_app_type(process_name, exe_path)

        # 檢查是否是同一個程式（同名且相同視窗標題不需要重新記錄）
        if display_name == self._current_app and window_title == self._current_title:
            return

        # 如果是同一個瀏覽器但標題改了（切換分頁），也要記錄新 session
        # 如果是其他程式切換，也要記錄新 session

        # 結束前一個 session
        self._end_current_session()

        # 開始新 session
        with self._lock:
            self._current_app = display_name
            self._current_title = window_title
            self._current_session_id = self.db.start_session(
                app_name=display_name,
                window_title=window_title,
                exe_path=exe_path,
                app_type=app_type,
            )
            logger.debug(f"New session: {display_name} - {window_title}")

            if self._on_app_change:
                try:
                    self._on_app_change(display_name, window_title, app_type)
                except Exception as e:
                    logger.error(f"App change callback error: {e}")

    def _end_current_session(self):
        """結束當前 session"""
        with self._lock:
            if self._current_session_id is not None:
                try:
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
