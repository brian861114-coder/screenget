"""
main.py - ScreenGet 應用程式入口
初始化所有模組並啟動應用程式。
"""

import sys
import os
import logging
from datetime import datetime

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from core.database import UsageDatabase
from core.tracker import UsageTracker
from core.idle_detector import IdleDetector
from core.analyzer import UsageAnalyzer
from ui.main_window import MainWindow
from ui.system_tray import SystemTray

# 設定日誌
log_dir = os.path.join(os.getenv('APPDATA', ''), 'ScreenGet')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'screenget.log'),
                          encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ScreenGetApp:
    """ScreenGet 主應用程式"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # 關閉視窗不退出

        # 初始化資料庫
        self.db = UsageDatabase()
        self.db.close_all_open_sessions()  # 清理上次異常退出的 sessions

        # 初始化分析器
        self.analyzer = UsageAnalyzer(self.db)

        # 初始化追蹤器
        self.tracker = UsageTracker(self.db)
        self.tracker.set_on_app_change(self._on_app_change)

        # 初始化閒置偵測器
        self.idle_detector = IdleDetector(
            idle_timeout_minutes=20,
            on_idle=self._on_idle,
            on_resume=self._on_resume
        )

        # 初始化 UI
        self._init_ui()

        # 設定每日資料清理
        self._setup_cleanup_timer()

        logger.info("ScreenGet initialized successfully")

    def _init_ui(self):
        """初始化 UI 元件"""
        # 取得圖示路徑
        icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'icon.png')
        if not os.path.exists(icon_path):
            icon_path = None

        # 主視窗
        self.main_window = MainWindow(self.analyzer)

        # 系統匣
        self.system_tray = SystemTray(icon_path)
        self.system_tray.show_window_signal.connect(self._show_dashboard)
        self.system_tray.quit_signal.connect(self._quit)
        self.system_tray.toggle_tracking_signal.connect(self._toggle_tracking)
        self.system_tray.show()

    def _setup_cleanup_timer(self):
        """每天清理一次過期資料"""
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._do_cleanup)
        self.cleanup_timer.start(3600 * 1000)  # 每小時檢查一次

    def _do_cleanup(self):
        """執行資料清理"""
        try:
            self.db.cleanup_old_data(30)
            logger.info("Old data cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def _on_app_change(self, app_name: str, title: str, app_type: str):
        """前景視窗切換回呼"""
        tooltip = f"ScreenGet - 當前: {app_name}"
        self.system_tray.update_tooltip(tooltip)

    def _on_idle(self, idle_start: datetime):
        """閒置回呼 - 暫停追蹤"""
        logger.info(f"Idle detected at {idle_start}")
        self.tracker.pause()
        self.main_window.update_tracking_status(True, is_idle=True)
        self.system_tray.update_tooltip("ScreenGet - 😴 閒置中")

    def _on_resume(self, resume_time: datetime):
        """從閒置恢復回呼"""
        logger.info(f"User resumed at {resume_time}")
        self.tracker.resume()
        self.main_window.update_tracking_status(True, is_idle=False)
        self.system_tray.update_tooltip("ScreenGet - ⚡ 追蹤中")

    def _show_dashboard(self):
        """顯示儀表板"""
        self.main_window.show_and_activate()

    def _toggle_tracking(self):
        """切換追蹤狀態"""
        if self.tracker.is_paused:
            self.tracker.resume()
            self.main_window.update_tracking_status(True)
            self.system_tray.show_message("ScreenGet", "已繼續追蹤")
        else:
            self.tracker.pause()
            self.main_window.update_tracking_status(False)
            self.system_tray.show_message("ScreenGet", "已暫停追蹤")

    def _quit(self):
        """退出應用程式"""
        logger.info("Shutting down ScreenGet...")
        self.tracker.stop()
        self.idle_detector.stop()
        self.system_tray.hide()
        self.main_window.set_force_quit()
        self.main_window.close()
        self.app.quit()

    def run(self):
        """啟動應用程式"""
        logger.info("Starting ScreenGet...")

        # 啟動追蹤
        self.tracker.start()
        self.idle_detector.start()

        # 顯示系統匣通知
        self.system_tray.show_message(
            "ScreenGet",
            "螢幕使用監控已啟動，正在追蹤使用狀況。",
        )

        return self.app.exec()


def main():
    try:
        screen_get = ScreenGetApp()
        sys.exit(screen_get.run())
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
