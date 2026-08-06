"""
period_bar.py - 共用時間週期／日期選擇列
"""

from datetime import datetime, timedelta, date
from typing import Tuple

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QButtonGroup, QDateEdit, QFrame, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate

from core.i18n import t
from ui.theme import sp


class PeriodButton(QPushButton):
    """時間週期切換按鈕"""

    def __init__(self, text: str, period: str, parent=None):
        super().__init__(text, parent)
        self.period = period
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(36)
        self.setMinimumWidth(72)
        self._update_style(False)

    def _update_style(self, checked: bool):
        size = sp(13)
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #A2D2FF;
                    color: #000000;
                    border: none;
                    border-radius: 8px;
                    font-size: {size}px;
                    font-weight: bold;
                    padding: 6px 14px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #FFFFFF;
                    color: #445566;
                    border: 1px solid #B9FBC0;
                    border-radius: 8px;
                    font-size: {size}px;
                    padding: 6px 14px;
                }}
                QPushButton:hover {{
                    background-color: #F0F8FF;
                    color: #000000;
                }}
            """)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._update_style(checked)


class PeriodBar(QWidget):
    """今日／本週／本月／自訂日期區間"""

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_period = "daily"
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.period_group = QButtonGroup(self)
        self.period_group.setExclusive(True)

        self.btn_daily = PeriodButton(t("period_today"), "daily")
        self.btn_weekly = PeriodButton(t("period_week"), "weekly")
        self.btn_monthly = PeriodButton(t("period_month"), "monthly")
        self.btn_custom = PeriodButton(t("period_custom"), "custom")
        self.btn_daily.setChecked(True)

        for btn in (self.btn_daily, self.btn_weekly, self.btn_monthly, self.btn_custom):
            self.period_group.addButton(btn)
            layout.addWidget(btn)
            btn.clicked.connect(lambda checked, b=btn: self._on_period(b))

        self.custom_wrap = QFrame()
        custom_layout = QHBoxLayout(self.custom_wrap)
        custom_layout.setContentsMargins(8, 0, 0, 0)
        custom_layout.setSpacing(4)

        self.lbl_from = QLabel(t("date_from"))
        self.lbl_to = QLabel(t("date_to"))
        self.start_date = QDateEdit()
        self.end_date = QDateEdit()
        for w in (self.start_date, self.end_date):
            w.setCalendarPopup(True)
            w.setDisplayFormat("yyyy-MM-dd")
            w.setMinimumHeight(32)
            w.setStyleSheet("""
                QDateEdit {
                    background: #FFFFFF; border: 1px solid #B9FBC0;
                    border-radius: 6px; padding: 2px 8px;
                }
            """)
        self.start_date.setDate(QDate.currentDate().addDays(-6))
        self.end_date.setDate(QDate.currentDate())
        self.start_date.dateChanged.connect(self._on_custom_date)
        self.end_date.dateChanged.connect(self._on_custom_date)

        custom_layout.addWidget(self.lbl_from)
        custom_layout.addWidget(self.start_date)
        custom_layout.addWidget(self.lbl_to)
        custom_layout.addWidget(self.end_date)
        self.custom_wrap.setVisible(False)
        layout.addWidget(self.custom_wrap)

    def _on_period(self, btn: PeriodButton):
        self.current_period = btn.period
        for b in self.period_group.buttons():
            b._update_style(b == btn)
        self.custom_wrap.setVisible(self.current_period == "custom")
        self.changed.emit()

    def _on_custom_date(self, *_):
        if self.current_period == "custom":
            if self.start_date.date() > self.end_date.date():
                self.end_date.blockSignals(True)
                self.end_date.setDate(self.start_date.date())
                self.end_date.blockSignals(False)
            self.changed.emit()

    def set_period(self, period: str):
        mapping = {
            "daily": self.btn_daily,
            "weekly": self.btn_weekly,
            "monthly": self.btn_monthly,
            "custom": self.btn_custom,
        }
        btn = mapping.get(period, self.btn_daily)
        btn.setChecked(True)
        self._on_period(btn)

    def sync_from(self, other: "PeriodBar"):
        """從另一個 PeriodBar 複製狀態（詳情頁用）"""
        start, end, period = other.get_range()
        if period == "custom":
            self.set_custom_range(start.date(), (end - timedelta(days=1)).date())
        else:
            self.set_period(period)

    def set_custom_range(self, start: date, end: date):
        self.start_date.blockSignals(True)
        self.end_date.blockSignals(True)
        self.start_date.setDate(QDate(start.year, start.month, start.day))
        self.end_date.setDate(QDate(end.year, end.month, end.day))
        self.start_date.blockSignals(False)
        self.end_date.blockSignals(False)
        self.set_period("custom")

    def get_range(self) -> Tuple[datetime, datetime, str]:
        """回傳 (start, end, period)；end 為排他上界。"""
        today = date.today()
        period = self.current_period
        if period == "daily":
            start = datetime.combine(today, datetime.min.time())
            end = datetime.combine(today + timedelta(days=1), datetime.min.time())
        elif period == "weekly":
            monday = today - timedelta(days=today.weekday())
            start = datetime.combine(monday, datetime.min.time())
            end = datetime.combine(today + timedelta(days=1), datetime.min.time())
        elif period == "monthly":
            start = datetime.combine(today.replace(day=1), datetime.min.time())
            end = datetime.combine(today + timedelta(days=1), datetime.min.time())
        else:
            s = self.start_date.date().toPyDate()
            e = self.end_date.date().toPyDate()
            if e < s:
                e = s
            start = datetime.combine(s, datetime.min.time())
            end = datetime.combine(e + timedelta(days=1), datetime.min.time())
        return start, end, period

    def is_single_day(self) -> bool:
        start, end, _ = self.get_range()
        return (end - start) <= timedelta(days=1)

    def apply_language(self):
        self.btn_daily.setText(t("period_today"))
        self.btn_weekly.setText(t("period_week"))
        self.btn_monthly.setText(t("period_month"))
        self.btn_custom.setText(t("period_custom"))
        self.lbl_from.setText(t("date_from"))
        self.lbl_to.setText(t("date_to"))
        for b in self.period_group.buttons():
            b._update_style(b.isChecked())
