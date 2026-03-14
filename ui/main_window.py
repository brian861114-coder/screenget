"""
main_window.py - 主視窗
深色主題的現代化 UI，左側導航列，右側內容區域。
關閉視窗時最小化到系統匣。
"""

import logging
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon, QCloseEvent

from core.analyzer import UsageAnalyzer
from ui.dashboard_page import DashboardPage
from ui.analysis_page import AnalysisPage
from ui.browser_page import BrowserPage
from ui.detail_page import DetailListPage
from ui.settings_page import SettingsPage
from core.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

# 全域淺色主題樣式 (基於 #D7F5F2)
LIGHT_STYLESHEET = """
    QMainWindow {
        background-color: #D7F5F2;
    }
    QWidget {
        background-color: #D7F5F2;
        color: #000000;
        font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif;
    }
    QLabel {
        background-color: transparent;
        color: #000000;
    }
    QScrollArea {
        background-color: transparent;
        border: none;
    }
"""


class NavButton(QPushButton):
    """導航按鈕"""

    def __init__(self, text: str, icon_text: str = "", parent=None):
        super().__init__(f" {icon_text}  {text}" if icon_text else text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(44)
        self.setMinimumWidth(180)
        self._update_style(False)

    def _update_style(self, checked: bool):
        if checked:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #B2E2F2;
                    color: #000000;
                    border: none;
                    border-left: 4px solid #000000;
                    border-radius: 0px;
                    text-align: left;
                    padding: 10px 16px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #445566;
                    border: none;
                    border-left: 4px solid transparent;
                    border-radius: 0px;
                    text-align: left;
                    padding: 10px 16px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 0, 0, 0.05);
                    color: #000000;
                }
            """)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._update_style(checked)


class MainWindow(QMainWindow):
    """主視窗"""

    def __init__(self, analyzer: UsageAnalyzer, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer
        self.settings_manager = settings
        self._minimize_to_tray = True  # 關閉時最小化到系統匣
        self._force_quit = False

        self.setWindowTitle("ScreenGet - 螢幕使用監控")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        self.setStyleSheet(LIGHT_STYLESHEET)

        # 設定視窗圖示
        # 取得專案根目錄 (ui/main_window.py -> ui -> root)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, 'resources', 'icon.png')
        
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
            # 同時確保全域圖示也設定了
            QApplication.setWindowIcon(app_icon)
        else:
            logger.warning(f"找不到圖示檔: {icon_path}")

        self._init_ui()
        self._setup_timer()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ─── 左側導航列 ───
        nav_panel = QFrame()
        nav_panel.setFixedWidth(200)
        nav_panel.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-right: 1px solid #B9FBC0;
            }
        """)
        nav_layout = QVBoxLayout(nav_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        # Logo / 品牌
        brand = QLabel("🖥️ ScreenGet")
        brand.setStyleSheet("""
            color: #000000;
            font-size: 18px;
            font-weight: bold;
            padding: 20px 16px;
            background-color: transparent;
        """)
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(brand)

        # 分隔線
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #B9FBC0; max-height: 1px;")
        nav_layout.addWidget(separator)

        nav_layout.addSpacing(10)

        # 導航按鈕
        self.btn_dashboard = NavButton("使用總覽", "📊")
        self.btn_browser = NavButton("瀏覽器分析", "🌐")
        self.btn_analysis = NavButton("軟體分析", "🔍")
        self.btn_settings = NavButton("設定", "⚙️")

        self.btn_dashboard.setChecked(True)
        self.btn_dashboard.clicked.connect(lambda: self._switch_page(0))
        self.btn_browser.clicked.connect(lambda: self._switch_page(1))
        self.btn_analysis.clicked.connect(lambda: self._switch_page(2))
        self.btn_settings.clicked.connect(lambda: self._switch_page(3))

        nav_layout.addWidget(self.btn_dashboard)
        nav_layout.addWidget(self.btn_browser)
        nav_layout.addWidget(self.btn_analysis)
        nav_layout.addWidget(self.btn_settings)
        nav_layout.addStretch()

        # 狀態資訊
        self.status_label = QLabel("⚡ 追蹤中")
        self.status_label.setStyleSheet("""
            color: #2D5A27;
            font-size: 12px;
            padding: 12px 16px;
            background-color: transparent;
            font-weight: bold;
        """)
        nav_layout.addWidget(self.status_label)

        main_layout.addWidget(nav_panel)

        # ─── 右側內容區域 ───
        self.stack = QStackedWidget()

        self.dashboard_page = DashboardPage(self.analyzer)
        self.browser_page = BrowserPage(self.analyzer)
        self.analysis_page = AnalysisPage(self.analyzer)
        self.settings_page = SettingsPage(self.settings_manager)

        # 連接 dashboard 的 app 點擊事件
        self.dashboard_page.app_clicked.connect(self._go_to_analysis)
        self.browser_page.website_clicked.connect(self._go_to_analysis)
        self.settings_page.settings_changed.connect(self._on_settings_changed)

        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.browser_page)
        self.stack.addWidget(self.analysis_page)
        self.stack.addWidget(self.settings_page) # index 3
        
        # ─── 詳細清單頁面 (不直接顯示在導航列) ───
        self.app_detail_page = DetailListPage(self.analyzer, "所有程式使用排行", app_type='app')
        self.browser_detail_page = DetailListPage(self.analyzer, "網站造訪總排行", app_type='browser')
        
        self.stack.addWidget(self.app_detail_page) # index 4
        self.stack.addWidget(self.browser_detail_page) # index 5
        
        # 連接詳細頁面信號
        self.dashboard_page.detail_requested.connect(lambda: self._show_detail('app'))
        self.browser_page.detail_requested.connect(lambda: self._show_detail('browser'))
        
        self.app_detail_page.back_clicked.connect(lambda: self._switch_page(0))
        self.browser_detail_page.back_clicked.connect(lambda: self._switch_page(1))

        main_layout.addWidget(self.stack)

    def _setup_timer(self):
        """設定自動重新整理定時器（每 30 秒更新一次）"""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._auto_refresh)
        self.refresh_timer.start(30000)  # 30 秒

    def _auto_refresh(self):
        """定時重新整理當前頁面"""
        if self.isVisible():
            current_page = self.stack.currentWidget()
            if hasattr(current_page, 'refresh_data'):
                current_page.refresh_data()

    def _switch_page(self, index: int):
        """切換頁面"""
        self.stack.setCurrentIndex(index)
        self.btn_dashboard.setChecked(index == 0)
        self.btn_dashboard._update_style(index == 0)
        self.btn_browser.setChecked(index == 1)
        self.btn_browser._update_style(index == 1)
        self.btn_analysis.setChecked(index == 2)
        self.btn_analysis._update_style(index == 2)
        self.btn_settings.setChecked(index == 3)
        self.btn_settings._update_style(index == 3)

        # 切換時重新載入資料
        page = self.stack.widget(index)
        if hasattr(page, 'refresh_data'):
            page.refresh_data()

    def _show_detail(self, category: str):
        """顯示詳細清單頁面"""
        if category == 'app':
            self.app_detail_page.set_period(self.dashboard_page.current_period)
            self.stack.setCurrentIndex(4)
        else:
            self.browser_detail_page.set_period(self.browser_page.current_period)
            self.stack.setCurrentIndex(5)

    def _on_settings_changed(self):
        """當設定（如白名單）變更時，重新整理目前頁面"""
        current = self.stack.currentWidget()
        if hasattr(current, 'refresh_data'):
            current.refresh_data()
        
        # 切換時取消導航列的所有選取狀態 (或維持原本的)
        # 這裡我們維持原本的導航選中，只是內容區換了

    def _go_to_analysis(self, app_name: str):
        """跳轉到分析頁面查看特定軟體"""
        self._switch_page(2)
        self.analysis_page.set_app(app_name)

    def update_tracking_status(self, is_tracking: bool, is_idle: bool = False):
        """更新追蹤狀態顯示"""
        if is_idle:
            self.status_label.setText("😴 閒置中")
            self.status_label.setStyleSheet("""
                color: #ffd93d;
                font-size: 12px;
                padding: 12px 16px;
                background-color: transparent;
            """)
        elif is_tracking:
            self.status_label.setText("⚡ 追蹤中")
            self.status_label.setStyleSheet("""
                color: #2D5A27;
                font-size: 12px;
                padding: 12px 16px;
                background-color: transparent;
                font-weight: bold;
            """)
        else:
            self.status_label.setText("⏸ 已暫停")
            self.status_label.setStyleSheet("""
                color: #B22222;
                font-size: 12px;
                padding: 12px 16px;
                background-color: transparent;
                font-weight: bold;
            """)

    def show_and_activate(self):
        """顯示並啟用視窗"""
        self.show()
        self.activateWindow()
        self.raise_()
        # 重新整理資料
        current = self.stack.currentWidget()
        if hasattr(current, 'refresh_data'):
            current.refresh_data()

    def set_force_quit(self):
        """設定為真正退出（不最小化到系統匣）"""
        self._force_quit = True

    def closeEvent(self, event: QCloseEvent):
        """關閉視窗時最小化到系統匣"""
        if self._minimize_to_tray and not self._force_quit:
            event.ignore()
            self.hide()
        else:
            event.accept()
