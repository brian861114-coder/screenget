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
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def set_app_user_model_id():
    if sys.platform == 'win32':
        import ctypes
        try:
            myappid = u'brian861114.screenget.app.v1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print(f"Failed to set AppUserModelID: {e}")

set_app_user_model_id()

from core.database import UsageDatabase
from core.settings_manager import SettingsManager
from core.tracker import UsageTracker
from core.idle_detector import IdleDetector
from core.analyzer import UsageAnalyzer
from core.browser_bridge import register_native_host, BrowserBridgeWatcher
from core.i18n import set_language
from ui.main_window import MainWindow
from ui.system_tray import SystemTray

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
        self.app.setQuitOnLastWindowClosed(False)

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

        self.db = UsageDatabase()
        self.db.close_all_open_sessions()
        try:
            repaired = self.db.repair_inflated_sessions(max_hours=8.0)
            if repaired:
                logger.info(f"Repaired {repaired} inflated historical session(s)")
        except Exception as e:
            logger.error(f"Failed to repair inflated sessions: {e}")

        self.settings_manager = SettingsManager()
        set_language(self.settings_manager.get_language())
        from ui.theme import set_font_preset, get_font_pt
        from PyQt6.QtGui import QFont
        set_font_preset(self.settings_manager.get_font_size())
        self.app.setFont(QFont("Microsoft JhengHei UI", get_font_pt()))
        self.analyzer = UsageAnalyzer(self.db, self.settings_manager)

        self.tracker = UsageTracker(self.db)
        self.tracker.set_on_app_change(self._on_app_change)

        idle_minutes = self.settings_manager.get_idle_timeout_minutes()
        self.idle_detector = IdleDetector(
            idle_timeout_minutes=idle_minutes,
            on_idle=self._on_idle,
            on_resume=self._on_resume
        )

        # 註冊瀏覽器 Native Messaging Host
        try:
            register_native_host(self.settings_manager.get_extension_id())
        except Exception as e:
            logger.error(f"Native host registration failed: {e}")

        self.bridge_watcher = BrowserBridgeWatcher(self._on_bridge_page)

        self.health_context = {
            "is_tracking": lambda: self.tracker.is_running and not self.tracker.is_paused,
            "is_idle": lambda: self.idle_detector.is_idle,
            "is_paused": lambda: self.tracker.is_paused and not self.idle_detector.is_idle,
        }

        self._init_ui()
        self._setup_cleanup_timer()

        logger.info("ScreenGet initialized successfully")

    def _init_ui(self):
        self.main_window = MainWindow(
            self.analyzer, self.settings_manager, health_context=self.health_context
        )
        if self.main_icon:
            self.main_window.setWindowIcon(self.main_icon)

        # 設定變更時同步閒置門檻
        self.main_window.settings_page.settings_changed.connect(self._on_settings_changed)

        self.system_tray = SystemTray(self.icon_path)
        self.system_tray.show_window_signal.connect(self._show_dashboard)
        self.system_tray.quit_signal.connect(self._quit)
        self.system_tray.toggle_tracking_signal.connect(self._toggle_tracking)
        self.system_tray.show()

    def _setup_cleanup_timer(self):
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._do_cleanup)
        self.cleanup_timer.start(3600 * 1000)

    def _do_cleanup(self):
        try:
            self.db.cleanup_old_data(30)
            logger.info("Old data cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def _on_settings_changed(self):
        minutes = self.settings_manager.get_idle_timeout_minutes()
        self.idle_detector.set_timeout_minutes(minutes)
        logger.info(f"Settings applied: idle={minutes}m")

    def _on_bridge_page(self, event_type: str, url: str, title: str):
        """處理瀏覽器擴充套件事件"""
        if event_type == "ping":
            return
        if event_type == "page_end":
            return
        if event_type == "page_start" and url:
            applied = self.tracker.apply_browser_page(url, title)
            if applied:
                logger.debug(f"Bridge applied: {url[:80]}")

    def _on_app_change(self, app_name: str, title: str, app_type: str):
        # 可能在追蹤執行緒呼叫 → 佇列到 GUI 執行緒
        QTimer.singleShot(
            0,
            lambda name=app_name: self.system_tray.update_tooltip(f"ScreenGet - 當前: {name}"),
        )

    def _on_idle(self, idle_start: datetime):
        logger.info(f"Idle detected; last activity at {idle_start}")
        self.tracker.pause(end_time=idle_start)
        QTimer.singleShot(0, lambda: self._apply_status_ui(is_idle=True, paused=True))

    def _on_resume(self, resume_time: datetime):
        logger.info(f"User resumed at {resume_time}")
        self.tracker.resume()
        QTimer.singleShot(0, lambda: self._apply_status_ui(is_idle=False, paused=False))

    def _apply_status_ui(self, is_idle: bool, paused: bool):
        if is_idle:
            self.main_window.update_tracking_status(True, is_idle=True)
            self.system_tray.update_tooltip("ScreenGet - 閒置中")
            self.system_tray.set_paused(True, is_idle=True)
        elif paused:
            self.main_window.update_tracking_status(False)
            self.system_tray.update_tooltip("ScreenGet - 已暫停")
            self.system_tray.set_paused(True)
        else:
            self.main_window.update_tracking_status(True, is_idle=False)
            self.system_tray.update_tooltip("ScreenGet - 追蹤中")
            self.system_tray.set_paused(False)

    def _show_dashboard(self):
        self.main_window.show_and_activate()

    def _toggle_tracking(self):
        if self.tracker.is_paused:
            self.tracker.resume()
            self._apply_status_ui(is_idle=False, paused=False)
            self.system_tray.show_message("ScreenGet", "已繼續追蹤")
        else:
            self.tracker.pause()
            self._apply_status_ui(is_idle=False, paused=True)
            self.system_tray.show_message("ScreenGet", "已暫停追蹤")

    def _quit(self):
        logger.info("Shutting down ScreenGet...")
        self.bridge_watcher.stop()
        self.tracker.stop()
        self.idle_detector.stop()
        self.system_tray.hide()
        try:
            self.db.close()
        except Exception:
            pass
        self.main_window.set_force_quit()
        self.main_window.close()
        self.app.quit()

    def run(self):
        logger.info("Starting ScreenGet...")

        self.tracker.start()
        self.idle_detector.start()
        self.bridge_watcher.start(parent=self.app)

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
