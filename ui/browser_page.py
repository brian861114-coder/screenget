"""
browser_page.py - 瀏覽器分析介面（第一／二層）
層級：總時長概覽 → 網站排行 →（點擊進入）單一網站詳情
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import pyqtSignal

from core.analyzer import UsageAnalyzer
from core.i18n import t
from ui.charts import UsageBarChart, TrendChart
from ui.period_bar import PeriodBar
from ui.widgets import StatCard, EmptyState, LoadingOverlay, SectionHeader, UnitSwitcher, CredibilityBadge
from ui.theme import SCROLL_STYLE, HINT_STYLE, title_style


class BrowserPage(QWidget):
    website_clicked = pyqtSignal(str)
    detail_requested = pyqtSignal(str)
    open_settings = pyqtSignal()
    unit_changed = pyqtSignal(str)

    def __init__(self, analyzer: UsageAnalyzer, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer
        self._top_site = None
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
        self.title = QLabel(t("browser_title"))
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

        hint_row = QHBoxLayout()
        self.layer_hint = QLabel(t("browser_layer_hint"))
        self.layer_hint.setStyleSheet(HINT_STYLE)
        hint_row.addWidget(self.layer_hint, 1)
        self.cred_badge = CredibilityBadge()
        hint_row.addWidget(self.cred_badge)
        self.root.addLayout(hint_row)

        self.cred_legend = QLabel(t("cred_legend"))
        self.cred_legend.setStyleSheet(HINT_STYLE)
        self.root.addWidget(self.cred_legend)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.card_total = StatCard(t("card_browse_total"), clickable=True)
        self.card_sites = StatCard(t("card_sites"), clickable=True)
        self.card_top = StatCard(t("card_top_site"), clickable=True)
        self.card_total.clicked.connect(lambda: self.detail_requested.emit("browser"))
        self.card_sites.clicked.connect(lambda: self.detail_requested.emit("browser"))
        self.card_top.clicked.connect(self._on_top_site_click)
        cards.addWidget(self.card_total)
        cards.addWidget(self.card_sites)
        cards.addWidget(self.card_top)
        self.root.addLayout(cards)

        self.empty = EmptyState()
        self.empty.action_clicked.connect(self.open_settings.emit)
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

        self.sec_trend = SectionHeader(t("section_browse_trend"), t("layer_l1"))
        bl.addWidget(self.sec_trend)
        self.trend_chart = TrendChart(width=12, height=3)
        self.trend_chart.setMinimumHeight(200)
        bl.addWidget(self.trend_chart)

        self.sec_ranking = SectionHeader(t("section_site_ranking"), t("chart_click_site_hint"))
        bl.addWidget(self.sec_ranking)
        self.ranking_chart = UsageBarChart(width=12, height=5)
        self.ranking_chart.setMinimumHeight(400)
        self.ranking_chart.item_clicked.connect(self.website_clicked.emit)
        bl.addWidget(self.ranking_chart)
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

    def _on_top_site_click(self):
        if self._top_site:
            self.website_clicked.emit(self._top_site)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.loading.isVisible():
            self.loading.setGeometry(self.rect())

    def apply_language(self):
        self.title.setText(t("browser_title"))
        self.title.setStyleSheet(title_style())
        self.layer_hint.setText(t("browser_layer_hint"))
        self.cred_legend.setText(t("cred_legend"))
        self.card_total.set_title(t("card_browse_total"))
        self.card_sites.set_title(t("card_sites"))
        self.card_top.set_title(t("card_top_site"))
        self.card_total.apply_language()
        self.card_sites.apply_language()
        self.card_top.apply_language()
        self.sec_trend.set_title(t("section_browse_trend"))
        self.sec_trend.set_hint(t("layer_l1"))
        self.sec_ranking.set_title(t("section_site_ranking"))
        self.sec_ranking.set_hint(t("chart_click_site_hint"))
        self.unit_switcher.apply_language()
        self.period_bar.apply_language()
        self.empty.configure()
        self.loading.apply_language()
        self.refresh_data()

    def refresh_data(self):
        self.loading.show_loading()
        try:
            self.sync_unit()
            unit = self._unit()
            start, end, _ = self.period_bar.get_range()
            rankings = self.analyzer.get_website_rankings(start, end)
            total = sum(r["total_seconds"] for r in rankings)
            self.card_total.set_value(self.analyzer.format_duration(total))
            self.card_sites.set_value(str(len(rankings)))
            self._top_site = rankings[0]["app_name"] if rankings else None
            self.card_top.set_value(self._top_site or "—")

            summary = self.analyzer.get_browser_credibility_summary(start, end)
            if summary["total_seconds"] > 0:
                self.cred_badge.set_level(summary["credibility"], summary["url_percent"])
            else:
                self.cred_badge.set_level("")

            if not rankings:
                self.content.hide()
                self.empty.show()
            else:
                self.empty.hide()
                self.content.show()
                self.ranking_chart.update_chart(rankings, max_items=5, unit=unit)
                trend = self.analyzer.get_trend_for_range(start, end, app_type="browser")
                self.trend_chart.update_chart(trend, unit=unit)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Browser dashboard refresh error: {e}")
        finally:
            self.loading.hide_loading()
