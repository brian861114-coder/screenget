"""
dashboard_page.py - 展示介面（儀表板）
顯示當天/當周/當月各軟體的使用狀況。
"""

from datetime import date, datetime
from typing import List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QButtonGroup, QSizePolicy, QComboBox,
    QCalendarWidget, QDialog, QVBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QDate
from PyQt6.QtGui import QFont, QTextCharFormat, QColor

from core.analyzer import UsageAnalyzer
from ui.charts import TimelineChart, UsageBarChart, HourlyChart

class StatCard(QFrame):
    """統計卡片元件"""
    clicked = pyqtSignal()

    def __init__(self, title: str, value: str = "0", clickable: bool = False, parent=None):
        super().__init__(parent)
        self.clickable = clickable
        self.setObjectName("statCard")
        
        if self.clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setStyleSheet("""
                #statCard {
                    background-color: #FFFFFF;
                    border-radius: 12px;
                    border: 1px solid #B9FBC0;
                    padding: 16px;
                }
                #statCard:hover {
                    background-color: #F8FFF9;
                    border: 1px solid #A2D2FF;
                }
            """)
        else:
            self.setStyleSheet("""
                #statCard {
                    background-color: #FFFFFF;
                    border-radius: 12px;
                    border: 1px solid #B9FBC0;
                    padding: 16px;
                }
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #445566; font-size: 12px;")
        layout.addWidget(self.title_label)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            "color: #000000; font-size: 24px; font-weight: bold;"
        )
        layout.addWidget(self.value_label)

    def mousePressEvent(self, event):
        if self.clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_value(self, value: str):
        self.value_label.setText(value)


class PeriodButton(QPushButton):
    """時間週期切換按鈕"""

    def __init__(self, text: str, period: str, parent=None):
        super().__init__(text, parent)
        self.period = period
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(36)
        self.setMinimumWidth(80)
        self._update_style(False)

    def _update_style(self, checked: bool):
        if checked:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #A2D2FF;
                    color: #000000;
                    border: none;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 6px 16px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #445566;
                    border: 1px solid #B9FBC0;
                    border-radius: 8px;
                    font-size: 13px;
                    padding: 6px 16px;
                }
                QPushButton:hover {
                    background-color: #F0F8FF;
                    color: #000000;
                }
            """)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._update_style(checked)


