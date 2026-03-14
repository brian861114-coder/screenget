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
from PyQt6.QtGui import QIcon

def resource_path(relative_path):
    """取得資源的絕對路徑，相容於 PyInstaller 封裝後的路徑"""
    try:
        # PyInstaller 建立一個臨時資料夾並將路徑存放在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# 在 Windows 上設定 AppUserModelID — 必須在 QApplication 建立「之前」呼叫才能生效
def set_app_user_model_id():
    if sys.platform == 'win32':
        import ctypes
        try:
            myappid = u'brian861114.screenget.app.v1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print(f"Failed to set AppUserModelID: {e}")

# 盡早呼叫，確保在 QApplication 建立前就設定好
set_app_user_model_id()

from core.database import UsageDatabase
from core.settings_manager import SettingsManager
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

        # 設定全域圖示：優先使用 .ico（Windows 工作列必須用 .ico 才能正確顯示）
        ico_path = resource_path(os.path.join('resources', 'icon.ico'))
        png_path = resource_path(os.path.join('resources', 'icon.png'))
        self.icon_path = ico_path if os.path.exists(ico_path) else png_path

        if os.path.exists(self.icon_path):
            app_icon = QIcon(self.icon_path)
            self.app.setWindowIcon(app_icon)
            self.main_icon = app_icon
            logger.info(f"Icon loaded: {self.icon_path}")
        else:
            logger.warning(f"Icon not found: {self.icon_path}")
            self.main_icon = None

        # 初始化資料庫
        self.db = UsageDatabase()
        self.db.close_all_open_sessions()

        # 初始化設定管理器
        self.settings_manager = SettingsManager()

        # 初始化分析器
        self.analyzer = UsageAnalyzer(self.db, self.settings_manager)

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
        # 主視窗
        self.main_window = MainWindow(self.analyzer, self.settings_manager)
        if self.main_icon:
            self.main_window.setWindowIcon(self.main_icon)

        # 系統匣
        self.system_tray = SystemTray(self.icon_path)
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
