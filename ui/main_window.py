"""
main_window.py - 主視窗（導航層級、麵包屑）
"""

import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCloseEvent, QFont

from core.analyzer import UsageAnalyzer
from core.settings_manager import SettingsManager
from core.i18n import t, set_language
from ui.dashboard_page import DashboardPage
from ui.analysis_page import AnalysisPage
from ui.browser_page import BrowserPage
from ui.website_page import WebsitePage
from ui.detail_page import DetailListPage
from ui.settings_page import SettingsPage
from ui.widgets import BreadcrumbBar
from ui.theme import (
    BG, SURFACE, BORDER, TEXT, TEXT_MUTED, ACCENT_GREEN_DARK,
    set_font_preset, build_main_stylesheet, get_font_pt, sp,
)

logger = logging.getLogger(__name__)

# stack indices
IDX_DASH = 0
IDX_BROWSER = 1
IDX_ANALYSIS = 2
IDX_SETTINGS = 3
IDX_APP_DETAIL = 4
IDX_BROWSER_DETAIL = 5
IDX_WEBSITE = 6


class NavButton(QPushButton):
    def __init__(self, text: str, icon_text: str = "", parent=None):
        super().__init__(parent)
        self._label = text
        self._icon = icon_text
        self._refresh_text()
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(44)
        self.setMinimumWidth(180)
        self._update_style(False)

    def _refresh_text(self):
        self.setText(f" {self._icon}  {self._label}" if self._icon else self._label)

    def set_label(self, text: str):
        self._label = text
        self._refresh_text()

    def _update_style(self, checked: bool):
        size = sp(14)
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #B2E2F2; color: #000000; border: none;
                    border-left: 4px solid #000000; border-radius: 0px;
                    text-align: left; padding: 10px 16px; font-size: {size}px; font-weight: bold;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; color: #445566; border: none;
                    border-left: 4px solid transparent; border-radius: 0px;
                    text-align: left; padding: 10px 16px; font-size: {size}px;
                }}
                QPushButton:hover {{ background-color: rgba(0, 0, 0, 0.05); color: #000000; }}
            """)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._update_style(checked)

class MainWindow(QMainWindow):
    def __init__(self, analyzer: UsageAnalyzer, settings: SettingsManager,
                 health_context: dict = None, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer
        self.settings_manager = settings
        self.health_context = health_context or {}
        self._minimize_to_tray = True
        self._force_quit = False
        self._status_mode = "tracking"
        self._nav_parent = IDX_DASH  # 詳情頁時側欄維持的父層

        set_language(settings.get_language())
        set_font_preset(settings.get_font_size())
        self.setWindowTitle(t("app_title"))
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        self.apply_font_size(refresh_pages=False)

        self._init_ui()
        self._setup_timer()
        self.apply_font_size()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ─── 左側導航 ───
        nav_panel = QFrame()
        nav_panel.setFixedWidth(200)
        nav_panel.setStyleSheet(f"""
            QFrame {{ background-color: {SURFACE}; border-right: 1px solid {BORDER}; }}
        """)
        nav_layout = QVBoxLayout(nav_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        self.brand = QLabel("ScreenGet")
        self.brand.setStyleSheet(f"""
            color: {TEXT}; font-size: {sp(18)}px; font-weight: bold;
            padding: 20px 16px; background-color: transparent;
        """)
        self.brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self.brand)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {BORDER}; max-height: 1px;")
        nav_layout.addWidget(separator)
        nav_layout.addSpacing(10)

        self.btn_dashboard = NavButton(t("nav_dashboard"))
        self.btn_browser = NavButton(t("nav_browser"))
        self.btn_analysis = NavButton(t("nav_analysis"))
        self.btn_settings = NavButton(t("nav_settings"))
        self.btn_dashboard.setChecked(True)

        self.btn_dashboard.clicked.connect(lambda: self._switch_page(IDX_DASH))
        self.btn_browser.clicked.connect(lambda: self._switch_page(IDX_BROWSER))
        self.btn_analysis.clicked.connect(lambda: self._switch_page(IDX_ANALYSIS))
        self.btn_settings.clicked.connect(lambda: self._switch_page(IDX_SETTINGS))

        for b in (self.btn_dashboard, self.btn_browser, self.btn_analysis, self.btn_settings):
            nav_layout.addWidget(b)
        nav_layout.addStretch()

        self.status_label = QLabel(t("status_tracking"))
        self.status_label.setStyleSheet(f"""
            color: {ACCENT_GREEN_DARK}; font-size: 12px; padding: 12px 16px;
            background-color: transparent; font-weight: bold;
        """)
        nav_layout.addWidget(self.status_label)
        main_layout.addWidget(nav_panel)

        # ─── 右側：麵包屑 + 內容 ───
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        crumb_wrap = QWidget()
        crumb_wrap.setStyleSheet(f"background: {BG};")
        crumb_layout = QVBoxLayout(crumb_wrap)
        crumb_layout.setContentsMargins(24, 12, 24, 0)
        self.breadcrumb = BreadcrumbBar()
        self.breadcrumb.crumb_clicked.connect(self._on_crumb_clicked)
        crumb_layout.addWidget(self.breadcrumb)
        right_layout.addWidget(crumb_wrap)

        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack, 1)
        main_layout.addWidget(right)

        self.dashboard_page = DashboardPage(self.analyzer)
        self.browser_page = BrowserPage(self.analyzer)
        self.analysis_page = AnalysisPage(self.analyzer)
        self.settings_page = SettingsPage(
            self.settings_manager, self.analyzer, health_context=self.health_context
        )
        self.app_detail_page = DetailListPage(self.analyzer, "detail_apps", app_type=None)
        self.browser_detail_page = DetailListPage(self.analyzer, "detail_sites", app_type="browser")
        self.website_page = WebsitePage(self.analyzer)

        for page in (
            self.dashboard_page, self.browser_page, self.analysis_page,
            self.settings_page, self.app_detail_page, self.browser_detail_page,
            self.website_page,
        ):
            self.stack.addWidget(page)

        # 信號連接
        self.dashboard_page.app_clicked.connect(self._go_to_analysis)
        self.dashboard_page.detail_requested.connect(lambda: self._show_detail("app"))
        self.dashboard_page.open_settings.connect(lambda: self._switch_page(IDX_SETTINGS))
        self.dashboard_page.unit_changed.connect(self._on_unit_changed)

        self.browser_page.website_clicked.connect(self._go_to_website)
        self.browser_page.detail_requested.connect(lambda: self._show_detail("browser"))
        self.browser_page.open_settings.connect(lambda: self._switch_page(IDX_SETTINGS))
        self.browser_page.unit_changed.connect(self._on_unit_changed)

        self.analysis_page.unit_changed.connect(self._on_unit_changed)
        self.website_page.unit_changed.connect(self._on_unit_changed)

        self.app_detail_page.back_clicked.connect(lambda: self._switch_page(IDX_DASH))
        self.app_detail_page.item_clicked.connect(self._go_to_analysis)
        self.app_detail_page.unit_changed.connect(self._on_unit_changed)
        self.browser_detail_page.back_clicked.connect(lambda: self._switch_page(IDX_BROWSER))
        self.browser_detail_page.item_clicked.connect(self._go_to_website)
        self.browser_detail_page.unit_changed.connect(self._on_unit_changed)
        self.website_page.back_clicked.connect(lambda: self._switch_page(IDX_BROWSER))

        self.settings_page.settings_changed.connect(self._on_settings_changed)
        self.settings_page.language_changed.connect(self.apply_language)

        self._update_breadcrumb(IDX_DASH)

    def apply_language(self, lang: str = None):
        if lang:
            set_language(lang)
        else:
            set_language(self.settings_manager.get_language())

        self.setWindowTitle(t("app_title"))
        self.btn_dashboard.set_label(t("nav_dashboard"))
        self.btn_browser.set_label(t("nav_browser"))
        self.btn_analysis.set_label(t("nav_analysis"))
        self.btn_settings.set_label(t("nav_settings"))
        self._refresh_status_text()

        for page in (
            self.dashboard_page, self.browser_page, self.analysis_page,
            self.settings_page, self.app_detail_page, self.browser_detail_page,
            self.website_page,
        ):
            if hasattr(page, "apply_language"):
                page.apply_language()
        self._update_breadcrumb(self.stack.currentIndex())

    def _setup_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._auto_refresh)
        self.refresh_timer.start(30000)

    def _auto_refresh(self):
        if self.isVisible():
            current_page = self.stack.currentWidget()
            if hasattr(current_page, "refresh_data"):
                current_page.refresh_data()

    def _set_nav_highlight(self, index: int):
        """側欄高亮：詳情頁維持父層選中"""
        highlight = index
        if index == IDX_APP_DETAIL:
            highlight = IDX_DASH
        elif index in (IDX_BROWSER_DETAIL, IDX_WEBSITE):
            highlight = IDX_BROWSER

        self.btn_dashboard.setChecked(highlight == IDX_DASH)
        self.btn_browser.setChecked(highlight == IDX_BROWSER)
        self.btn_analysis.setChecked(highlight == IDX_ANALYSIS)
        self.btn_settings.setChecked(highlight == IDX_SETTINGS)

    def _update_breadcrumb(self, index: int):
        if index == IDX_APP_DETAIL:
            self.breadcrumb.set_crumbs([t("crumb_overview"), t("crumb_detail")])
        elif index == IDX_BROWSER_DETAIL:
            self.breadcrumb.set_crumbs([t("crumb_browser"), t("crumb_site_list")])
        elif index == IDX_WEBSITE and self.website_page.current_site:
            crumbs = [t("crumb_browser"), t("crumb_site_list"), self.website_page.current_site]
            self.breadcrumb.set_crumbs(crumbs)
        elif index == IDX_ANALYSIS and self.analysis_page.current_app:
            # 軟體分析路徑（不再把網站導向此頁）
            parent = t("crumb_overview") if self._nav_parent == IDX_DASH else t("crumb_analysis")
            self.breadcrumb.set_crumbs([
                parent, t("crumb_analysis"), self.analysis_page.current_app
            ])
        else:
            self.breadcrumb.set_crumbs([])

    def _on_crumb_clicked(self, crumb_index: int):
        idx = self.stack.currentIndex()
        if idx == IDX_APP_DETAIL and crumb_index == 0:
            self._switch_page(IDX_DASH)
        elif idx == IDX_BROWSER_DETAIL and crumb_index == 0:
            self._switch_page(IDX_BROWSER)
        elif idx == IDX_WEBSITE:
            if crumb_index == 0:
                self._switch_page(IDX_BROWSER)
            elif crumb_index == 1:
                self._show_detail("browser")
        elif idx == IDX_ANALYSIS:
            if crumb_index == 0:
                self._switch_page(
                    self._nav_parent if self._nav_parent in (IDX_DASH, IDX_ANALYSIS) else IDX_DASH
                )
            elif crumb_index == 1:
                pass

    def _switch_page(self, index: int):
        if index <= IDX_SETTINGS:
            self._nav_parent = index
        self.stack.setCurrentIndex(index)
        self._set_nav_highlight(index)
        self._update_breadcrumb(index)
        page = self.stack.widget(index)
        if hasattr(page, "refresh_data"):
            page.refresh_data()

    def _show_detail(self, category: str):
        if category == "app":
            self._nav_parent = IDX_DASH
            self.app_detail_page.set_range_from_bar(self.dashboard_page.period_bar)
            self.stack.setCurrentIndex(IDX_APP_DETAIL)
            self._set_nav_highlight(IDX_APP_DETAIL)
            self._update_breadcrumb(IDX_APP_DETAIL)
        else:
            self._nav_parent = IDX_BROWSER
            # 從網站詳情回到排行時沿用網站頁區間，否則用瀏覽器總覽
            source = self.website_page.period_bar if self.stack.currentIndex() == IDX_WEBSITE else self.browser_page.period_bar
            self.browser_detail_page.set_range_from_bar(source)
            self.stack.setCurrentIndex(IDX_BROWSER_DETAIL)
            self._set_nav_highlight(IDX_BROWSER_DETAIL)
            self._update_breadcrumb(IDX_BROWSER_DETAIL)

    def _on_settings_changed(self):
        self.apply_font_size(refresh_data=True)
        self._sync_all_units()

    def apply_font_size(self, refresh_pages: bool = True, refresh_data: bool = False):
        """依設定套用全域字級。預設只重套樣式；必要時只刷新目前可見頁資料。"""
        preset = self.settings_manager.get_font_size()
        set_font_preset(preset)

        app = QApplication.instance()
        if app is not None:
            font = QFont("Microsoft JhengHei UI", get_font_pt())
            app.setFont(font)

        self.setStyleSheet(build_main_stylesheet())

        if hasattr(self, "brand"):
            self.brand.setStyleSheet(f"""
                color: {TEXT}; font-size: {sp(18)}px; font-weight: bold;
                padding: 20px 16px; background-color: transparent;
            """)
        for btn in (
            getattr(self, "btn_dashboard", None),
            getattr(self, "btn_browser", None),
            getattr(self, "btn_analysis", None),
            getattr(self, "btn_settings", None),
        ):
            if btn is not None:
                btn._update_style(btn.isChecked())

        self._refresh_status_style()

        if refresh_pages and hasattr(self, "stack"):
            from ui.theme import (
                title_style, subtitle_style, HINT_STYLE, INPUT_STYLE,
                PRIMARY_BTN, SECTION_LABEL_STYLE,
            )
            for page in (
                self.dashboard_page, self.browser_page, self.analysis_page,
                self.settings_page, self.app_detail_page, self.browser_detail_page,
                self.website_page,
            ):
                self._restyle_page(
                    page, title_style, subtitle_style, HINT_STYLE,
                    INPUT_STYLE, PRIMARY_BTN, SECTION_LABEL_STYLE,
                )

            # 只刷新目前可見頁，避免啟動／設定變更時 matplotlib 風暴
            if refresh_data:
                current = self.stack.currentWidget()
                if hasattr(current, "refresh_data"):
                    current.refresh_data()

    def _restyle_page(self, page, title_style, subtitle_style, HINT_STYLE,
                      INPUT_STYLE, PRIMARY_BTN, SECTION_LABEL_STYLE):
        if hasattr(page, "title"):
            page.title.setStyleSheet(title_style())
        if hasattr(page, "title_label"):
            page.title_label.setStyleSheet(
                f"color: {TEXT}; font-size: {sp(20)}px; font-weight: bold; margin-left: 10px;"
            )
        if hasattr(page, "select_label"):
            page.select_label.setStyleSheet(subtitle_style())
        if hasattr(page, "layer_hint"):
            page.layer_hint.setStyleSheet(HINT_STYLE)
        if hasattr(page, "cred_legend"):
            page.cred_legend.setStyleSheet(HINT_STYLE)
        if hasattr(page, "hint"):
            page.hint.setStyleSheet(HINT_STYLE)
        if hasattr(page, "btn_back"):
            page.btn_back.setStyleSheet(PRIMARY_BTN)
        for attr in ("app_combo", "site_combo", "timeline_filter"):
            w = getattr(page, attr, None)
            if w is not None:
                w.setStyleSheet(INPUT_STYLE)
        for attr in dir(page):
            if not attr.startswith("sec_"):
                continue
            sec = getattr(page, attr, None)
            if sec is not None and hasattr(sec, "title_label"):
                sec.title_label.setStyleSheet(SECTION_LABEL_STYLE)
                if hasattr(sec, "hint_label"):
                    sec.hint_label.setStyleSheet(HINT_STYLE)
        if hasattr(page, "unit_switcher"):
            page.unit_switcher.apply_language()
        if hasattr(page, "period_bar"):
            # 只更新按鈕樣式，避免觸發 changed→refresh
            for b in page.period_bar.period_group.buttons():
                b._update_style(b.isChecked())

    def _refresh_status_style(self):
        if not hasattr(self, "status_label"):
            return
        size = sp(12)
        if self._status_mode == "idle":
            self.status_label.setStyleSheet(
                f"color: #C48A2A; font-size: {size}px; padding: 12px 16px; background-color: transparent;"
            )
        elif self._status_mode == "tracking":
            self.status_label.setStyleSheet(f"""
                color: {ACCENT_GREEN_DARK}; font-size: {size}px; padding: 12px 16px;
                background-color: transparent; font-weight: bold;
            """)
        else:
            self.status_label.setStyleSheet(
                f"color: #B22222; font-size: {size}px; padding: 12px 16px; "
                f"background-color: transparent; font-weight: bold;"
            )

    def _on_unit_changed(self, _unit: str = None):
        """任一頁切換單位後，同步其他頁的切換器狀態。"""
        self._sync_all_units(skip=self.stack.currentWidget())

    def _sync_all_units(self, skip=None):
        for page in (
            self.dashboard_page, self.browser_page, self.analysis_page,
            self.app_detail_page, self.browser_detail_page, self.website_page,
        ):
            if page is skip:
                continue
            if hasattr(page, "sync_unit"):
                page.sync_unit()

    def _go_to_analysis(self, app_name: str):
        current = self.stack.currentIndex()
        if current in (IDX_DASH, IDX_APP_DETAIL):
            self._nav_parent = IDX_DASH
        else:
            self._nav_parent = IDX_ANALYSIS
        self.stack.setCurrentIndex(IDX_ANALYSIS)
        self._set_nav_highlight(IDX_ANALYSIS)
        self.analysis_page.set_app(app_name)
        self._update_breadcrumb(IDX_ANALYSIS)

    def _go_to_website(self, site: str):
        """瀏覽器分層第三層：單一網站"""
        current = self.stack.currentIndex()
        self._nav_parent = IDX_BROWSER
        if current == IDX_BROWSER:
            self.website_page.set_range_from_bar(self.browser_page.period_bar)
        elif current == IDX_BROWSER_DETAIL:
            self.website_page.set_range_from_bar(self.browser_detail_page.period_bar)
        self.stack.setCurrentIndex(IDX_WEBSITE)
        self._set_nav_highlight(IDX_WEBSITE)
        self.website_page.set_site(site)
        self._update_breadcrumb(IDX_WEBSITE)

    def _refresh_status_text(self):
        if self._status_mode == "idle":
            self.status_label.setText(t("status_idle"))
        elif self._status_mode == "paused":
            self.status_label.setText(t("status_paused"))
        else:
            self.status_label.setText(t("status_tracking"))

    def update_tracking_status(self, is_tracking: bool, is_idle: bool = False):
        if is_idle:
            self._status_mode = "idle"
        elif is_tracking:
            self._status_mode = "tracking"
        else:
            self._status_mode = "paused"
        self._refresh_status_style()
        self._refresh_status_text()

    def show_and_activate(self):
        self.show()
        self.activateWindow()
        self.raise_()
        current = self.stack.currentWidget()
        if hasattr(current, "refresh_data"):
            current.refresh_data()

    def set_force_quit(self):
        self._force_quit = True

    def closeEvent(self, event: QCloseEvent):
        if self._minimize_to_tray and not self._force_quit:
            event.ignore()
            self.hide()
        else:
            event.accept()