class DashboardPage(QWidget):
    """展示介面 - 儀表板頁面"""

    app_clicked = pyqtSignal(str)  # 點擊某程式，跳轉到分析頁面
    detail_requested = pyqtSignal(str) # 'app' or 'browser'

    def __init__(self, analyzer: UsageAnalyzer, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer
        self.current_period = 'daily'
        self.target_date = date.today() # 當前查看的日期
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ─── 標題區 ───
        header = QHBoxLayout()
        title = QLabel("📊 使用狀況總覽")
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

        self.card_total = StatCard("總使用時長 (點擊查看全部)", clickable=True)
        self.card_apps = StatCard("使用程式數")
        self.card_top = StatCard("最常使用")

        self.card_total.clicked.connect(lambda: self.detail_requested.emit('app'))

        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_apps)
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

        # ─── 時間段圖表 ───
        timeline_header = QHBoxLayout()
        section_timeline = QLabel("🕐 使用時間段")
        section_timeline.setStyleSheet(
            "color: #000000; font-size: 16px; font-weight: bold; margin-top: 8px;"
        )
        timeline_header.addWidget(section_timeline)

        # 📅 選擇日期按鈕
        self.btn_date_picker = QPushButton("📅 選擇日期")
        self.btn_date_picker.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_date_picker.setStyleSheet("""
            QPushButton {
                background-color: #F0F8FF;
                color: #0078D7;
                border: 1px solid #A2D2FF;
                border-radius: 6px;
                padding: 2px 10px;
                font-size: 12px;
                margin-left: 10px;
                margin-top: 8px;
            }
            QPushButton:hover {
                background-color: #E1F0FF;
            }
        """)
        self.btn_date_picker.clicked.connect(self._show_date_picker)
        timeline_header.addWidget(self.btn_date_picker)
        
        timeline_header.addStretch()
        
        # 下拉式選單
        self.timeline_filter = QComboBox()
        self.timeline_filter.setMinimumWidth(200)
        self.timeline_filter.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #B9FBC0;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.timeline_filter.addItem("TOP 5 most used")
        self.timeline_filter.currentTextChanged.connect(self._on_timeline_filter_changed)
        timeline_header.addWidget(self.timeline_filter)
        
        scroll_layout.addLayout(timeline_header)

        self.timeline_chart = TimelineChart(width=12, height=4)
        self.timeline_chart.setMinimumHeight(250)
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

        # ─── 使用時長排行 ───
        section_ranking = QLabel("🏆 使用時長排行")
        section_ranking.setStyleSheet(
            "color: #000000; font-size: 16px; font-weight: bold; margin-top: 8px;"
        )
        scroll_layout.addWidget(section_ranking)

        self.ranking_chart = UsageBarChart(width=12, height=5)
        self.ranking_chart.setMinimumHeight(350)
        scroll_layout.addWidget(self.ranking_chart)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def _on_period_change(self, btn: PeriodButton):
        """切換時間週期"""
        self.current_period = btn.period
        
        # 只在今日視圖顯示日期選擇按鈕
        self.btn_date_picker.setVisible(btn.period == 'daily')
        
        # 每次切換回今日時，預設顯示當下日期
        if btn.period == 'daily':
            from datetime import date
            self.target_date = date.today()

        # 更新所有按鈕樣式
        for b in self.period_group.buttons():
            b._update_style(b == btn)
        self.refresh_data()

    def _on_timeline_filter_changed(self):
        """當下拉選單切換時"""
        if self.current_period == 'daily':
            self.refresh_data()

    def refresh_data(self):
        """重新載入並顯示資料"""
        try:
            # 根據週期取得時間範圍
            if self.current_period == 'daily':
                # 獲取指定日期的數據
                target_date = self.target_date
                start = datetime.combine(target_date, datetime.min.time())
                end = datetime.combine(target_date, datetime.max.time())
                
                # 更新標題顯示
                if target_date == date.today():
                    self.card_total.title_label.setText("今日總使用時長 (點擊查看全部)")
                else:
                    self.card_total.title_label.setText(f"{target_date.strftime('%Y-%m-%d')} 總使用時長")

                rankings = self.analyzer.get_app_rankings(start, end)
                total = self.analyzer.get_total_usage(start, end)
            elif self.current_period == 'weekly':
                start, end = self.analyzer.get_week_range()
                rankings = self.analyzer.get_weekly_rankings()
                total = self.analyzer.get_weekly_total()
            else:
                start, end = self.analyzer.get_month_range()
                rankings = self.analyzer.get_monthly_rankings()
                total = self.analyzer.get_monthly_total()

            # 更新統計卡片
            self.card_total.set_value(self.analyzer.format_duration(total))
            self.card_apps.set_value(str(len(rankings)))
            if rankings:
                self.card_top.set_value(rankings[0]['app_name'])
            else:
                self.card_top.set_value("—")

            # 更新排行圖
            self.ranking_chart.update_chart(rankings)

            # 更新時間段圖
            if self.current_period == 'daily':
                blocks = self.analyzer.get_time_blocks(start, end)
                
                # 更新下拉選單內容
                self._update_timeline_filter_list(rankings)

                selected_filter = self.timeline_filter.currentText()
                
                if selected_filter == "TOP 5 most used":
                    # 僅保留前五名的資料
                    top_5_names = [r['app_name'] for r in rankings[:5]]
                    filtered_blocks = [b for b in blocks if b['app_name'] in top_5_names]
                    self.timeline_chart.update_chart(filtered_blocks, target_date=target_date)
                else:
                    # 特定程式
                    filtered_blocks = [b for b in blocks if b['app_name'] == selected_filter]
                    self.timeline_chart.update_chart(filtered_blocks, target_date=date.today())
                
                # 恢復 24 小時圖表
                self.hourly_chart.setVisible(True)
                hourly = self.analyzer.get_hourly_usage(start, end)
                self.hourly_chart.update_chart(hourly)
            elif self.current_period == 'weekly':
                # 同步過濾器設定
                self._update_timeline_filter_list(rankings)
                selected_filter = self.timeline_filter.currentText()
                
                weekly_data = self.analyzer.get_weekly_daily_totals()
                
                # 過濾資料
                if selected_filter == "TOP 5 most used":
                    top_5_names = [r['app_name'] for r in rankings[:5]]
                    for day in weekly_data:
                        day['app_usage'] = {name: val for name, val in day['app_usage'].items() if name in top_5_names}
                elif selected_filter != "TOP 5 most used":
                    # 特定程式
                    for day in weekly_data:
                        day['app_usage'] = {name: val for name, val in day['app_usage'].items() if name == selected_filter}

                self.timeline_chart.update_weekly_monthly_chart(weekly_data)
                self.hourly_chart.update_chart({})
            elif self.current_period == 'monthly':
                # 同步過濾器設定
                self._update_timeline_filter_list(rankings)
                selected_filter = self.timeline_filter.currentText()
                
                monthly_data = self.analyzer.get_monthly_weekly_totals()
                
                # 過濾資料
                if selected_filter == "TOP 5 most used":
                    top_5_names = [r['app_name'] for r in rankings[:5]]
                    for week in monthly_data:
                        week['app_usage'] = {name: val for name, val in week['app_usage'].items() if name in top_5_names}
                elif selected_filter != "TOP 5 most used":
                    # 特定程式
                    for week in monthly_data:
                        week['app_usage'] = {name: val for name, val in week['app_usage'].items() if name == selected_filter}

                self.timeline_chart.update_weekly_monthly_chart(monthly_data)
                self.hourly_chart.update_chart({})
            else:
                self.timeline_chart.update_chart([])
                self.hourly_chart.update_chart({})

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Dashboard refresh error: {e}")

    def _show_date_picker(self):
        """顯示日期選擇對話框 - Style 1 現代極簡潮流風格"""
        dialog = QDialog(self)
        dialog.setWindowTitle("📆 選擇日期")
        dialog.setFixedWidth(420)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #D7F5F2; /* 主畫面背景色 */
                border-radius: 15px;
            }
        """)
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(20, 20, 20, 20)
        dialog_layout.setSpacing(15)

        # 獲取所有有數據的日期
        active_dates = self.analyzer.get_active_dates()
        active_qdates = [QDate(d.year, d.month, d.day) for d in active_dates]

        calendar = QCalendarWidget()
        calendar.setGridVisible(False) # 為了風格一致，關閉原生格線
        calendar.setNavigationBarVisible(True)
        calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader) # 隱藏週數
        
        # 🟢 Style 1 核心樣式設定
        calendar.setStyleSheet("""
            QCalendarWidget QAbstractItemView {
                background-color: white;
                border-radius: 10px;
                outline: 0;
                selection-background-color: #A2D2FF;
                selection-color: black;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #D7F5F2;
                min-height: 40px;
            }
            QCalendarWidget QToolButton {
                color: black;
                font-weight: bold;
                background-color: transparent;
                border-radius: 5px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #FFFFFF;
            }
        """)

        # 📅 設定日期格式 (Style 1: 統一黑色或灰色，不再有紅色六日)
        # 1. 準備格式
        active_format = QTextCharFormat()
        active_format.setForeground(QColor("#000000")) # 深黑色 (有數據)
        active_format.setFontWeight(QFont.Weight.Bold)

        dim_format = QTextCharFormat()
        dim_format.setForeground(QColor("#CCCCCC")) # 淺灰色 (無數據)
        
        # 🚀 關鍵：全面覆寫年度日期格式以消除六日紅色
        curr_year = calendar.selectedDate().year()
        year_start = QDate(curr_year, 1, 1)
        for i in range(366): # 涵蓋整年
            qd = year_start.addDays(i)
            # 轉換為 python date 物件以進行比較
            pyd = date(qd.year(), qd.month(), qd.day())
            if pyd in active_dates:
                calendar.setDateTextFormat(qd, active_format)
            else:
                calendar.setDateTextFormat(qd, dim_format)

        dialog_layout.addWidget(calendar)
        
        btn_confirm = QPushButton("確認選擇")
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setMinimumHeight(45)
        btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #A2D2FF;
                color: black;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #92C2EF;
                border: 1px solid #FFFFFF;
            }
        """)
        
        def on_confirm():
            selected_qdate = calendar.selectedDate()
            selected_date = date(selected_qdate.year(), selected_qdate.month(), selected_qdate.day())
            
            if selected_date in active_dates:
                self.target_date = selected_date
                self.refresh_data()
                dialog.accept()
            else:
                from PyQt6.QtWidgets import QMessageBox
                msg = QMessageBox(dialog)
                msg.setWindowTitle("提示")
                msg.setText("該日期沒有紀錄")
                msg.setInformativeText("請選擇深黑色的日期查看數據。")
                msg.setStyleSheet("QLabel{ min-width: 200px; color: black; }")
                msg.exec()

        btn_confirm.clicked.connect(on_confirm)
        dialog_layout.addWidget(btn_confirm)

        dialog.exec()

    def _update_timeline_filter_list(self, rankings: List[Dict[str, Any]]):
        """動態更新下拉選單中的程式名稱列表"""
        current_text = self.timeline_filter.currentText()
        
        # 暫時斷開信號以避免無限循環
        self.timeline_filter.blockSignals(True)
        self.timeline_filter.clear()
        self.timeline_filter.addItem("TOP 5 most used")
        
        # 加入所有有紀錄的程式
        app_names = sorted([r['app_name'] for r in rankings])
        self.timeline_filter.addItems(app_names)
        
        # 試著恢復原本的選取
        index = self.timeline_filter.findText(current_text)
        if index >= 0:
            self.timeline_filter.setCurrentIndex(index)
        else:
            self.timeline_filter.setCurrentIndex(0)
            
        self.timeline_filter.blockSignals(False)
