"""
charts.py - 圖表元件（可點擊 + 統一配色 + 單位刻度）
"""

import matplotlib
matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import timedelta
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import platform

from PyQt6.QtCore import pyqtSignal

if platform.system() == "Windows":
    plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "SimHei", "Arial"]
else:
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

from core.i18n import t
from core.units import resolve_chart_scale
from ui.theme import BG, SURFACE, TEXT, BORDER, ACCENT, CHART_COLORS, sp

DARK_BG = BG
DARK_SURFACE = SURFACE
DARK_TEXT = TEXT
DARK_GRID = BORDER
ACCENT_COLORS = CHART_COLORS


def get_color_for_app(app_name: str, app_list: List[str] = None) -> str:
    if app_list:
        try:
            idx = app_list.index(app_name) % len(ACCENT_COLORS)
            return ACCENT_COLORS[idx]
        except ValueError:
            pass
    idx = abs(hash(app_name)) % len(ACCENT_COLORS)
    return ACCENT_COLORS[idx]


def _cred_suffix(cred: str) -> str:
    if cred == "exact":
        return f" ·{t('cred_short_exact')}"
    if cred == "mixed":
        return f" ·{t('cred_short_mixed')}"
    if cred == "estimated":
        return f" ·{t('cred_short_est')}"
    return ""


def _tick_size() -> int:
    return sp(8)


def _label_size() -> int:
    return sp(10)


def _body_size() -> int:
    return sp(9)


def _empty_size() -> int:
    return sp(14)


class TimelineChart(FigureCanvas):
    def __init__(self, parent=None, width=10, height=3):
        self.fig = Figure(figsize=(width, height), facecolor=DARK_BG)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self._setup_style()

    def __del__(self):
        """釋放 matplotlib 資源"""
        plt.close(self.fig)

    def _setup_style(self):
        self.ax.set_facecolor(DARK_SURFACE)
        self.ax.tick_params(colors=DARK_TEXT, labelsize=_tick_size())
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["bottom"].set_color(DARK_GRID)
        self.ax.spines["left"].set_color(DARK_GRID)

    def update_chart(self, time_blocks: List[Dict[str, Any]], target_date=None, unit: str = "auto"):
        self.ax.clear()
        self._setup_style()

        if not time_blocks:
            self.ax.text(
                0.5, 0.5, t("no_data"), transform=self.ax.transAxes,
                ha="center", va="center", color=DARK_TEXT, fontsize=_empty_size(),
            )
            self.draw_idle()
            return

        app_totals: Dict[str, float] = {}
        for block in time_blocks:
            name = block["app_name"]
            dur = (block["end"] - block["start"]).total_seconds()
            app_totals[name] = app_totals.get(name, 0) + dur
        apps = sorted(app_totals.keys(), key=lambda a: app_totals[a], reverse=True)

        hourly_per_app: Dict[str, list] = {app: [0.0] * 24 for app in apps}
        for block in time_blocks:
            app_name = block["app_name"]
            current = block["start"]
            end = block["end"]
            while current < end:
                hour = current.hour
                next_hour = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                slice_end = min(next_hour, end)
                hourly_per_app[app_name][hour] += (slice_end - current).total_seconds()
                current = slice_end

        max_stack = max(
            (sum(hourly_per_app[app][h] for app in apps) for h in range(24)),
            default=0,
        )
        divisor, axis_key = resolve_chart_scale(max_stack, unit)

        hours = list(range(24))
        bottoms = [0.0] * 24
        for app_name in apps:
            values = [v / divisor for v in hourly_per_app[app_name]]
            color = get_color_for_app(app_name, apps)
            self.ax.bar(
                hours, values, bottom=bottoms, color=color,
                alpha=0.88, edgecolor="none", width=0.85, label=app_name,
            )
            bottoms = [bottoms[i] + values[i] for i in range(24)]

        self.ax.set_xticks(hours)
        self.ax.set_xticklabels([f"{h:02d}" for h in hours], fontsize=_tick_size(), color=DARK_TEXT)
        self.ax.set_xlabel(t("chart_hour"), color=DARK_TEXT, fontsize=_label_size())
        self.ax.set_ylabel(t(axis_key), color=DARK_TEXT, fontsize=_label_size())
        self.ax.set_xlim(-0.5, 23.5)
        self.ax.grid(axis="y", color=DARK_GRID, alpha=0.3, linestyle="--")

        if apps:
            self.ax.legend(
                loc="upper left", bbox_to_anchor=(1.01, 1), borderaxespad=0,
                fontsize=_tick_size(), frameon=False, labelcolor=DARK_TEXT,
            )
        self.fig.tight_layout(pad=1.5)
        self.draw_idle()

    def update_weekly_monthly_chart(self, data: List[Dict[str, Any]]):
        """更新週/月統計圖，X 軸為日期或週別，Y 軸為小時總量"""
        self.ax.clear()
        self._setup_style()

        if not data:
            self.ax.text(0.5, 0.5, '暫無資料', transform=self.ax.transAxes,
                        ha='center', va='center', color=DARK_TEXT, fontsize=14)
            self.draw()
            return

        labels = [d['label'] for d in data]
        
        # 取得所有 app 名稱以便著色 (排除白名單已在 analyzer 處理)
        all_apps = set()
        for d in data:
            all_apps.update(d['app_usage'].keys())
        apps = sorted(list(all_apps), key=lambda a: sum(d['app_usage'].get(a, 0) for d in data), reverse=True)

        # 繪製堆疊圖 (縱軸為小時)
        bottoms = [0.0] * len(data)
        for app_name in apps:
            # 轉換為小時
            values = [d['app_usage'].get(app_name, 0) / 3600.0 for d in data]
            color = get_color_for_app(app_name, apps)
            self.ax.bar(range(len(labels)), values, bottom=bottoms, color=color,
                       alpha=0.85, edgecolor='none', width=0.6, label=app_name)
            bottoms = [bottoms[i] + values[i] for i in range(len(data))]

        self.ax.set_xticks(range(len(labels)))
        self.ax.set_xticklabels(labels, fontsize=9, color=DARK_TEXT)
        self.ax.set_ylabel('使用時長 (小時)', color=DARK_TEXT, fontsize=10)
        self.ax.grid(axis='y', color=DARK_GRID, alpha=0.3, linestyle='--')
        
        # 設定 Y 軸下限為 0
        self.ax.set_ylim(bottom=0)
        
        # 圖例放右側 (與今日視圖一致)
        if apps:
            self.ax.legend(
                loc='upper left', bbox_to_anchor=(1.01, 1), borderaxespad=0,
                fontsize=8, frameon=False, labelcolor=DARK_TEXT
            )

        self.fig.tight_layout(pad=1.5)
        self.draw()


