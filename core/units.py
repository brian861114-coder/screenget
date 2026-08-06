"""
units.py - 時長單位格式與圖表刻度
"""

from typing import Tuple

# auto | hours | minutes
DURATION_UNITS = ("auto", "hours", "minutes")


def normalize_unit(unit: str) -> str:
    if unit in DURATION_UNITS:
        return unit
    return "auto"


def format_duration(seconds: float, unit: str = "auto") -> str:
    """依單位偏好格式化秒數。"""
    if seconds is None or seconds < 0:
        seconds = 0
    unit = normalize_unit(unit)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if unit == "hours":
        # 以小時為主：>=1h 用 Xh Ym，否則用小數小時
        if hours > 0:
            return f"{hours}h {minutes}m" if minutes else f"{hours}h"
        if minutes > 0 or secs > 0:
            return f"{seconds / 3600:.2f}h"
        return "0h"

    if unit == "minutes":
        total_min = seconds / 60.0
        if total_min >= 100:
            return f"{total_min:.0f}m"
        if total_min >= 10:
            return f"{total_min:.1f}m"
        if total_min >= 1:
            return f"{total_min:.1f}m"
        return f"{secs}s"

    # auto：可讀的 h / m / s
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def resolve_chart_scale(max_seconds: float, unit: str = "auto") -> Tuple[float, str]:
    """
    回傳 (除數, 軸標 i18n key)。
    長時段自動改用小時，避免分鐘軸難讀。
    """
    unit = normalize_unit(unit)
    max_seconds = max(0.0, float(max_seconds or 0))
    if unit == "hours" or (unit == "auto" and max_seconds >= 3600):
        return 3600.0, "chart_hours"
    return 60.0, "chart_minutes"


def credibility_from_ratio(url_seconds: float, total_seconds: float) -> str:
    """exact / mixed / estimated"""
    if total_seconds <= 0:
        return "estimated"
    ratio = url_seconds / total_seconds
    if ratio >= 0.7:
        return "exact"
    if ratio > 0:
        return "mixed"
    return "estimated"
