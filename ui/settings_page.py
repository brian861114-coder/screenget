"""
settings_page.py - 設定介面
提供語言切換、開機啟動與白名單管理。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QCheckBox, QListWidget, QPushButton, QLineEdit, QFrame,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from core.settings_manager import SettingsManager

class SettingsPage(QWidget):
    """設定頁面"""
    settings_changed = pyqtSignal()
    
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        # ─── 標題 ───
        title = QLabel("⚙️ 應用程式設定")
        title.setStyleSheet("color: #000000; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)
        
        # ─── 語言設定 ───
        lang_group = QFrame()
        lang_group.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; padding: 16px; border: 1px solid #B9FBC0;")
        lang_layout = QVBoxLayout(lang_group)
        
        lang_header = QLabel("🌐 語言設定 / Language")
        lang_header.setStyleSheet("font-weight: bold; border: none; font-size: 18px;")
        lang_layout.addWidget(lang_header)
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["繁體中文", "English", "日本語"])
        # 對應 zh_TW, en_US, ja_JP
        lang_map = {'zh_TW': 0, 'en_US': 1, 'ja_JP': 2}
        self.lang_combo.setCurrentIndex(lang_map.get(self.settings_manager.get_language(), 0))
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_layout.addWidget(self.lang_combo)
        
        layout.addWidget(lang_group)
        
        # ─── 自動執行 ───
        auto_group = QFrame()
        auto_group.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; padding: 16px; border: 1px solid #B9FBC0;")
        auto_layout = QVBoxLayout(auto_group)
        
        self.auto_check = QCheckBox("開機自動執行 ScreenGet")
        self.auto_check.setChecked(self.settings_manager.settings.get('autostart', False))
        self.auto_check.stateChanged.connect(self._on_autostart_changed)
        self.auto_check.setStyleSheet("font-weight: bold; border: none; font-size: 18px;")
        auto_layout.addWidget(self.auto_check)
        
        layout.addWidget(auto_group)
        
        # ─── 白名單 ───
        white_group = QFrame()
        white_group.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; padding: 16px; border: 1px solid #B9FBC0;")
        white_layout = QVBoxLayout(white_group)
        
        white_header = QLabel("🛡️ 數據排除白名單 (應用程式名稱或網域)")
        white_header.setStyleSheet("font-weight: bold; border: none; font-size: 18px;")
        white_layout.addWidget(white_header)
        
        white_desc = QLabel("加入列表的程式或網站將不會出現在統計圖表中。")
        white_desc.setStyleSheet("color: #666666; font-size: 11px; border: none;")
        white_layout.addWidget(white_desc)
        
        # 輸入區
        input_layout = QHBoxLayout()
        self.white_input = QLineEdit()
        self.white_input.setPlaceholderText("例如: chrome://newtab 或 Notepad")
        self.btn_add = QPushButton("加入")
        self.btn_add.clicked.connect(self._add_to_whitelist)
        self.btn_add.setStyleSheet("background-color: #A2D2FF; font-weight: bold; padding: 5px 15px;")
        input_layout.addWidget(self.white_input)
        input_layout.addWidget(self.btn_add)
        white_layout.addLayout(input_layout)
        
        # 列表區
        self.white_list = QListWidget()
        self.white_list.addItems(self.settings_manager.settings.get('whitelist', []))
        white_layout.addWidget(self.white_list)
        
        self.btn_remove = QPushButton("移除選中項目")
        self.btn_remove.clicked.connect(self._remove_from_whitelist)
        self.btn_remove.setStyleSheet("background-color: #FFB7B2; font-weight: bold; padding: 5px;")
        white_layout.addWidget(self.btn_remove)
        
        layout.addWidget(white_group)
        layout.addStretch()

    def _on_language_changed(self, index):
        langs = ['zh_TW', 'en_US', 'ja_JP']
        self.settings_manager.set_language(langs[index])
        QMessageBox.information(self, "設定已更新", "語言設定已更改，部分介面可能需要重啟程式才能完全生效。")

    def _on_autostart_changed(self, state):
        self.settings_manager.set_autostart(state == Qt.CheckState.Checked.value)

    def _add_to_whitelist(self):
        text = self.white_input.text().strip()
        if text:
            if text not in self.settings_manager.settings['whitelist']:
                self.settings_manager.add_to_whitelist(text)
                self.white_list.addItem(text)
                self.white_input.clear()
                self.settings_changed.emit()
            else:
                QMessageBox.warning(self, "提示", "該項目已在列表中。")

    def _remove_from_whitelist(self):
        current_item = self.white_list.currentItem()
        if current_item:
            name = current_item.text()
            self.settings_manager.remove_from_whitelist(name)
            self.white_list.takeItem(self.white_list.row(current_item))
            self.settings_changed.emit()
