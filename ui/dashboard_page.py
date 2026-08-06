"""
dashboard_page.py - 展示介面（儀表板）
"""

from typing import List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QComboBox
)
from PyQt6.QtCore import pyqtSignal

from core.analyzer import UsageAnalyzer
from core.i18n import t
from ui.charts import TimelineChart, UsageBarChart, HourlyChart
from ui.period_bar import PeriodBar
from ui.widgets import StatCard, EmptyState, LoadingOverlay, SectionHeader, UnitSwitcher
from ui.theme import SCROLL_STYLE, INPUT_STYLE, title_style


class DashboardPage(QWidget):
    app_clicked = pyqtSignal(str)
    detail_requested = pyqtSignal(str)
    open_settings = pyqtSignal()
    unit_changed = pyqtSignal(str)

    def __init__(self, analyzer: UsageAnalyzer, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer
        self._init_ui()

    @property
    def current_period(self) -> str:
        return self.period_bar.current_period

    def _unit(self) -> str:
        if self.analyzer.settings:
            return self.analyzer.settings.get_duration_unit()
        return "auto"

    def _init_ui(self):
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(24, 20, 24, 20)
        self.root.setSpacing(16)

        header = QHBoxLayout()
        self.title = QLabel(t("dash_title"))
        self.title.setStyleSheet(title_style())
        header.addWidget(self.title)
        header.addStretch()
        self.unit_switcher = UnitSwitcher(self._unit())
        self.unit_switcher.changed.connect(self._on_unit_changed)
        header.addWidget(self.unit_switcher)
        self.period_bar = PeriodBar()
        self.period_bar.changed.connect(self.refresh_data)
        header.addWidget(self.period_bar)
        self.root.addLayout(header)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        self.card_total = StatCard(t("card_total"), clickable=True)
        self.card_apps = StatCard(t("card_apps"))
        self.card_top = StatCard(t("card_top"))
        self.card_total.clicked.connect(lambda: self.detail_requested.emit("app"))
        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_apps)
        cards_layout.addWidget(self.card_top)
        self.root.addLayout(cards_layout)

        self.empty = EmptyState()
        self.empty.action_clicked.connect(self.open_settings.emit)
        self.empty.hide()
        self.root.addWidget(self.empty)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL_STYLE)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(12)

        timeline_header = QHBoxLayout()
        self.sec_timeline = SectionHeader(t("section_timeline"))
        timeline_header.addWidget(self.sec_timeline, 1)
        self.timeline_filter = QComboBox()
        self.timeline_filter.setMinimumWidth(200)
        self.timeline_filter.setStyleSheet(INPUT_STYLE)
        self.timeline_filter.addItem(t("filter_top5"))
        self.timeline_filter.currentTextChanged.connect(self._on_timeline_filter_changed)
        timeline_header.addWidget(self.timeline_filter)
        scroll_layout.addLayout(timeline_header)
        self.timeline_chart = TimelineChart(width=12, height=4)
        self.timeline_chart.setMinimumHeight(250)
        scroll_layout.addWidget(self.timeline_chart)

        self.sec_hourly = SectionHeader(t("section_hourly"))
        scroll_layout.addWidget(self.sec_hourly)
        self.hourly_chart = HourlyChart(width=12, height=3)
        self.hourly_chart.setMinimumHeight(200)
        scroll_layout.addWidget(self.hourly_chart)

        self.sec_ranking = SectionHeader(t("section_ranking"), t("chart_click_hint"))
        scroll_layout.addWidget(self.sec_ranking)
        self.ranking_chart = UsageBarChart(width=12, height=5)
        self.ranking_chart.setMinimumHeight(350)
        self.ranking_chart.item_clicked.connect(self.app_clicked.emit)
        scroll_layout.addWidget(self.ranking_chart)

        self.sec_category = SectionHeader(t("section_category"))
        scroll_layout.addWidget(self.sec_category)
        self.category_chart = UsageBarChart(width=12, height=3)
        self.category_chart.setMinimumHeight(220)
        scroll_layout.addWidget(self.category_chart)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        content_layout.addWidget(scroll)
        self.root.addWidget(self.content, 1)

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

    def _on_timeline_filter_changed(self):
        if self.period_bar.is_single_day():
            self.refresh_data()

    def apply_language(self):
        self.title.setText(t("dash_title"))
        self.title.setStyleSheet(title_style())
        self.card_total.set_title(t("card_total"))
        self.card_apps.set_title(t("card_apps"))
        self.card_top.set_title(t("card_top"))
        self.card_total.apply_language()
        self.sec_timeline.set_title(t("section_timeline"))
        self.sec_hourly.set_title(t("section_hourly"))
        self.sec_ranking.set_title(t("section_ranking"))
        self.sec_ranking.set_hint(t("chart_click_hint"))
        self.sec_category.set_title(t("section_category"))
        self.unit_switcher.apply_language()
        self.period_bar.apply_language()
        self.empty.configure()
        self.loading.apply_language()
        self.timeline_filter.blockSignals(True)
        if self.timeline_filter.count() > 0:
            self.timeline_filter.setItemText(0, t("filter_top5"))
        self.timeline_filter.blockSignals(False)
        self.refresh_data()

    def refresh_data(self):
        self.loading.show_loading()
        try:
            self.sync_unit()
            unit = self._unit()
            start, end, _ = self.period_bar.get_range()
            rankings = self.analyzer.get_app_rankings(start, end)
            total = self.analyzer.get_total_usage(start, end)

            self.card_total.set_value(self.analyzer.format_duration(total))
            self.card_apps.set_value(str(len(rankings)))
            self.card_top.set_value(rankings[0]["app_name"] if rankings else "—")

            if not rankings:
                self.content.hide()
                self.empty.show()
                self.empty.configure(
                    title=t("empty_title"),
                    body=t("empty_body"),
                    action=t("empty_action"),
                    show_action=True,
                )
            else:
                self.empty.hide()
                self.content.show()
                self.ranking_chart.update_chart(rankings, max_items=5, unit=unit)
                categories = self.analyzer.get_category_rankings(start, end)
                self.category_chart.update_chart(categories, max_items=8, unit=unit)

                if self.period_bar.is_single_day():
                    self._update_timeline_filter_list(rankings)
                    selected = self.timeline_filter.currentText()
                    blocks = self.analyzer.get_time_blocks(start, end)
                    if selected in (t("filter_top5"), "TOP 5 most used"):
                        top_names = [r["app_name"] for r in rankings[:5]]
                        blocks = [b for b in blocks if b["app_name"] in top_names]
                    else:
                        blocks = [b for b in blocks if b["app_name"] == selected]
                    self.timeline_chart.update_chart(blocks, target_date=start.date(), unit=unit)
                    self.hourly_chart.update_chart(
                        self.analyzer.get_hourly_usage(start, end), unit=unit
                    )
                else:
                    self.timeline_chart.update_chart([], unit=unit)
                    self.hourly_chart.update_chart({}, unit=unit)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Dashboard refresh error: {e}")
        finally:
            self.loading.hide_loading()

    def _update_timeline_filter_list(self, rankings: List[Dict[str, Any]]):
        current_text = self.timeline_filter.currentText()
        self.timeline_filter.blockSignals(True)
        self.timeline_filter.clear()
        self.timeline_filter.addItem(t("filter_top5"))
        self.timeline_filter.addItems(sorted(r["app_name"] for r in rankings))
        idx = self.timeline_filter.findText(current_text)
        self.timeline_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.timeline_filter.blockSignals(False)
