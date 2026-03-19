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
        # 使用 ScrollArea 包裹內容
        from PyQt6.QtWidgets import QScrollArea, QWidget
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        
        content_widget = QWidget()
        content_widget.setObjectName("ContentWidget")
        content_widget.setStyleSheet("#ContentWidget { background-color: transparent; }")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        # ─── 標題 ───
        title = QLabel("⚙️ 應用程式設定")
        title.setStyleSheet("color: #000000; font-size: 22px; font-weight: bold; border: none;")
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
        
        # ─── Chrome 外掛設定 ───
        chrome_group = QFrame()
        chrome_group.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; border: 1px solid #B9FBC0;")
        chrome_layout = QVBoxLayout(chrome_group)
        chrome_layout.setContentsMargins(16, 16, 16, 16)
        chrome_layout.setSpacing(6)
        
        chrome_header = QLabel("🧩 Chrome 擴充功能設定 (網頁追蹤)")
        chrome_header.setStyleSheet("font-weight: bold; font-size: 18px; color: #000000; border: none; margin-bottom: 5px;")
        chrome_layout.addWidget(chrome_header)
        
        import os
        from PyQt6.QtGui import QPixmap
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ext_path = os.path.join(base_dir, 'browser_extension')
            icon_dev_path = os.path.join(base_dir, '開發人員模式.png')
            icon_load_path = os.path.join(base_dir, '載入未封裝項目.png')
        except:
            ext_path = "專案資料夾內的 browser_extension 目錄"
            icon_dev_path = ""
            icon_load_path = ""

        def add_step(layout, text, icon_path=None):
            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(8)
            
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #000000; font-size: 13px; border: none;")
            lbl.setWordWrap(True)
            h_layout.addWidget(lbl)
            
            if icon_path and os.path.exists(icon_path):
                img_lbl = QLabel()
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaledToHeight(22, Qt.TransformationMode.SmoothTransformation)
                    img_lbl.setPixmap(scaled_pixmap)
                    img_lbl.setStyleSheet("border: none;")
                    h_layout.addWidget(img_lbl)
            
            h_layout.addStretch()
            layout.addLayout(h_layout)

        subtitle = QLabel("如何啟用 Chrome 網站追蹤功能：")
        subtitle.setStyleSheet("color: #000000; font-weight: bold; border: none; font-size: 14px; margin-top: 5px;")
        chrome_layout.addWidget(subtitle)
        
        add_step(chrome_layout, "1. 開啟 Chrome 瀏覽器，進入 [ chrome://extensions/ ]")
        add_step(chrome_layout, "2. 開啟右上角的「開發人員模式」。", icon_dev_path)
        add_step(chrome_layout, "3. 點擊「載入未封裝項目」。", icon_load_path)
        
        path_lbl = QLabel(f"4. 選擇以下目錄路徑：\n{ext_path}")
        path_lbl.setStyleSheet("""
            QLabel {
                color: #000000; 
                font-size: 12px; 
                border: 1px dashed #A2D2FF; 
                padding: 10px; 
                background-color: #F8FDFF;
                border-radius: 4px;
                margin: 5px 0px;
            }
        """)
        path_lbl.setWordWrap(True)
        path_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        chrome_layout.addWidget(path_lbl)
        
        add_step(chrome_layout, "5. 將外掛固定在工具列，即可開始追蹤造訪的網站網域。")
        
        btn_copy_ext = QPushButton("📋 複製擴充功能頁面網址")
        btn_copy_ext.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_ext.setStyleSheet("""
            QPushButton {
                background-color: #A2D2FF; 
                color: #000000;
                font-weight: bold; 
                border-radius: 6px;
                padding: 8px; 
                margin-top: 10px;
                border: none;
            }
            QPushButton:hover { background-color: #BDE4FF; }
        """)
        from PyQt6.QtWidgets import QApplication
        btn_copy_ext.clicked.connect(lambda: [
            QApplication.clipboard().setText("chrome://extensions/"), 
            QMessageBox.information(self, "提示", "網址已複製到剪貼簿。")
        ])
        chrome_layout.addWidget(btn_copy_ext)
        
        layout.addWidget(chrome_group)
        
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
        
        # 導出按鈕
        self.btn_export = QPushButton("📤 導出白名單 (複製到剪貼簿)")
        self.btn_export.clicked.connect(self._export_whitelist)
        self.btn_export.setStyleSheet("background-color: #B9FBC0; font-weight: bold; padding: 5px; margin-top: 5px;")
        white_layout.addWidget(self.btn_export)
        
        layout.addWidget(white_group)
        layout.addStretch()

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def _export_whitelist(self):
        """導出白名單內容到剪貼簿"""
        from PyQt6.QtWidgets import QApplication
        whitelist = self.settings_manager.settings.get('whitelist', [])
        if not whitelist:
            QMessageBox.information(self, "提示", "白名單為空。")
            return
            
        text = "\n".join(whitelist)
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "提示", "已複製到剪貼簿")

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
