"""
system_tray.py - 系統匣模組
常駐系統匣，提供右鍵選單和雙擊開啟主視窗。
"""

import logging
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSignal, QObject

logger = logging.getLogger(__name__)


class SystemTray(QObject):
    """系統匣管理器"""

    show_window_signal = pyqtSignal()
    quit_signal = pyqtSignal()
    toggle_tracking_signal = pyqtSignal()

    def __init__(self, icon_path: str = None, parent=None):
        super().__init__(parent)

        self.app = QApplication.instance()
        self.tray_icon = QSystemTrayIcon(parent)

        # 設定圖示
        if icon_path:
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # 使用預設的應用圖示
            self.tray_icon.setIcon(self.app.style().standardIcon(
                self.app.style().StandardPixmap.SP_ComputerIcon
            ))

        self.tray_icon.setToolTip("ScreenGet - 螢幕使用監控")

        # 建立右鍵選單
        self._create_menu()

        # 雙擊開啟主視窗
        self.tray_icon.activated.connect(self._on_activated)

        self._is_tracking = True

    def _create_menu(self):
        """建立系統匣右鍵選單"""
        menu = QMenu()

        # 開啟儀表板
        self.action_show = QAction("📊 開啟儀表板", self)
        self.action_show.triggered.connect(self.show_window_signal.emit)
        menu.addAction(self.action_show)

        menu.addSeparator()

        # 暫停/繼續追蹤
        self.action_toggle = QAction("⏸ 暫停追蹤", self)
        self.action_toggle.triggered.connect(self._toggle_tracking)
        menu.addAction(self.action_toggle)

        menu.addSeparator()

        # 退出
        action_quit = QAction("❌ 退出", self)
        action_quit.triggered.connect(self.quit_signal.emit)
        menu.addAction(action_quit)

        self.tray_icon.setContextMenu(menu)

    def _on_activated(self, reason):
        """系統匣圖示被點擊"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window_signal.emit()

    def _toggle_tracking(self):
        """切換追蹤狀態"""
        self._is_tracking = not self._is_tracking
        if self._is_tracking:
            self.action_toggle.setText("⏸ 暫停追蹤")
        else:
            self.action_toggle.setText("▶ 繼續追蹤")
        self.toggle_tracking_signal.emit()

    def show(self):
        """顯示系統匣圖示"""
        self.tray_icon.show()

    def hide(self):
        """隱藏系統匣圖示"""
        self.tray_icon.hide()

    def show_message(self, title: str, message: str,
                     icon=QSystemTrayIcon.MessageIcon.Information,
                     duration: int = 3000):
        """顯示系統匣通知"""
        self.tray_icon.showMessage(title, message, icon, duration)

    def update_tooltip(self, text: str):
        """更新 tooltip"""
        self.tray_icon.setToolTip(text)
