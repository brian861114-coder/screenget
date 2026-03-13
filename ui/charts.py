"""
charts.py - 圖表元件
使用 matplotlib 嵌入 PyQt6，繪製使用時間段長條圖和排行圖。
"""

import matplotlib
matplotlib.use('QtAgg')

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch
from matplotlib.dates import DateFormatter, HourLocator
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np

# 淺色主題配色 (基於 #D7F5F2)
DARK_BG = '#D7F5F2'
DARK_SURFACE = '#FFFFFF'
DARK_TEXT = '#000000'
DARK_GRID = '#B9FBC0'
ACCENT_COLORS = [
    '#A2D2FF', '#B9FBC0', '#FFD700', '#FFB7B2',
    '#B2E2F2', '#E2F0CB', '#FFDAC1', '#FF9AA2',
    '#C7CEEA', '#97C1A9', '#DFE3E6', '#BDD9E4',
]


def get_color_for_app(app_name: str, app_list: List[str] = None) -> str:
    """取得程式對應的顏色"""
    if app_list:
        try:
            idx = app_list.index(app_name) % len(ACCENT_COLORS)
            return ACCENT_COLORS[idx]
        except ValueError:
            pass
    # 使用 hash 取得穩定的顏色
    idx = hash(app_name) % len(ACCENT_COLORS)
    return ACCENT_COLORS[idx]


class TimelineChart(FigureCanvas):
    """時間段長條圖 - 顯示一天中各時段的使用情況（Gantt-style）"""

    def __init__(self, parent=None, width=10, height=3):
        self.fig = Figure(figsize=(width, height), facecolor=DARK_BG)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self._setup_style()

    def _setup_style(self):
        self.ax.set_facecolor(DARK_SURFACE)
        self.ax.tick_params(colors=DARK_TEXT, labelsize=8)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_color(DARK_GRID)
        self.ax.spines['left'].set_color(DARK_GRID)

    def update_chart(self, time_blocks: List[Dict[str, Any]], target_date=None):
        """更新時間段圖表"""
        self.ax.clear()
        self._setup_style()

        if not time_blocks:
            self.ax.text(0.5, 0.5, '暫無資料', transform=self.ax.transAxes,
                        ha='center', va='center', color=DARK_TEXT, fontsize=14)
            self.draw()
            return

        # 取得所有不重複的 app
        apps = list(dict.fromkeys(b['app_name'] for b in time_blocks))

        for block in time_blocks:
            app_name = block['app_name']
            y_pos = apps.index(app_name)
            start = block['start']
            end = block['end']
            width = mdates.date2num(end) - mdates.date2num(start)
            color = get_color_for_app(app_name, apps)

            self.ax.barh(y_pos, width, left=mdates.date2num(start),
                        height=0.6, color=color, alpha=0.85,
                        edgecolor='none', linewidth=0)

        # 設定 Y 軸
        self.ax.set_yticks(range(len(apps)))
        self.ax.set_yticklabels(apps, fontsize=9, color=DARK_TEXT)

        # 設定 X 軸（時間）
        self.ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
        self.ax.xaxis.set_major_locator(HourLocator(interval=2))

        if target_date:
            start_of_day = datetime.combine(target_date, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)
            self.ax.set_xlim(mdates.date2num(start_of_day),
                           mdates.date2num(end_of_day))

        self.ax.grid(axis='x', color=DARK_GRID, alpha=0.3, linestyle='--')
        self.ax.set_xlabel('時間', color=DARK_TEXT, fontsize=10)
        self.fig.tight_layout(pad=1.5)
        self.draw()


