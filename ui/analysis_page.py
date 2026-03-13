"""
analysis_page.py - 分析介面
顯示特定軟體當天/當周/當月的使用狀況。
"""

from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QScrollArea, QFrame, QButtonGroup
)
from PyQt6.QtCore import Qt

from core.analyzer import UsageAnalyzer
from ui.charts import TimelineChart, HourlyChart, TrendChart
from ui.dashboard_page import StatCard, PeriodButton


class AnalysisPage(QWidget):
    """分析介面 - 特定軟體使用狀況"""

    def __init__(self, analyzer: UsageAnalyzer, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer
        self.current_period = 'daily'
        self.current_app = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ─── 標題區 ───
        header = QHBoxLayout()
        title = QLabel("🔍 軟體使用分析")
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

        # ─── 軟體選擇 ───
        select_layout = QHBoxLayout()
        select_label = QLabel("選擇軟體：")
        select_label.setStyleSheet("color: #445566; font-size: 14px;")
        select_layout.addWidget(select_label)

        self.app_combo = QComboBox()
        self.app_combo.setMinimumWidth(250)
        self.app_combo.setMinimumHeight(36)
        self.app_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid #B9FBC0;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #445566;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid #B9FBC0;
                selection-background-color: #A2D2FF;
                selection-color: #000000;
            }
        """)
        self.app_combo.currentTextChanged.connect(self._on_app_change)
        select_layout.addWidget(self.app_combo)
        select_layout.addStretch()

        layout.addLayout(select_layout)

        # ─── 統計卡片 ───
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_daily = StatCard("今日使用時長")
        self.card_weekly = StatCard("本週使用時長")
        self.card_monthly = StatCard("本月使用時長")

        cards_layout.addWidget(self.card_daily)
        cards_layout.addWidget(self.card_weekly)
        cards_layout.addWidget(self.card_monthly)

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

        # ─── 時間段圖表 ───
        section_timeline = QLabel("🕐 使用時間段")
        section_timeline.setStyleSheet(
            "color: #000000; font-size: 16px; font-weight: bold; margin-top: 8px;"
        )
        scroll_layout.addWidget(section_timeline)

        self.timeline_chart = TimelineChart(width=12, height=3)
        self.timeline_chart.setMinimumHeight(200)
        scroll_layout.addWidget(self.timeline_chart)

        # ─── 24 小時分佈 ───
        section_hourly = QLabel("📈 24 小時使用分佈")
        section_hourly.setStyleSheet(
            "color: #000000; font-size: 16px; font-weight: bold; margin-top: 8px;"
        )
        scroll_layout.addWidget(section_hourly)

        self.hourly_chart = HourlyChart(width=12, height=3)
        self.hourly_chart.setMinimumHeight(200)
        scroll_layout.addWidget(self.hourly_chart)

        # ─── 使用趨勢 ───
        section_trend = QLabel("📉 使用趨勢 (過去 7 天)")
        section_trend.setStyleSheet(
            "color: #000000; font-size: 16px; font-weight: bold; margin-top: 8px;"
        )
        scroll_layout.addWidget(section_trend)

        self.trend_chart = TrendChart(width=12, height=3)
        self.trend_chart.setMinimumHeight(200)
        scroll_layout.addWidget(self.trend_chart)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def _on_period_change(self, btn: PeriodButton):
        """切換時間週期"""
        self.current_period = btn.period
        for b in self.period_group.buttons():
            b._update_style(b == btn)
        self.refresh_data()

    def _on_app_change(self, app_name: str):
        """切換選擇的軟體"""
        self.current_app = app_name if app_name else None
        self.refresh_data()

    def set_app(self, app_name: str):
        """從外部設定當前分析的軟體"""
        idx = self.app_combo.findText(app_name)
        if idx >= 0:
            self.app_combo.setCurrentIndex(idx)
        else:
            self.current_app = app_name
            self.refresh_data()

    def refresh_data(self):
        """重新載入並顯示資料"""
        try:
            # 更新程式下拉選單
            self._refresh_app_list()

            if not self.current_app:
                return

            app = self.current_app

            # 更新三個時段的統計卡片
            daily_total = self.analyzer.get_daily_total(app)
            weekly_total = self.analyzer.get_weekly_total(app)
            monthly_total = self.analyzer.get_monthly_total(app)

            self.card_daily.set_value(self.analyzer.format_duration(daily_total))
            self.card_weekly.set_value(self.analyzer.format_duration(weekly_total))
            self.card_monthly.set_value(self.analyzer.format_duration(monthly_total))

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

            # 更新時間段圖（僅日視圖）
            if self.current_period == 'daily':
                blocks = self.analyzer.get_time_blocks(start, end, app)
                self.timeline_chart.update_chart(blocks, target_date=date.today())

                hourly = self.analyzer.get_hourly_usage(start, end, app)
                self.hourly_chart.update_chart(hourly)
            else:
                self.timeline_chart.update_chart([])
                self.hourly_chart.update_chart({})

            # 更新趨勢圖
            trend = self.analyzer.get_daily_trend(days, app)
            self.trend_chart.update_chart(trend)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Analysis refresh error: {e}")

    def _refresh_app_list(self):
        """更新程式下拉選單"""
        # 取得近一個月使用過的所有程式
        start, end = self.analyzer.get_month_range()
        apps = self.analyzer.get_all_apps_in_range(start, end)

        current = self.app_combo.currentText()
        self.app_combo.blockSignals(True)
        self.app_combo.clear()
        for app in sorted(apps):
            self.app_combo.addItem(app)
        # 恢復之前的選擇
        if current:
            idx = self.app_combo.findText(current)
            if idx >= 0:
                self.app_combo.setCurrentIndex(idx)
        self.app_combo.blockSignals(False)

        if not self.current_app and apps:
            self.current_app = apps[0]
