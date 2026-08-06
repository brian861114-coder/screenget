"""
widgets.py - 共用 UI 元件（空狀態、載入、麵包屑、區塊標題）
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.i18n import t
from ui.theme import (
    SURFACE, TEXT, TEXT_MUTED, TEXT_HINT, BORDER, ACCENT_SOFT,
    CARD_STYLE, HINT_STYLE, PRIMARY_BTN, SECTION_LABEL_STYLE, sp,
)


class SectionHeader(QWidget):
    """區塊標題 + 可選提示"""

    def __init__(self, title: str, hint: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 4)
        layout.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(SECTION_LABEL_STYLE)
        layout.addWidget(self.title_label)
        self.hint_label = QLabel(hint)
        self.hint_label.setStyleSheet(HINT_STYLE)
        self.hint_label.setVisible(bool(hint))
        layout.addWidget(self.hint_label)

    def set_title(self, title: str):
        self.title_label.setText(title)

    def set_hint(self, hint: str):
        self.hint_label.setText(hint)
        self.hint_label.setVisible(bool(hint))


class BreadcrumbBar(QWidget):
    """麵包屑導航：總覽 > 詳情"""

    crumb_clicked = pyqtSignal(int)  # index in crumbs

    def __init__(self, parent=None):
        super().__init__(parent)
        self._crumbs = []
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 8)
        self.layout.setSpacing(6)
        self.setVisible(False)

    def set_crumbs(self, crumbs: list):
        """crumbs: list of str labels；最後一項為目前頁（不可點）"""
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._crumbs = crumbs or []
        if len(self._crumbs) < 2:
            self.setVisible(False)
            return

        self.setVisible(True)
        for i, label in enumerate(self._crumbs):
            if i > 0:
                sep = QLabel("›")
                sep.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
                self.layout.addWidget(sep)

            if i < len(self._crumbs) - 1:
                btn = QPushButton(label)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFlat(True)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        color: #3A7CA5; background: transparent; border: none;
                        font-size: 13px; font-weight: bold; padding: 0;
                        text-decoration: underline;
                    }}
                    QPushButton:hover {{ color: #1F5A80; }}
                """)
                btn.clicked.connect(lambda checked=False, idx=i: self.crumb_clicked.emit(idx))
                self.layout.addWidget(btn)
            else:
                cur = QLabel(label)
                cur.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: bold;")
                self.layout.addWidget(cur)

        self.layout.addStretch()