class UsageBarChart(FigureCanvas):
    """可點擊的橫向排行圖"""

    item_clicked = pyqtSignal(str)

    def __init__(self, parent=None, width=10, height=5):
        self.fig = Figure(figsize=(width, height), facecolor=DARK_BG)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self._names: List[str] = []
        self._bars = None
        self._cid = self.mpl_connect("button_press_event", self._on_click)
        self._setup_style()

    def __del__(self):
        """釋放 matplotlib 資源"""
        plt.close(self.fig)

    def _setup_style(self):
        self.ax.set_facecolor(DARK_SURFACE)
        self.ax.tick_params(colors=DARK_TEXT, labelsize=_body_size())
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["bottom"].set_color(DARK_GRID)
        self.ax.spines["left"].set_color(DARK_GRID)

    def update_chart(self, rankings: List[Dict[str, Any]], max_items: int = 10, unit: str = "auto"):
        self.ax.clear()
        self._setup_style()
        self._names = []
        self._bars = None

        if not rankings:
            self.ax.text(
                0.5, 0.5, t("no_data"), transform=self.ax.transAxes,
                ha="center", va="center", color=DARK_TEXT, fontsize=_empty_size(),
            )
            self.draw_idle()
            return

        data = rankings[:max_items]
        data.reverse()
        self._names = [d["app_name"] for d in data]
        labels = [
            f"{d['app_name']}{_cred_suffix(d.get('credibility', ''))}"
            for d in data
        ]
        max_secs = max((d["total_seconds"] for d in data), default=0)
        divisor, axis_key = resolve_chart_scale(max_secs, unit)
        values = [d["total_seconds"] / divisor for d in data]
        colors = [get_color_for_app(n) for n in self._names]

        self._bars = self.ax.barh(
            range(len(self._names)), values, color=colors,
            alpha=0.88, height=0.6, edgecolor="none", picker=True,
        )
        self.ax.set_yticks(range(len(self._names)))
        self.ax.set_yticklabels(labels, fontsize=_body_size(), color=DARK_TEXT)
        self.ax.set_xlabel(t(axis_key), color=DARK_TEXT, fontsize=_label_size())

        pad = (max(values) * 0.01) if values else 0.5
        for bar, d in zip(self._bars, data):
            self.ax.text(
                bar.get_width() + pad,
                bar.get_y() + bar.get_height() / 2,
                d["formatted_time"], va="center",
                color=DARK_TEXT, fontsize=_tick_size(), fontweight="bold",
            )

        self.ax.grid(axis="x", color=DARK_GRID, alpha=0.3, linestyle="--")
        self.fig.tight_layout(pad=1.5)
        self.draw_idle()

    def _on_click(self, event):
        if event.inaxes != self.ax or not self._bars or not self._names:
            return
        if event.ydata is None:
            return
        idx = int(round(event.ydata))
        if 0 <= idx < len(self._names):
            self.item_clicked.emit(self._names[idx])