class UsageBarChart(FigureCanvas):
    """使用時長橫向長條圖 - 顯示各程式的使用排行"""

    def __init__(self, parent=None, width=10, height=5):
        self.fig = Figure(figsize=(width, height), facecolor=DARK_BG)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self._setup_style()

    def _setup_style(self):
        self.ax.set_facecolor(DARK_SURFACE)
        self.ax.tick_params(colors=DARK_TEXT, labelsize=9)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_color(DARK_GRID)
        self.ax.spines['left'].set_color(DARK_GRID)

    def update_chart(self, rankings: List[Dict[str, Any]], max_items: int = 10):
        """更新排行圖表"""
        self.ax.clear()
        self._setup_style()

        if not rankings:
            self.ax.text(0.5, 0.5, '暫無資料', transform=self.ax.transAxes,
                        ha='center', va='center', color=DARK_TEXT, fontsize=14)
            self.draw()
            return

        # 限制顯示數量
        data = rankings[:max_items]
        data.reverse()  # 反轉讓最高的在最上面

        names = [d['app_name'] for d in data]
        values = [d['total_seconds'] / 60 for d in data]  # 轉換為分鐘
        colors = [get_color_for_app(n) for n in names]

        bars = self.ax.barh(range(len(names)), values, color=colors,
                           alpha=0.85, height=0.6, edgecolor='none')

        self.ax.set_yticks(range(len(names)))
        self.ax.set_yticklabels(names, fontsize=9, color=DARK_TEXT)
        self.ax.set_xlabel('使用時間 (分鐘)', color=DARK_TEXT, fontsize=10)

        # 在條形圖右側顯示時間
        for i, (bar, d) in enumerate(zip(bars, data)):
            self.ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                        d['formatted_time'], va='center',
                        color=DARK_TEXT, fontsize=8, fontweight='bold')

        self.ax.grid(axis='x', color=DARK_GRID, alpha=0.3, linestyle='--')
        self.fig.tight_layout(pad=1.5)
        self.draw()


class HourlyChart(FigureCanvas):
    """24 小時使用分佈圖"""

    def __init__(self, parent=None, width=10, height=3):
        self.fig = Figure(figsize=(width, height), facecolor=DARK_BG)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self._setup_style()

    def _setup_style(self):
        self.ax.set_facecolor(DARK_SURFACE)
        self.ax.tick_params(colors=DARK_TEXT, labelsize=8)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_color(DARK_GRID)
        self.ax.spines['left'].set_color(DARK_GRID)

    def update_chart(self, hourly_data: Dict[int, float]):
        """更新 24 小時分佈圖"""
        self.ax.clear()
        self._setup_style()

        hours = list(range(24))
        values = [hourly_data.get(h, 0) / 60 for h in hours]  # 轉換為分鐘

        colors = ['#00d2ff' if v > 0 else DARK_GRID for v in values]

        self.ax.bar(hours, values, color=colors, alpha=0.85,
                   edgecolor='none', width=0.8)

        self.ax.set_xticks(hours)
        self.ax.set_xticklabels([f'{h:02d}' for h in hours],
                                fontsize=7, color=DARK_TEXT)
        self.ax.set_xlabel('小時', color=DARK_TEXT, fontsize=10)
        self.ax.set_ylabel('分鐘', color=DARK_TEXT, fontsize=10)
        self.ax.grid(axis='y', color=DARK_GRID, alpha=0.3, linestyle='--')
        self.fig.tight_layout(pad=1.5)
        self.draw()


class TrendChart(FigureCanvas):
    """使用趨勢折線圖（過去 N 天）"""

    def __init__(self, parent=None, width=10, height=3):
        self.fig = Figure(figsize=(width, height), facecolor=DARK_BG)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self._setup_style()

    def _setup_style(self):
        self.ax.set_facecolor(DARK_SURFACE)
        self.ax.tick_params(colors=DARK_TEXT, labelsize=8)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_color(DARK_GRID)
        self.ax.spines['left'].set_color(DARK_GRID)

    def update_chart(self, trend_data: List[Dict[str, Any]]):
        """更新趨勢圖"""
        self.ax.clear()
        self._setup_style()

        if not trend_data:
            self.ax.text(0.5, 0.5, '暫無資料', transform=self.ax.transAxes,
                        ha='center', va='center', color=DARK_TEXT, fontsize=14)
            self.draw()
            return

        dates = [d['date_str'] for d in trend_data]
        values = [d['total_seconds'] / 60 for d in trend_data]  # 分鐘

        self.ax.plot(dates, values, color='#00d2ff', linewidth=2,
                    marker='o', markersize=6, markerfacecolor='#7b2ff7',
                    markeredgecolor='#00d2ff', markeredgewidth=1.5)

        # 填充面積
        self.ax.fill_between(dates, values, alpha=0.1, color='#00d2ff')

        self.ax.set_xlabel('日期', color=DARK_TEXT, fontsize=10)
        self.ax.set_ylabel('分鐘', color=DARK_TEXT, fontsize=10)
        self.ax.grid(axis='y', color=DARK_GRID, alpha=0.3, linestyle='--')

        plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        self.fig.tight_layout(pad=1.5)
        self.draw()