class EmptyState(QFrame):
    """空狀態區塊"""

    action_clicked = pyqtSignal()

    def __init__(self, title: str = "", body: str = "", action: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("emptyState")
        self.setStyleSheet(f"""
            #emptyState {{
                background-color: {SURFACE};
                border: 1px dashed {BORDER};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 36, 32, 36)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon = QLabel("")
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setStyleSheet("font-size: 36px; border: none;")
        self.icon.hide()
        layout.addWidget(self.icon)

        self.title_label = QLabel(title or t("empty_title"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: bold; border: none;")
        layout.addWidget(self.title_label)

        self.body_label = QLabel(body or t("empty_body"))
        self.body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body_label.setWordWrap(True)
        self.body_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px; border: none;")
        layout.addWidget(self.body_label)

        self.action_btn = QPushButton(action or t("empty_action"))
        self.action_btn.setStyleSheet(PRIMARY_BTN)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.setVisible(bool(action) or True)
        self.action_btn.clicked.connect(self.action_clicked.emit)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.action_btn)
        row.addStretch()
        layout.addLayout(row)

    def configure(self, title: str = "", body: str = "", action: str = "", show_action: bool = True):
        self.title_label.setText(title or t("empty_title"))
        self.body_label.setText(body or t("empty_body"))
        self.action_btn.setText(action or t("empty_action"))
        self.action_btn.setVisible(show_action)


class LoadingOverlay(QFrame):
    """輕量載入提示（蓋在內容上方）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        self.setStyleSheet(f"""
            #loadingOverlay {{
                background-color: rgba(215, 245, 242, 180);
                border: none;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label = QLabel(t("loading"))
        self.label.setStyleSheet(f"""
            color: {TEXT}; font-size: 14px; font-weight: bold;
            background: {SURFACE}; border: 1px solid {BORDER};
            border-radius: 10px; padding: 12px 20px;
        """)
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.hide()

    def show_loading(self, text: str = None):
        self.label.setText(text or t("loading"))
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.raise_()
        self.show()

    def hide_loading(self):
        self.hide()

    def apply_language(self):
        self.label.setText(t("loading"))


class StatCard(QFrame):
    """統計卡片"""
    clicked = pyqtSignal()

    def __init__(self, title: str, value: str = "0", clickable: bool = False, parent=None):
        super().__init__(parent)
        self.clickable = clickable
        self.setObjectName("statCard")
        self._apply_style()
        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(self.title_label)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            f"color: {TEXT}; font-size: 24px; font-weight: bold;"
        )
        layout.addWidget(self.value_label)

        if clickable:
            self.hint = QLabel(t("click_hint"))
            self.hint.setStyleSheet(HINT_STYLE)
            layout.addWidget(self.hint)
        else:
            self.hint = None

    def _apply_style(self):
        border = ACCENT_SOFT if self.clickable else BORDER
        self.setStyleSheet(f"""
            #statCard {{
                background-color: {SURFACE};
                border-radius: 12px;
                border: 1px solid {border};
            }}
            #statCard:hover {{
                background-color: #F7FFFE;
                border: 1px solid {ACCENT_SOFT};
            }}
        """)

    def mousePressEvent(self, event):
        if self.clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_value(self, value: str):
        self.value_label.setText(value)

    def set_title(self, title: str):
        self.title_label.setText(title)

    def apply_language(self):
        if self.hint:
            self.hint.setText(t("click_hint"))


class UnitSwitcher(QWidget):
    """時長單位切換：自動 / 小時 / 分鐘"""

    changed = pyqtSignal(str)

    def __init__(self, initial: str = "auto", parent=None):
        super().__init__(parent)
        self.current = initial if initial in ("auto", "hours", "minutes") else "auto"
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.lbl = QLabel(t("unit_label"))
        self.lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(self.lbl)

        self.buttons = {}
        for key, text_key in (
            ("auto", "unit_auto"),
            ("hours", "unit_hours"),
            ("minutes", "unit_minutes"),
        ):
            btn = QPushButton(t(text_key))
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(32)
            btn.clicked.connect(lambda checked, k=key: self._select(k))
            layout.addWidget(btn)
            self.buttons[key] = btn
        self._refresh_styles()

    def _select(self, unit: str):
        if unit == self.current:
            self._refresh_styles()
            return
        self.current = unit
        self._refresh_styles()
        self.changed.emit(unit)

    def set_unit(self, unit: str, emit: bool = False):
        if unit not in self.buttons:
            unit = "auto"
        self.current = unit
        self._refresh_styles()
        if emit:
            self.changed.emit(unit)

    def _refresh_styles(self):
        size = sp(12)
        for key, btn in self.buttons.items():
            checked = key == self.current
            btn.setChecked(checked)
            if checked:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #A2D2FF; color: #000000; border: none;
                        border-radius: 6px; font-size: {size}px; font-weight: bold;
                        padding: 4px 10px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #FFFFFF; color: #445566;
                        border: 1px solid #B9FBC0; border-radius: 6px;
                        font-size: {size}px; padding: 4px 10px;
                    }}
                    QPushButton:hover {{ background-color: #F0F8FF; color: #000000; }}
                """)

    def apply_language(self):
        self.lbl.setText(t("unit_label"))
        self.lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: {sp(12)}px;")
        self.buttons["auto"].setText(t("unit_auto"))
        self.buttons["hours"].setText(t("unit_hours"))
        self.buttons["minutes"].setText(t("unit_minutes"))
        self._refresh_styles()


class CredibilityBadge(QLabel):
    """可信度標籤：精確 / 混合 / 估計"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = ""
        self.setVisible(False)

    def set_level(self, level: str, percent: int = None):
        self._level = level or ""
        if not level:
            self.setVisible(False)
            return
        if level == "exact":
            text = t("precision_exact")
            bg, fg = "#E6F6EA", "#2D5A27"
        elif level == "mixed":
            text = t("precision_mixed")
            bg, fg = "#FFF4E0", "#8A5A12"
        else:
            text = t("precision_estimated")
            bg, fg = "#EEF2F6", "#445566"
        if percent is not None:
            text = f"{text} · {percent}%"
        self.setText(text)
        self.setStyleSheet(
            f"color: {fg}; font-size: 12px; padding: 4px 10px; "
            f"background: {bg}; border-radius: 4px;"
        )
        self.setVisible(True)

    def apply_language(self):
        if self._level:
            # percent unknown on re-apply; keep level only
            self.set_level(self._level)
