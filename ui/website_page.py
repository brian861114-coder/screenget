"""
website_page.py - 單一網站分析（瀏覽器第三層）
層級：瀏覽器總覽 → 網站排行 → 本頁（網站趨勢／頁面）
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QScrollArea
)
from PyQt6.QtCore import pyqtSignal

from core.analyzer import UsageAnalyzer
from core.i18n import t
from ui.charts import TimelineChart, HourlyChart, TrendChart, UsageBarChart
from ui.period_bar import PeriodBar
from ui.widgets import (
    StatCard, EmptyState, LoadingOverlay, SectionHeader, UnitSwitcher, CredibilityBadge
)
from ui.theme import SCROLL_STYLE, INPUT_STYLE, HINT_STYLE, title_style


class WebsitePage(QWidget):
    """單一網站詳情：時長卡片、時間軸、小時分佈、趨勢、頁面排行"""

    back_clicked = pyqtSignal()
    unit_changed = pyqtSignal(str)

    def __init__(self, analyzer: UsageAnalyzer, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer
        self.current_site = None
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
        self.title = QLabel(t("website_title"))
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

        self.layer_hint = QLabel(t("website_layer_hint"))
        self.layer_hint.setStyleSheet(HINT_STYLE)
        self.root.addWidget(self.layer_hint)

        select_layout = QHBoxLayout()
        self.select_label = QLabel(t("select_site"))
        self.select_label.setStyleSheet("color: #445566; font-size: 14px;")
        select_layout.addWidget(self.select_label)
        self.site_combo = QComboBox()
        self.site_combo.setMinimumWidth(280)
        self.site_combo.setMinimumHeight(36)
        self.site_combo.setStyleSheet(INPUT_STYLE)
        self.site_combo.currentTextChanged.connect(self._on_site_change)
        select_layout.addWidget(self.site_combo)
        self.precision_badge = CredibilityBadge()
        select_layout.addWidget(self.precision_badge)
        select_layout.addStretch()
        self.root.addLayout(select_layout)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.card_daily = StatCard(t("card_today"))
        self.card_weekly = StatCard(t("card_week"))
        self.card_monthly = StatCard(t("card_month"))
        cards.addWidget(self.card_daily)
        cards.addWidget(self.card_weekly)
        cards.addWidget(self.card_monthly)
        self.root.addLayout(cards)

        self.empty = EmptyState()
        self.empty.action_btn.hide()
        self.empty.hide()
        self.root.addWidget(self.empty)

        self.content = QWidget()
        cl = QVBoxLayout(self.content)
        cl.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL_STYLE)
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(12)

        self.sec_timeline = SectionHeader(t("section_timeline"))
        bl.addWidget(self.sec_timeline)
        self.timeline_chart = TimelineChart(width=12, height=3)
        self.timeline_chart.setMinimumHeight(200)
        bl.addWidget(self.timeline_chart)

        self.sec_hourly = SectionHeader(t("section_hourly"))
        bl.addWidget(self.sec_hourly)
        self.hourly_chart = HourlyChart(width=12, height=3)
        self.hourly_chart.setMinimumHeight(200)
        bl.addWidget(self.hourly_chart)

        self.sec_trend = SectionHeader(t("section_site_trend"))
        bl.addWidget(self.sec_trend)
        self.trend_chart = TrendChart(width=12, height=3)
        self.trend_chart.setMinimumHeight(200)
        bl.addWidget(self.trend_chart)

        self.sec_pages = SectionHeader(t("section_page_ranking"))
        bl.addWidget(self.sec_pages)
        self.pages_chart = UsageBarChart(width=12, height=4)
        self.pages_chart.setMinimumHeight(280)
        bl.addWidget(self.pages_chart)
        bl.addStretch()
        scroll.setWidget(body)
        cl.addWidget(scroll)
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

    def _on_site_change(self, site: str):
        self.current_site = site if site else None
        self.refresh_data()

    def set_site(self, site: str):
        self.site_combo.blockSignals(True)
        idx = self.site_combo.findText(site)
        if idx >= 0:
            self.site_combo.setCurrentIndex(idx)
        elif site:
            self.site_combo.addItem(site)
            self.site_combo.setCurrentText(site)
        self.current_site = site if site else None
        self.site_combo.blockSignals(False)
        self.refresh_data()

    def set_range_from_bar(self, other: PeriodBar):
        self.period_bar.blockSignals(True)
        self.period_bar.sync_from(other)
        self.period_bar.blockSignals(False)

    def apply_language(self):
        self.title.setText(t("website_title"))
        self.title.setStyleSheet(title_style())
        self.layer_hint.setText(t("website_layer_hint"))
        self.select_label.setText(t("select_site"))
        self.card_daily.set_title(t("card_today"))
        self.card_weekly.set_title(t("card_week"))
        self.card_monthly.set_title(t("card_month"))
        self.sec_timeline.set_title(t("section_timeline"))
        self.sec_hourly.set_title(t("section_hourly"))
        self.sec_trend.set_title(t("section_site_trend"))
        self.sec_pages.set_title(t("section_page_ranking"))
        self.unit_switcher.apply_language()
        self.period_bar.apply_language()
        self.loading.apply_language()
        self.refresh_data()

    def refresh_data(self):
        self.loading.show_loading()
        try:
            self.sync_unit()
            unit = self._unit()
            self._refresh_site_list()
            if not self.current_site:
                self.content.hide()
                self.precision_badge.set_level("")
                self.empty.show()
                self.empty.configure(show_action=False)
                self.empty.action_btn.hide()
                return

            self.empty.hide()
            self.content.show()
            site = self.current_site

            self.card_daily.set_value(
                self.analyzer.format_duration(self.analyzer.get_website_daily_total(site))
            )
            self.card_weekly.set_value(
                self.analyzer.format_duration(self.analyzer.get_website_weekly_total(site))
            )
            self.card_monthly.set_value(
                self.analyzer.format_duration(self.analyzer.get_website_monthly_total(site))
            )

            start, end, _ = self.period_bar.get_range()
            cred = self.analyzer.get_website_credibility(start, end, site)
            self.precision_badge.set_level(cred["credibility"], cred["url_percent"])

            if self.period_bar.is_single_day():
                blocks = self.analyzer.get_website_time_blocks(start, end, site)
                self.timeline_chart.update_chart(blocks, target_date=start.date(), unit=unit)
                self.hourly_chart.update_chart(
                    self.analyzer.get_website_hourly(start, end, site), unit=unit
                )
            else:
                self.timeline_chart.update_chart([], unit=unit)
                self.hourly_chart.update_chart({}, unit=unit)

            self.trend_chart.update_chart(
                self.analyzer.get_website_trend(start, end, site), unit=unit
            )
            pages, _ = self.analyzer.get_website_pages(start, end, site)
            self.pages_chart.update_chart(pages, max_items=8, unit=unit)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Website page refresh error: {e}")
        finally:
            self.loading.hide_loading()

    def _refresh_site_list(self):
        start, end = self.analyzer.get_month_range()
        sites = self.analyzer.get_all_websites_in_range(start, end)
        previous = self.current_site or self.site_combo.currentText()
        self.site_combo.blockSignals(True)
        self.site_combo.clear()
        for site in sites:
            self.site_combo.addItem(site)
        if previous and self.site_combo.findText(previous) >= 0:
            self.site_combo.setCurrentText(previous)
            self.current_site = previous
        elif previous and previous not in sites:
            self.site_combo.addItem(previous)
            self.site_combo.setCurrentText(previous)
            self.current_site = previous
        elif sites:
            self.site_combo.setCurrentIndex(0)
            self.current_site = self.site_combo.currentText()
        else:
            self.current_site = None
        self.site_combo.blockSignals(False)
