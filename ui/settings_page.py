"""
settings_page.py - 設定介面（分頁資訊架構）
"""

from datetime import datetime, timedelta, date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QListWidget, QPushButton, QLineEdit, QFrame,
    QMessageBox, QFileDialog, QDateEdit, QTextEdit, QTabWidget, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate

from core.settings_manager import SettingsManager
from core.analyzer import UsageAnalyzer
from core.exporter import UsageExporter
from core.browser_bridge import BrowserBridgeWatcher, register_native_host
from core.health_check import run_health_check, repair_health_issues, issues_to_text
from core.i18n import t, set_language
from ui.theme import (
    PRIMARY_BTN, SECONDARY_BTN, DANGER_BTN, INPUT_STYLE,
    SCROLL_STYLE, TEXT, TEXT_MUTED, HINT_STYLE, ACCENT_GREEN_DARK, WARNING,
    SURFACE, BORDER, sp, title_style,
)


class SettingsPage(QWidget):
    settings_changed = pyqtSignal()
    language_changed = pyqtSignal(str)

    CONTROL_HEIGHT = 36

    def __init__(self, settings: SettingsManager, analyzer: UsageAnalyzer = None,
                 health_context: dict = None, parent=None):
        super().__init__(parent)
        self.settings_manager = settings
        self.analyzer = analyzer
        self.health_context = health_context or {}
        self._last_issues = []
        self._idle_options = [5, 10, 15, 20, 30, 45, 60]
        self._field_labels = []
        self._field_controls = []
        self._group_frames = []
        self._init_ui()

    def _group(self) -> QFrame:
        """卡片容器：樣式必須限定選擇器，否則邊框會滲到子 QLabel。"""
        frame = QFrame()
        frame.setObjectName("settingsCard")
        frame.setStyleSheet(self._group_style())
        self._group_frames.append(frame)
        return frame

    def _style_control(self, widget):
        """統一輸入／下拉高度與樣式。"""
        import ui.theme as theme
        widget.setStyleSheet(theme.INPUT_STYLE)
        widget.setFixedHeight(self.CONTROL_HEIGHT)
        widget.setMinimumWidth(140)
        if widget not in self._field_controls:
            self._field_controls.append(widget)
        return widget

    def _group_style(self) -> str:
        import ui.theme as theme
        return f"""
            QFrame#settingsCard {{
                background-color: {theme.SURFACE};
                border: 1px solid {theme.BORDER};
                border-radius: 12px;
            }}
            QFrame#settingsCard > QLabel {{
                background: transparent;
                border: none;
            }}
        """

    def _header_style(self) -> str:
        import ui.theme as theme
        return (
            f"font-weight: bold; border: none; background: transparent; "
            f"font-size: {theme.sp(15)}px; color: {theme.TEXT};"
        )

    def _hint_style(self) -> str:
        import ui.theme as theme
        return (
            f"color: {theme.TEXT_MUTED}; font-size: {theme.sp(12)}px; "
            f"border: none; background: transparent;"
        )

    def _field_label_style(self) -> str:
        import ui.theme as theme
        return (
            f"color: {theme.TEXT}; font-size: {theme.sp(13)}px; border: none; "
            f"background: transparent; padding: 0px 4px;"
        )

    def _header(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(self._header_style())
        return label

    def _hint(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(self._hint_style())
        return label

    def _field_label(self, text: str) -> QLabel:
        """列內標籤：與輸入框同高、同字級，無外框。"""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        label.setFixedHeight(self.CONTROL_HEIGHT)
        label.setStyleSheet(self._field_label_style())
        self._field_labels.append(label)
        return label

    def _scroll_wrap(self, inner: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL_STYLE)
        scroll.setWidget(inner)
        return scroll

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        self.title = QLabel(t("settings_title"))
        self.title.setStyleSheet(title_style())
        root.addWidget(self.title)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid #B9FBC0; border-radius: 10px;
                background: #D7F5F2; top: -1px;
            }}
            QTabBar::tab {{
                background: #FFFFFF; color: {TEXT_MUTED};
                border: 1px solid #B9FBC0; border-bottom: none;
                border-top-left-radius: 8px; border-top-right-radius: 8px;
                padding: 8px 16px; margin-right: 4px; font-size: 13px;
            }}
            QTabBar::tab:selected {{
                background: #A2D2FF; color: {TEXT}; font-weight: bold;
            }}
        """)
        root.addWidget(self.tabs)

        self.tabs.addTab(self._build_general_tab(), t("settings_tab_general"))
        self.tabs.addTab(self._build_tracking_tab(), t("settings_tab_tracking"))
        self.tabs.addTab(self._build_organize_tab(), t("settings_tab_organize"))
        self.tabs.addTab(self._build_export_tab(), t("settings_tab_export"))

        self._refresh_category_ui()
        self.refresh_bridge_status()

    def _build_general_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(14)

        lang_group = self._group()
        lang_l = QVBoxLayout(lang_group)
        lang_l.setContentsMargins(16, 16, 16, 16)
        lang_l.setSpacing(10)
        self.lang_header = self._header(t("lang_header"))
        lang_l.addWidget(self.lang_header)
        self.lang_combo = QComboBox()
        self._style_control(self.lang_combo)
        self.lang_combo.addItems(["繁體中文", "English", "日本語"])
        lang_map = {"zh_TW": 0, "en_US": 1, "ja_JP": 2}
        self.lang_combo.setCurrentIndex(lang_map.get(self.settings_manager.get_language(), 0))
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_l.addWidget(self.lang_combo)
        layout.addWidget(lang_group)

        auto_group = self._group()
        auto_l = QVBoxLayout(auto_group)
        auto_l.setContentsMargins(16, 16, 16, 16)
        self.auto_check = QCheckBox(t("autostart"))
        self.auto_check.setChecked(self.settings_manager.settings.get("autostart", False))
        self.auto_check.stateChanged.connect(self._on_autostart_changed)
        self.auto_check.setStyleSheet(
            f"font-weight: bold; border: none; background: transparent; font-size: {sp(13)}px;"
        )
        auto_l.addWidget(self.auto_check)
        layout.addWidget(auto_group)

        idle_group = self._group()
        idle_l = QVBoxLayout(idle_group)
        idle_l.setContentsMargins(16, 16, 16, 16)
        idle_l.setSpacing(10)
        self.idle_header = self._header(t("idle_header"))
        idle_l.addWidget(self.idle_header)
        self.idle_desc = self._hint(t("idle_desc"))
        idle_l.addWidget(self.idle_desc)
        idle_row = QHBoxLayout()
        idle_row.setSpacing(10)
        idle_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.idle_label = self._field_label(t("idle_label"))
        idle_row.addWidget(self.idle_label)
        self.idle_combo = QComboBox()
        self._style_control(self.idle_combo)
        for m in self._idle_options:
            self.idle_combo.addItem(t("minutes_fmt", n=m), m)
        current_idle = self.settings_manager.get_idle_timeout_minutes()
        idx = self._idle_options.index(current_idle) if current_idle in self._idle_options else 3
        self.idle_combo.setCurrentIndex(idx)
        self.idle_combo.currentIndexChanged.connect(self._on_idle_changed)
        idle_row.addWidget(self.idle_combo)
        idle_row.addStretch()
        idle_l.addLayout(idle_row)
        layout.addWidget(idle_group)

        unit_group = self._group()
        unit_l = QVBoxLayout(unit_group)
        unit_l.setContentsMargins(16, 16, 16, 16)
        unit_l.setSpacing(10)
        self.unit_header = self._header(t("unit_header"))
        unit_l.addWidget(self.unit_header)
        self.unit_desc = self._hint(t("unit_desc"))
        unit_l.addWidget(self.unit_desc)
        unit_row = QHBoxLayout()
        unit_row.setSpacing(10)
        unit_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.unit_label = self._field_label(t("unit_label"))
        unit_row.addWidget(self.unit_label)
        self.unit_combo = QComboBox()
        self._style_control(self.unit_combo)
        self.unit_combo.addItem(t("unit_auto"), "auto")
        self.unit_combo.addItem(t("unit_hours"), "hours")
        self.unit_combo.addItem(t("unit_minutes"), "minutes")
        current_unit = self.settings_manager.get_duration_unit()
        for i in range(self.unit_combo.count()):
            if self.unit_combo.itemData(i) == current_unit:
                self.unit_combo.setCurrentIndex(i)
                break
        self.unit_combo.currentIndexChanged.connect(self._on_unit_changed)
        unit_row.addWidget(self.unit_combo)
        unit_row.addStretch()
        unit_l.addLayout(unit_row)
        layout.addWidget(unit_group)

        font_group = self._group()
        font_l = QVBoxLayout(font_group)
        font_l.setContentsMargins(16, 16, 16, 16)
        font_l.setSpacing(10)
        self.font_header = self._header(t("font_header"))
        font_l.addWidget(self.font_header)
        self.font_desc = self._hint(t("font_desc"))
        font_l.addWidget(self.font_desc)
        font_row = QHBoxLayout()
        font_row.setSpacing(10)
        font_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.font_label = self._field_label(t("font_label"))
        font_row.addWidget(self.font_label)
        self.font_combo = QComboBox()
        self._style_control(self.font_combo)
        self._fill_font_combo()
        self.font_combo.currentIndexChanged.connect(self._on_font_size_changed)
        font_row.addWidget(self.font_combo)
        font_row.addStretch()
        font_l.addLayout(font_row)
        layout.addWidget(font_group)

        layout.addStretch()
        return self._scroll_wrap(page)

    def _fill_font_combo(self):
        current = self.settings_manager.get_font_size()
        self.font_combo.blockSignals(True)
        self.font_combo.clear()
        for key, label_key in (
            ("small", "font_small"),
            ("medium", "font_medium"),
            ("large", "font_large"),
            ("xlarge", "font_xlarge"),
        ):
            self.font_combo.addItem(t(label_key), key)
        for i in range(self.font_combo.count()):
            if self.font_combo.itemData(i) == current:
                self.font_combo.setCurrentIndex(i)
                break
        self.font_combo.blockSignals(False)

    def _build_tracking_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(14)

        health_group = self._group()
        hl = QVBoxLayout(health_group)
        hl.setContentsMargins(16, 16, 16, 16)
        hl.setSpacing(10)
        self.health_header = self._header(t("health_header"))
        hl.addWidget(self.health_header)
        self.health_desc = self._hint(t("health_desc"))
        hl.addWidget(self.health_desc)
        btns = QHBoxLayout()
        btns.setSpacing(10)
        self.btn_health_run = QPushButton(t("btn_health_run"))
        self.btn_health_repair = QPushButton(t("btn_health_repair"))
        self.btn_health_run.setStyleSheet(PRIMARY_BTN)
        self.btn_health_repair.setStyleSheet(SECONDARY_BTN)
        self.btn_health_run.setFixedHeight(self.CONTROL_HEIGHT)
        self.btn_health_repair.setFixedHeight(self.CONTROL_HEIGHT)
        self.btn_health_run.clicked.connect(self._run_health_check)
        self.btn_health_repair.clicked.connect(self._repair_health)
        btns.addWidget(self.btn_health_run)
        btns.addWidget(self.btn_health_repair)
        btns.addStretch()
        hl.addLayout(btns)
        self.health_summary = QLabel("")
        self.health_summary.setStyleSheet(
            f"border: none; background: transparent; font-size: {sp(13)}px; font-weight: bold;"
        )
        hl.addWidget(self.health_summary)
        self.health_output = QTextEdit()
        self.health_output.setReadOnly(True)
        self.health_output.setMinimumHeight(180)
        self.health_output.setStyleSheet(
            f"border: 1px solid {BORDER}; border-radius: 8px; background: #FAFFFE; "
            f"font-size: {sp(12)}px;"
        )
        hl.addWidget(self.health_output)
        layout.addWidget(health_group)

        bridge_group = self._group()
        bl = QVBoxLayout(bridge_group)
        bl.setContentsMargins(16, 16, 16, 16)
        bl.setSpacing(10)
        self.bridge_header = self._header(t("bridge_header"))
        bl.addWidget(self.bridge_header)
        self.bridge_status = QLabel("")
        self.bridge_status.setStyleSheet(
            f"border: none; background: transparent; font-size: {sp(13)}px;"
        )
        bl.addWidget(self.bridge_status)
        ext_row = QHBoxLayout()
        ext_row.setSpacing(10)
        ext_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.ext_label = self._field_label(t("ext_id"))
        ext_row.addWidget(self.ext_label)
        self.ext_id_input = QLineEdit(self.settings_manager.get_extension_id())
        self._style_control(self.ext_id_input)
        self.ext_id_input.setMinimumWidth(220)
        ext_row.addWidget(self.ext_id_input, 1)
        self.btn_register_host = QPushButton(t("btn_register"))
        self.btn_register_host.setStyleSheet(PRIMARY_BTN)
        self.btn_register_host.setFixedHeight(self.CONTROL_HEIGHT)
        self.btn_register_host.clicked.connect(self._register_bridge)
        ext_row.addWidget(self.btn_register_host)
        bl.addLayout(ext_row)
        self.bridge_hint = self._hint(t("bridge_hint"))
        bl.addWidget(self.bridge_hint)
        layout.addWidget(bridge_group)
        layout.addStretch()
        return self._scroll_wrap(page)

    def _build_organize_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(14)

        cat_group = self._group()
        cl = QVBoxLayout(cat_group)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.setSpacing(10)
        self.cat_header = self._header(t("cat_header"))
        cl.addWidget(self.cat_header)
        self.cat_desc = self._hint(t("cat_desc"))
        cl.addWidget(self.cat_desc)
        cat_row = QHBoxLayout()
        cat_row.setSpacing(10)
        cat_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.item_label = self._field_label(t("item"))
        self.cat_label = self._field_label(t("category"))
        self.cat_app_combo = QComboBox()
        self._style_control(self.cat_app_combo)
        self.cat_app_combo.setMinimumWidth(180)
        self.cat_category_combo = QComboBox()
        self._style_control(self.cat_category_combo)
        self.cat_category_combo.addItems(self.settings_manager.get_categories())
        self.btn_set_category = QPushButton(t("btn_apply_cat"))
        self.btn_set_category.setStyleSheet(SECONDARY_BTN)
        self.btn_set_category.setFixedHeight(self.CONTROL_HEIGHT)
        self.btn_set_category.clicked.connect(self._apply_category)
        cat_row.addWidget(self.item_label)
        cat_row.addWidget(self.cat_app_combo, 2)
        cat_row.addWidget(self.cat_label)
        cat_row.addWidget(self.cat_category_combo, 1)
        cat_row.addWidget(self.btn_set_category)
        cl.addLayout(cat_row)
        self.cat_map_list = QListWidget()
        self.cat_map_list.setMinimumHeight(140)
        cl.addWidget(self.cat_map_list)
        layout.addWidget(cat_group)

        white_group = self._group()
        wl = QVBoxLayout(white_group)
        wl.setContentsMargins(16, 16, 16, 16)
        wl.setSpacing(10)
        self.white_header = self._header(t("whitelist_header"))
        wl.addWidget(self.white_header)
        self.white_desc = self._hint(t("whitelist_desc"))
        wl.addWidget(self.white_desc)
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        input_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.white_input = QLineEdit()
        self._style_control(self.white_input)
        self.btn_add = QPushButton(t("btn_add"))
        self.btn_add.setStyleSheet(PRIMARY_BTN)
        self.btn_add.setFixedHeight(self.CONTROL_HEIGHT)
        self.btn_add.clicked.connect(self._add_to_whitelist)
        input_row.addWidget(self.white_input)
        input_row.addWidget(self.btn_add)
        wl.addLayout(input_row)
        self.white_list = QListWidget()
        self.white_list.addItems(self.settings_manager.settings.get("whitelist", []))
        wl.addWidget(self.white_list)
        self.btn_remove = QPushButton(t("btn_remove"))
        self.btn_remove.setStyleSheet(DANGER_BTN)
        self.btn_remove.setFixedHeight(self.CONTROL_HEIGHT)
        self.btn_remove.clicked.connect(self._remove_from_whitelist)
        wl.addWidget(self.btn_remove)
        layout.addWidget(white_group)
        layout.addStretch()
        return self._scroll_wrap(page)

    def _build_export_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(14)

        export_group = self._group()
        el = QVBoxLayout(export_group)
        el.setContentsMargins(16, 16, 16, 16)
        el.setSpacing(10)
        self.export_header = self._header(t("export_header"))
        el.addWidget(self.export_header)
        self.export_desc = self._hint(t("export_desc"))
        el.addWidget(self.export_desc)
        date_row = QHBoxLayout()
        date_row.setSpacing(10)
        date_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.lbl_from = self._field_label(t("date_from"))
        self.lbl_to = self._field_label(t("date_to"))
        self.export_start = QDateEdit()
        self.export_end = QDateEdit()
        for w in (self.export_start, self.export_end):
            w.setCalendarPopup(True)
            w.setDisplayFormat("yyyy-MM-dd")
            self._style_control(w)
        self.export_start.setDate(QDate.currentDate().addDays(-6))
        self.export_end.setDate(QDate.currentDate())
        date_row.addWidget(self.lbl_from)
        date_row.addWidget(self.export_start)
        date_row.addWidget(self.lbl_to)
        date_row.addWidget(self.export_end)
        date_row.addStretch()
        el.addLayout(date_row)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_export_csv = QPushButton(t("btn_export_csv"))
        self.btn_export_json = QPushButton(t("btn_export_json"))
        self.btn_export_csv.setStyleSheet(PRIMARY_BTN)
        self.btn_export_json.setStyleSheet(PRIMARY_BTN)
        self.btn_export_csv.setFixedHeight(self.CONTROL_HEIGHT)
        self.btn_export_json.setFixedHeight(self.CONTROL_HEIGHT)
        self.btn_export_csv.clicked.connect(lambda: self._export("csv"))
        self.btn_export_json.clicked.connect(lambda: self._export("json"))
        btn_row.addWidget(self.btn_export_csv)
        btn_row.addWidget(self.btn_export_json)
        btn_row.addStretch()
        el.addLayout(btn_row)
        layout.addWidget(export_group)
        layout.addStretch()
        return self._scroll_wrap(page)

    def apply_language(self):
        self.title.setText(t("settings_title"))
        self.tabs.setTabText(0, t("settings_tab_general"))
        self.tabs.setTabText(1, t("settings_tab_tracking"))
        self.tabs.setTabText(2, t("settings_tab_organize"))
        self.tabs.setTabText(3, t("settings_tab_export"))

        self.lang_header.setText(t("lang_header"))
        self.auto_check.setText(t("autostart"))
        self.idle_header.setText(t("idle_header"))
        self.idle_desc.setText(t("idle_desc"))
        self.idle_label.setText(t("idle_label"))
        cur = self.idle_combo.currentData()
        self.idle_combo.blockSignals(True)
        self.idle_combo.clear()
        for m in self._idle_options:
            self.idle_combo.addItem(t("minutes_fmt", n=m), m)
        if cur in self._idle_options:
            self.idle_combo.setCurrentIndex(self._idle_options.index(cur))
        self.idle_combo.blockSignals(False)

        self.unit_header.setText(t("unit_header"))
        self.unit_desc.setText(t("unit_desc"))
        self.unit_label.setText(t("unit_label"))
        cur_unit = self.unit_combo.currentData()
        self.unit_combo.blockSignals(True)
        self.unit_combo.clear()
        self.unit_combo.addItem(t("unit_auto"), "auto")
        self.unit_combo.addItem(t("unit_hours"), "hours")
        self.unit_combo.addItem(t("unit_minutes"), "minutes")
        for i in range(self.unit_combo.count()):
            if self.unit_combo.itemData(i) == cur_unit:
                self.unit_combo.setCurrentIndex(i)
                break
        self.unit_combo.blockSignals(False)

        self.font_header.setText(t("font_header"))
        self.font_desc.setText(t("font_desc"))
        self.font_label.setText(t("font_label"))
        self._fill_font_combo()

        self.health_header.setText(t("health_header"))
        self.health_desc.setText(t("health_desc"))
        self.btn_health_run.setText(t("btn_health_run"))
        self.btn_health_repair.setText(t("btn_health_repair"))
        self.bridge_header.setText(t("bridge_header"))
        self.ext_label.setText(t("ext_id"))
        self.btn_register_host.setText(t("btn_register"))
        self.bridge_hint.setText(t("bridge_hint"))
        self.cat_header.setText(t("cat_header"))
        self.cat_desc.setText(t("cat_desc"))
        self.item_label.setText(t("item"))
        self.cat_label.setText(t("category"))
        self.btn_set_category.setText(t("btn_apply_cat"))
        self.white_header.setText(t("whitelist_header"))
        self.white_desc.setText(t("whitelist_desc"))
        self.btn_add.setText(t("btn_add"))
        self.btn_remove.setText(t("btn_remove"))
        self.export_header.setText(t("export_header"))
        self.export_desc.setText(t("export_desc"))
        self.lbl_from.setText(t("date_from"))
        self.lbl_to.setText(t("date_to"))
        self.btn_export_csv.setText(t("btn_export_csv"))
        self.btn_export_json.setText(t("btn_export_json"))
        self.refresh_bridge_status()

    def refresh_data(self):
        import ui.theme as theme

        self._refresh_category_ui()
        self.refresh_bridge_status()
        if hasattr(self, "unit_combo"):
            current = self.settings_manager.get_duration_unit()
            self.unit_combo.blockSignals(True)
            for i in range(self.unit_combo.count()):
                if self.unit_combo.itemData(i) == current:
                    self.unit_combo.setCurrentIndex(i)
                    break
            self.unit_combo.blockSignals(False)
        if hasattr(self, "font_combo"):
            self._fill_font_combo()

        self.title.setStyleSheet(theme.title_style())
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid #B9FBC0; border-radius: 10px;
                background: #D7F5F2; top: -1px;
            }}
            QTabBar::tab {{
                background: #FFFFFF; color: {TEXT_MUTED};
                border: 1px solid #B9FBC0; border-bottom: none;
                border-top-left-radius: 8px; border-top-right-radius: 8px;
                padding: 8px 16px; margin-right: 4px; font-size: {theme.sp(13)}px;
            }}
            QTabBar::tab:selected {{
                background: #A2D2FF; color: {TEXT}; font-weight: bold;
            }}
        """)

        for frame in self._group_frames:
            frame.setStyleSheet(self._group_style())

        for header in (
            self.lang_header, self.idle_header, self.unit_header, self.font_header,
            self.health_header, self.bridge_header, self.cat_header,
            self.white_header, self.export_header,
        ):
            header.setStyleSheet(self._header_style())
        for hint in (
            self.idle_desc, self.unit_desc, self.font_desc, self.health_desc,
            self.bridge_hint, self.cat_desc, self.white_desc, self.export_desc,
        ):
            hint.setStyleSheet(self._hint_style())

        for label in self._field_labels:
            label.setFixedHeight(self.CONTROL_HEIGHT)
            label.setStyleSheet(self._field_label_style())

        for w in self._field_controls:
            self._style_control(w)

        self.auto_check.setStyleSheet(
            f"font-weight: bold; border: none; background: transparent; "
            f"font-size: {theme.sp(13)}px;"
        )
        for btn in (
            self.btn_health_run, self.btn_health_repair, self.btn_register_host,
            self.btn_set_category, self.btn_add, self.btn_remove,
            self.btn_export_csv, self.btn_export_json,
        ):
            btn.setFixedHeight(self.CONTROL_HEIGHT)
        self.btn_health_run.setStyleSheet(theme.PRIMARY_BTN)
        self.btn_health_repair.setStyleSheet(theme.SECONDARY_BTN)
        self.btn_register_host.setStyleSheet(theme.PRIMARY_BTN)
        self.btn_set_category.setStyleSheet(theme.SECONDARY_BTN)
        self.btn_add.setStyleSheet(theme.PRIMARY_BTN)
        self.btn_remove.setStyleSheet(theme.DANGER_BTN)
        self.btn_export_csv.setStyleSheet(theme.PRIMARY_BTN)
        self.btn_export_json.setStyleSheet(theme.PRIMARY_BTN)
        self.health_output.setStyleSheet(
            f"border: 1px solid {BORDER}; border-radius: 8px; background: #FAFFFE; "
            f"font-size: {theme.sp(12)}px;"
        )
        self.health_summary.setStyleSheet(
            f"border: none; background: transparent; font-size: {theme.sp(13)}px; font-weight: bold;"
        )

    def refresh_bridge_status(self):
        import ui.theme as theme
        if BrowserBridgeWatcher.is_connected(120):
            self.bridge_status.setText(t("bridge_ok"))
            self.bridge_status.setStyleSheet(
                f"border: none; background: transparent; "
                f"font-size: {theme.sp(13)}px; color: {ACCENT_GREEN_DARK};"
            )
        else:
            self.bridge_status.setText(t("bridge_warn"))
            self.bridge_status.setStyleSheet(
                f"border: none; background: transparent; "
                f"font-size: {theme.sp(13)}px; color: {WARNING};"
            )
    def _refresh_category_ui(self):
        names = set(self.settings_manager.get_category_map().keys())
        if self.analyzer:
            try:
                start, end = self.analyzer.get_month_range()
                names.update(self.analyzer.get_all_apps_in_range(start, end))
                for r in self.analyzer.get_website_rankings(start, end):
                    names.add(r["app_name"])
            except Exception:
                pass
        current = self.cat_app_combo.currentText()
        self.cat_app_combo.blockSignals(True)
        self.cat_app_combo.clear()
        for name in sorted(names, key=lambda x: x.lower()):
            self.cat_app_combo.addItem(name)
        if current:
            idx = self.cat_app_combo.findText(current)
            if idx >= 0:
                self.cat_app_combo.setCurrentIndex(idx)
        self.cat_app_combo.blockSignals(False)
        self.cat_map_list.clear()
        mapping = self.settings_manager.get_category_map()
        for name in sorted(mapping.keys(), key=lambda x: x.lower()):
            self.cat_map_list.addItem(f"{name}  →  {mapping[name]}")

    def _on_language_changed(self, index):
        langs = ["zh_TW", "en_US", "ja_JP"]
        lang = langs[index]
        self.settings_manager.set_language(lang)
        set_language(lang)
        self.language_changed.emit(lang)
        self.settings_changed.emit()

    def _on_autostart_changed(self, state):
        self.settings_manager.set_autostart(state == Qt.CheckState.Checked.value)

    def _on_idle_changed(self, _index):
        minutes = self.idle_combo.currentData() or 20
        self.settings_manager.set_idle_timeout_minutes(int(minutes))
        self.settings_changed.emit()

    def _on_unit_changed(self, _index):
        unit = self.unit_combo.currentData() or "auto"
        self.settings_manager.set_duration_unit(unit)
        self.settings_changed.emit()

    def _on_font_size_changed(self, _index):
        size = self.font_combo.currentData() or "medium"
        self.settings_manager.set_font_size(size)
        self.settings_changed.emit()

    def _run_health_check(self):
        if not self.analyzer:
            return
        ctx = self.health_context
        issues = run_health_check(
            self.analyzer.db, self.settings_manager,
            is_tracking=ctx.get("is_tracking"),
            is_idle=ctx.get("is_idle"),
            is_paused=ctx.get("is_paused"),
        )
        self._last_issues = issues
        ok = sum(1 for i in issues if i.level == "ok")
        warn = sum(1 for i in issues if i.level == "warn")
        err = sum(1 for i in issues if i.level == "error")
        self.health_summary.setText(t("health_summary", ok=ok, warn=warn, error=err))
        color = "#B22222" if err else (WARNING if warn else ACCENT_GREEN_DARK)
        self.health_summary.setStyleSheet(
            f"border: none; background: transparent; font-size: {sp(13)}px; "
            f"font-weight: bold; color: {color};"
        )
        self.health_output.setPlainText(issues_to_text(issues))

    def _repair_health(self):
        if not self.analyzer:
            return
        if not self._last_issues:
            self._run_health_check()
        n = repair_health_issues(self.analyzer.db, self.settings_manager, self._last_issues)
        QMessageBox.information(self, t("msg_updated"), t("msg_repair_done", n=n))
        self._run_health_check()
        self.settings_changed.emit()

    def _register_bridge(self):
        ext_id = self.ext_id_input.text().strip()
        if not ext_id:
            QMessageBox.warning(self, t("msg_tip"), t("msg_need_ext_id"))
            return
        self.settings_manager.set_extension_id(ext_id)
        ok = register_native_host(ext_id)
        if ok:
            QMessageBox.information(self, t("msg_bridge_ok"), t("msg_bridge_ok_body"))
        else:
            QMessageBox.critical(self, t("msg_bridge_fail"), t("msg_bridge_fail"))
        self.refresh_bridge_status()
        self.settings_changed.emit()

    def _apply_category(self):
        name = self.cat_app_combo.currentText().strip()
        category = self.cat_category_combo.currentText().strip()
        if not name or not category:
            return
        self.settings_manager.set_category(name, category)
        self._refresh_category_ui()
        self.settings_changed.emit()

    def _add_to_whitelist(self):
        text = self.white_input.text().strip()
        if text:
            if text not in self.settings_manager.settings["whitelist"]:
                self.settings_manager.add_to_whitelist(text)
                self.white_list.addItem(text)
                self.white_input.clear()
                self.settings_changed.emit()
            else:
                QMessageBox.warning(self, t("msg_tip"), t("msg_already_listed"))

    def _remove_from_whitelist(self):
        current_item = self.white_list.currentItem()
        if current_item:
            name = current_item.text()
            self.settings_manager.remove_from_whitelist(name)
            self.white_list.takeItem(self.white_list.row(current_item))
            self.settings_changed.emit()

    def _export(self, fmt: str):
        if not self.analyzer:
            return
        start_q = self.export_start.date()
        end_q = self.export_end.date()
        start = datetime(start_q.year(), start_q.month(), start_q.day())
        end = datetime(end_q.year(), end_q.month(), end_q.day()) + timedelta(days=1)
        if end <= start:
            QMessageBox.warning(self, t("msg_tip"), t("msg_date_error"))
            return
        stamp = date.today().strftime("%Y%m%d")
        if fmt == "csv":
            path, _ = QFileDialog.getSaveFileName(
                self, t("btn_export_csv"), f"screenget_export_{stamp}.csv", "CSV Files (*.csv)"
            )
            if not path:
                return
            try:
                UsageExporter(self.analyzer).export_csv(path, start, end)
                QMessageBox.information(self, t("msg_export_done"), t("msg_exported_to", path=path))
            except Exception as e:
                QMessageBox.critical(self, t("msg_export_fail"), str(e))
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, t("btn_export_json"), f"screenget_export_{stamp}.json", "JSON Files (*.json)"
            )
            if not path:
                return
            try:
                UsageExporter(self.analyzer).export_json(path, start, end)
                QMessageBox.information(self, t("msg_export_done"), t("msg_exported_to", path=path))
            except Exception as e:
                QMessageBox.critical(self, t("msg_export_fail"), str(e))