class HourlyChart(FigureCanvas):
    def __init__(self, parent=None, width=10, height=3):
        self.fig = Figure(figsize=(width, height), facecolor=DARK_BG)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self._setup_style()

    def __del__(self):
        """釋放 matplotlib 資源"""
        plt.close(self.fig)

    def _setup_style(self):
        self.ax.set_facecolor(DARK_SURFACE)
        self.ax.tick_params(colors=DARK_TEXT, labelsize=_tick_size())
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["bottom"].set_color(DARK_GRID)
        self.ax.spines["left"].set_color(DARK_GRID)

    def update_chart(self, hourly_data: Dict[int, float], unit: str = "auto"):
        self.ax.clear()
        self._setup_style()
        hours = list(range(24))
        max_secs = max((hourly_data.get(h, 0) for h in hours), default=0)
        divisor, axis_key = resolve_chart_scale(max_secs, unit)
        values = [hourly_data.get(h, 0) / divisor for h in hours]
        colors = [ACCENT if v > 0 else DARK_GRID for v in values]
        self.ax.bar(hours, values, color=colors, alpha=0.88, edgecolor="none", width=0.8)
        self.ax.set_xticks(hours)
        self.ax.set_xticklabels([f"{h:02d}" for h in hours], fontsize=_tick_size(), color=DARK_TEXT)
        self.ax.set_xlabel(t("chart_hour"), color=DARK_TEXT, fontsize=_label_size())
        self.ax.set_ylabel(t(axis_key), color=DARK_TEXT, fontsize=_label_size())
        self.ax.grid(axis="y", color=DARK_GRID, alpha=0.3, linestyle="--")
        self.fig.tight_layout(pad=1.5)
        self.draw_idle()


class TrendChart(FigureCanvas):
    def __init__(self, parent=None, width=10, height=3):
        self.fig = Figure(figsize=(width, height), facecolor=DARK_BG)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self._setup_style()

    def __del__(self):
        """釋放 matplotlib 資源"""
        plt.close(self.fig)

    def _setup_style(self):
        self.ax.set_facecolor(DARK_SURFACE)
        self.ax.tick_params(colors=DARK_TEXT, labelsize=_tick_size())
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["bottom"].set_color(DARK_GRID)
        self.ax.spines["left"].set_color(DARK_GRID)

    def update_chart(self, trend_data: List[Dict[str, Any]], unit: str = "auto"):
        self.ax.clear()
        self._setup_style()
        if not trend_data:
            self.ax.text(
                0.5, 0.5, t("no_data"), transform=self.ax.transAxes,
                ha="center", va="center", color=DARK_TEXT, fontsize=_empty_size(),
            )
            self.draw_idle()
            return

        dates = [d["date_str"] for d in trend_data]
        max_secs = max((d["total_seconds"] for d in trend_data), default=0)
        divisor, axis_key = resolve_chart_scale(max_secs, unit)
        short_key = "chart_hours_short" if divisor >= 3600 else "chart_minutes_short"
        values = [d["total_seconds"] / divisor for d in trend_data]
        self.ax.plot(
            dates, values, color=ACCENT, linewidth=2,
            marker="o", markersize=6, markerfacecolor=ACCENT,
            markeredgecolor=ACCENT, markeredgewidth=1.2,
        )
        self.ax.fill_between(dates, values, alpha=0.12, color=ACCENT)
        self.ax.set_xlabel(t("chart_date"), color=DARK_TEXT, fontsize=_label_size())
        self.ax.set_ylabel(t(short_key), color=DARK_TEXT, fontsize=_label_size())
        self.ax.grid(axis="y", color=DARK_GRID, alpha=0.3, linestyle="--")
        plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
        self.fig.tight_layout(pad=1.5)
        self.draw_idle()
