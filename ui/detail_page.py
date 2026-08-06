"""
detail_page.py - 詳細清單頁面（可點擊項目 + 可信度）
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.analyzer import UsageAnalyzer
from core.i18n import t
from ui.period_bar import PeriodBar
from ui.widgets import EmptyState, LoadingOverlay, UnitSwitcher, CredibilityBadge
from ui.theme import SCROLL_STYLE, PRIMARY_BTN, SURFACE, BORDER, TEXT, TEXT_MUTED, HINT_STYLE


class DetailItem(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, rank: int, name: str, duration: str, credibility: str = "", parent=None):
        super().__init__(parent)
        self.name = name
        self.setObjectName("detailItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            #detailItem {{
                background-color: {SURFACE}; border-radius: 8px;
                border: 1px solid {BORDER}; margin: 2px 0px;
            }}
            #detailItem:hover {{ background-color: #F0FBF2; border: 1px solid #A2D2FF; }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        rank_label = QLabel(str(rank))
        rank_label.setFixedWidth(30)
        rank_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px; font-weight: bold;")
        layout.addWidget(rank_label)
        name_label = QLabel(name)
        name_label.setStyleSheet(f"color: {TEXT}; font-size: 14px;")
        name_label.setWordWrap(True)
        layout.addWidget(name_label, 1)
        if credibility:
            badge = CredibilityBadge()
            badge.set_level(credibility)
            layout.addWidget(badge)
        duration_label = QLabel(duration)
        duration_label.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: bold;")
        layout.addWidget(duration_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.name)
        super().mousePressEvent(event)


class DetailListPage(QWidget):
    back_clicked = pyqtSignal()
    item_clicked = pyqtSignal(str)
    unit_changed = pyqtSignal(str)

    def __init__(self, analyzer: UsageAnalyzer, title_key: str, app_type: str = None, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer
        self.title_key = title_key
        self.app_type = app_type
        self._init_ui()

    @property
    def current_period(self) -> str:
        return self.period_bar.current_period

    def _unit(self) -> str:
        if self.analyzer.settings:
            return self.analyzer.settings.get_duration_unit()
        return "auto"

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self.btn_back = QPushButton(t("back"))
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_clicked.emit)
        self.btn_back.setStyleSheet(PRIMARY_BTN)
        header.addWidget(self.btn_back)

        self.title_label = QLabel(t(self.title_key))
        self.title_label.setStyleSheet(
            f"color: {TEXT}; font-size: 20px; font-weight: bold; margin-left: 10px;"
        )
        header.addWidget(self.title_label)
        header.addStretch()
        self.unit_switcher = UnitSwitcher(self._unit())
        self.unit_switcher.changed.connect(self._on_unit_changed)
        header.addWidget(self.unit_switcher)
        self.period_bar = PeriodBar()
        self.period_bar.changed.connect(self.refresh_data)
        header.addWidget(self.period_bar)
        layout.addLayout(header)

        self.hint = QLabel(t("detail_click_hint"))
        self.hint.setStyleSheet(HINT_STYLE)
        layout.addWidget(self.hint)

        self.cred_legend = QLabel(t("cred_legend") if self.app_type == "browser" else "")
        self.cred_legend.setStyleSheet(HINT_STYLE)
        self.cred_legend.setVisible(self.app_type == "browser")
        layout.addWidget(self.cred_legend)

        self.empty = EmptyState()
        self.empty.action_btn.hide()
        self.empty.hide()
        layout.addWidget(self.empty)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(SCROLL_STYLE)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_container)
        layout.addWidget(self.scroll, 1)

        self.loading = LoadingOverlay(self)

    def _on_unit_changed(self, unit: str):
        if self.analyzer.settings:
            self.analyzer.settings.set_duration_unit(unit)
        self.unit_changed.emit(unit)
        self.refresh_data()

    def sync_unit(self):
        self.unit_switcher.set_unit(self._unit())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.loading.isVisible():
            self.loading.setGeometry(self.rect())

    def set_period(self, period: str):
        self.period_bar.set_period(period)
        self.refresh_data()

    def set_range_from_bar(self, other: PeriodBar):
        self.period_bar.blockSignals(True)
        self.period_bar.sync_from(other)
        self.period_bar.blockSignals(False)
        self.refresh_data()

    def apply_language(self):
        self.btn_back.setText(t("back"))
        self.title_label.setText(t(self.title_key))
        self.hint.setText(t("detail_click_hint"))
        if self.app_type == "browser":
            self.cred_legend.setText(t("cred_legend"))
        self.unit_switcher.apply_language()
        self.period_bar.apply_language()
        self.loading.apply_language()
        self.refresh_data()

    def refresh_data(self):
        self.loading.show_loading()
        try:
            self.sync_unit()
            while self.list_layout.count():
                item = self.list_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()

            start, end, _ = self.period_bar.get_range()
            if self.app_type == "browser":
                rankings = self.analyzer.get_website_rankings(start, end)
            else:
                rankings = self.analyzer.get_app_rankings(start, end, app_type=self.app_type)
            rankings = [r for r in rankings if r["total_seconds"] > 0]

            self.list_layout.addStretch()
            for i, r in enumerate(rankings):
                item = DetailItem(
                    i + 1,
                    r["app_name"],
                    r["formatted_time"],
                    credibility=r.get("credibility", "") if self.app_type == "browser" else "",
                )
                item.clicked.connect(self.item_clicked.emit)
                self.list_layout.insertWidget(self.list_layout.count() - 1, item)

            if not rankings:
                self.scroll.hide()
                self.empty.show()
                self.empty.configure(title=t("no_records"), body=t("empty_body"), show_action=False)
                self.empty.action_btn.hide()
            else:
                self.empty.hide()
                self.scroll.show()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Detail list refresh error: {e}")
        finally:
            self.loading.hide_loading()
