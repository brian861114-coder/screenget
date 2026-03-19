"""
idle_detector.py - 閒置偵測模組
偵測使用者是否閒置（20分鐘無操作）或電腦進入休眠模式。
閒置時暫停追蹤，恢復時繼續追蹤。
"""

import ctypes
import ctypes.wintypes
import threading
import time
import logging
from typing import Callable, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Windows API - GetLastInputInfo
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', ctypes.wintypes.UINT),
        ('dwTime', ctypes.wintypes.DWORD),
    ]


def get_idle_seconds() -> float:
    """取得使用者閒置秒數"""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    return 0.0


class IdleDetector:
    """閒置偵測器"""

    def __init__(self, idle_timeout_minutes: int = 20,
                 on_idle: Optional[Callable] = None,
                 on_resume: Optional[Callable] = None,
                 check_interval: float = 5.0):
        """
        Args:
            idle_timeout_minutes: 閒置超時時間（分鐘）
            on_idle: 進入閒置狀態時的回呼
            on_resume: 從閒置恢復時的回呼
            check_interval: 檢查間隔（秒）
        """
        self.idle_timeout = idle_timeout_minutes * 60  # 轉換為秒
        self.on_idle = on_idle
        self.on_resume = on_resume
        self.check_interval = check_interval
        self._is_idle = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._idle_start_time: Optional[datetime] = None

    def start(self):
        """開始閒置偵測"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        logger.info(f"Idle detector started (timeout: {self.idle_timeout}s)")

    def stop(self):
        """停止閒置偵測"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Idle detector stopped")

    @property
    def is_idle(self) -> bool:
        return self._is_idle

    @property
    def idle_start_time(self) -> Optional[datetime]:
        return self._idle_start_time

    def _detection_loop(self):
        """偵測主迴圈"""
        while self._running:
            try:
                idle_seconds = get_idle_seconds()

                if not self._is_idle and idle_seconds >= self.idle_timeout:
                    # 進入閒置狀態
                    self._is_idle = True
                    # 閒置開始時間 = 現在 - 閒置秒數（即最後操作的時間點）
                    self._idle_start_time = datetime.now() - timedelta(seconds=idle_seconds)
                    logger.info(f"User idle for {idle_seconds:.0f}s, pausing tracking")
                    if self.on_idle:
                        try:
                            self.on_idle(self._idle_start_time)
                        except Exception as e:
                            logger.error(f"Idle callback error: {e}")

                elif self._is_idle and idle_seconds < self.idle_timeout:
                    # 從閒置恢復
                    self._is_idle = False
                    resume_time = datetime.now()
                    logger.info("User active, resuming tracking")
                    if self.on_resume:
                        try:
                            self.on_resume(resume_time)
                        except Exception as e:
                            logger.error(f"Resume callback error: {e}")
                    self._idle_start_time = None

            except Exception as e:
                logger.error(f"Idle detection error: {e}")

            time.sleep(self.check_interval)
