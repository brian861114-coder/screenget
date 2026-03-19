"""
detail_page.py - 詳細清單頁面
顯示所有程式或網站的使用時長清單。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from core.analyzer import UsageAnalyzer
from typing import List, Dict, Any

class DetailItem(QFrame):
    """清單中的單個項目"""
    def __init__(self, rank: int, name: str, duration: str, percentage: float = None, parent=None):
        super().__init__(parent)
        self.setObjectName("detailItem")
        self.setStyleSheet("""
            #detailItem {
                background-color: #FFFFFF;
                border-radius: 8px;
                border: 1px solid #B9FBC0;
                margin: 2px 0px;
            }
            #detailItem:hover {
                background-color: #F0FBF2;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # 排名
        rank_label = QLabel(str(rank))
        rank_label.setFixedWidth(30)
        rank_label.setStyleSheet("color: #445566; font-size: 14px; font-weight: bold;")
        layout.addWidget(rank_label)
        
        # 名稱
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #000000; font-size: 14px;")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        # 時長
        duration_label = QLabel(duration)
        duration_label.setStyleSheet("color: #000000; font-size: 14px; font-weight: bold;")
        layout.addWidget(duration_label)

class DetailListPage(QWidget):
    """詳細清單頁面"""
    back_clicked = pyqtSignal()
    
    def __init__(self, analyzer: UsageAnalyzer, title: str, app_type: str = None, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer
        self.page_title = title
        self.app_type = app_type # 'app' or 'browser' 或 None
        self.current_period = 'daily'
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # ─── 標題區 ───
        header = QHBoxLayout()
        
        self.btn_back = QPushButton("⬅ 返回")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_clicked.emit)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #A2D2FF;
                color: #000000;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #BDE4FF; }
        """)
        header.addWidget(self.btn_back)
        
        self.title_label = QLabel(self.page_title)
        self.title_label.setStyleSheet("color: #000000; font-size: 20px; font-weight: bold; margin-left: 10px;")
        header.addWidget(self.title_label)
        header.addStretch()
        
        layout.addLayout(header)
        
        # ─── 清單區 ───
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
        
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()
        
        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)

    def set_period(self, period: str):
        self.current_period = period
        self.refresh_data()

    def refresh_data(self):
        """重新整理清單內容"""
        # 清除現有項目
        for i in reversed(range(self.list_layout.count())):
            item = self.list_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            else:
                self.list_layout.removeItem(item)
        
        # 根據週期取得時間範圍
        if self.current_period == 'daily':
            start, end = self.analyzer.get_today_range()
        elif self.current_period == 'weekly':
            start, end = self.analyzer.get_week_range()
        else:
            start, end = self.analyzer.get_month_range()
            
        # 取得排行
        if self.app_type == 'browser':
            # 瀏覽器類型使用網站細分排行
            rankings = self.analyzer.get_browser_site_rankings(start, end)
        else:
            rankings = self.analyzer.get_app_rankings(start, end, app_type=self.app_type)
        
        # 如果是顯示全部程式時，排除排行中總時長為 0 的 (雖然 get_app_rankings 通常只回會有紀錄的)
        rankings = [r for r in rankings if r['total_seconds'] > 0]
        
        for i, r in enumerate(rankings):
            item = DetailItem(i + 1, r['app_name'], r['formatted_time'])
            self.list_layout.insertWidget(self.list_layout.count() - 1, item)
        
        if not rankings:
            no_data = QLabel("目前無使用紀錄")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data.setStyleSheet("color: #445566; font-size: 16px; padding: 40px;")
            self.list_layout.insertWidget(0, no_data)
        
        self.list_layout.addStretch()
