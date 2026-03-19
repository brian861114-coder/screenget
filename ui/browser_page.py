"""
browser_page.py - 瀏覽器分析介面
顯示 Chrome 瀏覽器中各網站的使用時長紀錄。
"""

from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.analyzer import UsageAnalyzer
from ui.charts import TimelineChart, UsageBarChart, HourlyChart, TrendChart
from ui.dashboard_page import StatCard, PeriodButton


class BrowserPage(QWidget):
    """瀏覽器分析介面 - 專門顯示各網站的使用狀況"""

    website_clicked = pyqtSignal(str)  # 點擊某網站，跳轉到分析頁面
    detail_requested = pyqtSignal(str) # 'app' or 'browser'

    def __init__(self, analyzer: UsageAnalyzer, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer
        self.current_period = 'daily'
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ─── 標題區 ───
        header = QHBoxLayout()
        title = QLabel("🌐 瀏覽器網站分析")
        title.setStyleSheet("color: #000000; font-size: 22px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        # 時間週期切換
        self.period_group = QButtonGroup(self)
        self.period_group.setExclusive(True)

        btn_daily = PeriodButton("今日", "daily")
        btn_weekly = PeriodButton("本週", "weekly")
        btn_monthly = PeriodButton("本月", "monthly")

        btn_daily.setChecked(True)

        for btn in [btn_daily, btn_weekly, btn_monthly]:
            self.period_group.addButton(btn)
            header.addWidget(btn)
            btn.clicked.connect(lambda checked, b=btn: self._on_period_change(b))

        layout.addLayout(header)

        # ─── 統計卡片區 ───
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_total = StatCard("瀏覽總時長 (點擊查看全部)", clickable=True)
        self.card_sites = StatCard("瀏覽網站數")
        self.card_top = StatCard("最常造訪網站")

        self.card_total.clicked.connect(lambda: self.detail_requested.emit('browser'))

        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_sites)
        cards_layout.addWidget(self.card_top)

        layout.addLayout(cards_layout)

        # ─── 滾動區域 ───
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical {
                background: #D7F5F2; width: 8px; border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #B9FBC0; border-radius: 4px; min-height: 30px;
            }
        """)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)

        # ─── 瀏覽趨勢 ───
        section_trend = QLabel("📈 瀏覽時間趨勢")
        section_trend.setStyleSheet(
            "color: #000000; font-size: 16px; font-weight: bold; margin-top: 8px;"
        )
        scroll_layout.addWidget(section_trend)

        self.trend_chart = TrendChart(width=12, height=3)
        self.trend_chart.setMinimumHeight(200)
        scroll_layout.addWidget(self.trend_chart)

        # ─── 網站排行 ───
        section_ranking = QLabel("🏆 網站造訪排行")
        section_ranking.setStyleSheet(
            "color: #000000; font-size: 16px; font-weight: bold; margin-top: 8px;"
        )
        scroll_layout.addWidget(section_ranking)

        self.ranking_chart = UsageBarChart(width=12, height=5)
        self.ranking_chart.setMinimumHeight(400)
        scroll_layout.addWidget(self.ranking_chart)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def _on_period_change(self, btn: PeriodButton):
        """切換時間週期"""
        self.current_period = btn.period
        # 更新所有按鈕樣式
        for b in self.period_group.buttons():
            b._update_style(b == btn)
        self.refresh_data()

    def refresh_data(self):
        """重新載入並顯示資料"""
        try:
            # 根據週期取得時間範圍
            if self.current_period == 'daily':
                start, end = self.analyzer.get_today_range()
                days = 7
            elif self.current_period == 'weekly':
                start, end = self.analyzer.get_week_range()
                days = 7
            else:
                start, end = self.analyzer.get_month_range()
                days = 30

            # 取得瀏覽器各網站排行（從 window_title 或 url 細分）
            rankings = self.analyzer.get_browser_site_rankings(start, end)
            total = sum(r['total_seconds'] for r in rankings)

            # 更新統計卡片
            self.card_total.set_value(self.analyzer.format_duration(total))
            self.card_sites.set_value(str(len(rankings)))
            if rankings:
                self.card_top.set_value(rankings[0]['app_name'])
            else:
                self.card_top.set_value("—")

            # 更新排行圖 (限制前五個)
            self.ranking_chart.update_chart(rankings, max_items=5)

            # 更新趨勢圖 (僅顯示瀏覽器類型)
            trend = self.analyzer.get_daily_trend(days, app_type='browser')
            self.trend_chart.update_chart(trend)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Browser dashboard refresh error: {e}")
