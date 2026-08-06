"""
theme.py - 共用視覺常數與樣式（視覺一致性 + 字級縮放）
"""

from typing import Dict

# 品牌色
BG = "#D7F5F2"
SURFACE = "#FFFFFF"
SURFACE_SOFT = "#F7FFFE"
TEXT = "#000000"
TEXT_MUTED = "#445566"
TEXT_HINT = "#667788"
ACCENT = "#5B9BD5"
ACCENT_SOFT = "#A2D2FF"
ACCENT_GREEN = "#B9FBC0"
ACCENT_GREEN_DARK = "#2D5A27"
BORDER = "#B9FBC0"
DANGER = "#E07A7A"
WARNING = "#C48A2A"

CHART_COLORS = [
    "#5B9BD5", "#7BC67E", "#E8C547", "#E89B8C",
    "#6CB4C9", "#A8C97A", "#E8B07A", "#D98A96",
    "#8FA3D4", "#6FAE8F", "#B0B8C0", "#7EB6C9",
]

# 字級：small / medium / large / xlarge
FONT_PRESETS: Dict[str, Dict[str, float]] = {
    "small": {"scale": 0.88, "pt": 10},
    "medium": {"scale": 1.0, "pt": 11},
    "large": {"scale": 1.15, "pt": 13},
    "xlarge": {"scale": 1.32, "pt": 15},
}

_font_preset = "medium"
_font_scale = 1.0
_font_pt = 11

SCROLL_STYLE = ""
CARD_STYLE = ""
SECTION_LABEL_STYLE = ""
HINT_STYLE = ""
PRIMARY_BTN = ""
SECONDARY_BTN = ""
DANGER_BTN = ""
INPUT_STYLE = ""


def sp(px: int) -> int:
    """依目前字級縮放像素字級。"""
    return max(9, int(round(px * _font_scale)))


def get_font_preset() -> str:
    return _font_preset


def get_font_pt() -> int:
    return _font_pt


def get_font_scale() -> float:
    return _font_scale


def set_font_preset(preset: str) -> str:
    """設定字級並刷新衍生樣式；回傳實際套用的 preset。"""
    global _font_preset, _font_scale, _font_pt
    if preset not in FONT_PRESETS:
        preset = "medium"
    _font_preset = preset
    _font_scale = FONT_PRESETS[preset]["scale"]
    _font_pt = int(FONT_PRESETS[preset]["pt"])
    _refresh_derived_styles()
    return _font_preset


def title_style() -> str:
    return f"color: {TEXT}; font-size: {sp(22)}px; font-weight: bold;"


def subtitle_style() -> str:
    return f"color: {TEXT_MUTED}; font-size: {sp(14)}px;"


def build_main_stylesheet() -> str:
    return f"""
    QMainWindow {{ background-color: {BG}; }}
    QWidget {{
        background-color: {BG}; color: {TEXT};
        font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif;
        font-size: {_font_pt}pt;
    }}
    QLabel {{ background-color: transparent; color: {TEXT}; }}
    QScrollArea {{ background-color: transparent; border: none; }}
"""


def _refresh_derived_styles():
    global SCROLL_STYLE, CARD_STYLE, SECTION_LABEL_STYLE, HINT_STYLE
    global PRIMARY_BTN, SECONDARY_BTN, DANGER_BTN, INPUT_STYLE

    SCROLL_STYLE = f"""
        QScrollArea {{ border: none; background-color: transparent; }}
        QScrollBar:vertical {{
            background: {BG}; width: 8px; border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {ACCENT_GREEN}; border-radius: 4px; min-height: 30px;
        }}
        QScrollBar:horizontal {{
            background: {BG}; height: 8px; border-radius: 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: {ACCENT_GREEN}; border-radius: 4px; min-width: 30px;
        }}
    """

    CARD_STYLE = f"""
        background-color: {SURFACE};
        border-radius: 12px;
        border: 1px solid {BORDER};
    """

    SECTION_LABEL_STYLE = f"""
        color: {TEXT}; font-size: {sp(16)}px; font-weight: bold; margin-top: 4px;
    """

    HINT_STYLE = f"""
        color: {TEXT_HINT}; font-size: {sp(11)}px; border: none;
    """

    PRIMARY_BTN = f"""
        QPushButton {{
            background-color: {ACCENT_SOFT}; color: {TEXT}; border: none;
            border-radius: 8px; padding: 8px 14px; font-weight: bold;
            font-size: {sp(13)}px;
        }}
        QPushButton:hover {{ background-color: #BDE4FF; }}
    """

    SECONDARY_BTN = f"""
        QPushButton {{
            background-color: {ACCENT_GREEN}; color: {TEXT}; border: none;
            border-radius: 8px; padding: 8px 14px; font-weight: bold;
            font-size: {sp(13)}px;
        }}
        QPushButton:hover {{ background-color: #C9FDD0; }}
    """

    DANGER_BTN = f"""
        QPushButton {{
            background-color: #FFB7B2; color: {TEXT}; border: none;
            border-radius: 8px; padding: 8px 14px; font-weight: bold;
            font-size: {sp(13)}px;
        }}
        QPushButton:hover {{ background-color: #FFC9C5; }}
    """

    INPUT_STYLE = f"""
        QLineEdit, QComboBox, QDateEdit, QSpinBox {{
            background-color: {SURFACE}; color: {TEXT};
            border: 1px solid {BORDER}; border-radius: 8px;
            padding: 6px 10px; font-size: {sp(13)}px;
        }}
        QComboBox::drop-down {{ border: none; width: 28px; }}
        QComboBox QAbstractItemView {{
            background: {SURFACE}; color: {TEXT};
            border: 1px solid {BORDER};
            selection-background-color: {ACCENT_SOFT};
            selection-color: {TEXT};
        }}
    """


set_font_preset("medium")
