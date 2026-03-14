"""
analyzer.py - 資料分析模組
對使用時長資料庫中的資料進行分析，提供日/週/月統計。
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Tuple
from collections import defaultdict

from core.database import UsageDatabase
from core.settings_manager import SettingsManager

class UsageAnalyzer:
    """使用量分析器"""

    def __init__(self, db: UsageDatabase, settings: SettingsManager = None):
        self.db = db
        self.settings = settings

    # ─── 時間範圍工具 ───

    @staticmethod
    def get_today_range() -> Tuple[datetime, datetime]:
        """取得今天的時間範圍"""
        today = date.today()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today + timedelta(days=1), datetime.min.time())
        return start, end

    @staticmethod
    def get_week_range() -> Tuple[datetime, datetime]:
        """取得本週的時間範圍（週一到今天）"""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        start = datetime.combine(monday, datetime.min.time())
        end = datetime.combine(today + timedelta(days=1), datetime.min.time())
        return start, end

    @staticmethod
    def get_month_range() -> Tuple[datetime, datetime]:
        """取得本月的時間範圍（1號到今天）"""
        today = date.today()
        first_day = today.replace(day=1)
        start = datetime.combine(first_day, datetime.min.time())
        end = datetime.combine(today + timedelta(days=1), datetime.min.time())
        return start, end

    # ─── 總使用時長 ───

    def get_total_usage(self, start: datetime, end: datetime,
                        app_name: str = None) -> float:
        """取得指定時間範圍的總使用秒數"""
        sessions = self.db.get_sessions_in_range(start, end, app_name)
        return sum(s.get('duration_seconds', 0) or 0 for s in sessions 
                   if not (self.settings and self.settings.is_whitelisted(s['app_name'])))

    def get_daily_total(self, app_name: str = None) -> float:
        """當日總使用時長（秒）"""
        start, end = self.get_today_range()
        return self.get_total_usage(start, end, app_name)

    def get_weekly_total(self, app_name: str = None) -> float:
        """當周總使用時長（秒）"""
        start, end = self.get_week_range()
        return self.get_total_usage(start, end, app_name)

    def get_monthly_total(self, app_name: str = None) -> float:
        """當月總使用時長（秒）"""
        start, end = self.get_month_range()
        return self.get_total_usage(start, end, app_name)

    # ─── 各程式使用時長排行 ───

    def get_app_rankings(self, start: datetime, end: datetime, 
                         app_type: str = None) -> List[Dict[str, Any]]:
        """取得各程式的使用時長排行，可篩選類型 (app / browser / game)"""
        sessions = self.db.get_sessions_in_range(start, end)
        app_usage: Dict[str, float] = defaultdict(float)
        app_types: Dict[str, str] = {}

        for s in sessions:
            name = s['app_name']
            
            # 白名單過濾
            if self.settings and self.settings.is_whitelisted(name):
                continue
                
            if app_type and s.get('app_type') != app_type:
                continue
            duration = s.get('duration_seconds', 0) or 0
            app_usage[name] += duration
            if name not in app_types:
                app_types[name] = s.get('app_type', 'app')

        rankings = []
        for name, total in sorted(app_usage.items(), key=lambda x: x[1], reverse=True):
            rankings.append({
                'app_name': name,
                'total_seconds': total,
                'app_type': app_types.get(name, 'app'),
                'formatted_time': self.format_duration(total),
            })
        return rankings

    def get_daily_rankings(self) -> List[Dict[str, Any]]:
        start, end = self.get_today_range()
        return self.get_app_rankings(start, end)

    def get_weekly_rankings(self) -> List[Dict[str, Any]]:
        start, end = self.get_week_range()
        return self.get_app_rankings(start, end)

    def get_monthly_rankings(self) -> List[Dict[str, Any]]:
        start, end = self.get_month_range()
        return self.get_app_rankings(start, end)

    # ─── 瀏覽器專用排行 ───

    def get_browser_rankings(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        return self.get_app_rankings(start, end, app_type='browser')

    def get_daily_browser_rankings(self) -> List[Dict[str, Any]]:
        start, end = self.get_today_range()
        return self.get_browser_rankings(start, end)

    # ─── 時間段分析（用於長條圖） ───

    def get_time_blocks(self, start: datetime, end: datetime,
                        app_name: str = None) -> List[Dict[str, Any]]:
        """
        取得使用時間段（每個 session 的起止時間）。
        回傳格式：[{'app_name': ..., 'start': datetime, 'end': datetime, ...}, ...]
        用於繪製 Gantt-style 時間段長條圖。
        """
        sessions = self.db.get_sessions_in_range(start, end, app_name)
        blocks = []
        for s in sessions:
            try:
                s_start = datetime.fromisoformat(s['start_time'])
                s_end = datetime.fromisoformat(s['end_time']) if s['end_time'] else None
                if s_end:
                    app_name = s['app_name']
                    # 白名單過濾
                    if self.settings and self.settings.is_whitelisted(app_name):
                        continue
                        
                    blocks.append({
                        'app_name': app_name,
                        'app_type': s.get('app_type', 'app'),
                        'start': s_start,
                        'end': s_end,
                        'duration_seconds': s.get('duration_seconds', 0),
                        'window_title': s.get('window_title', ''),
                        'url': s.get('url', ''),
                    })
            except (ValueError, TypeError):
                continue
        return blocks

    def get_hourly_usage(self, start: datetime, end: datetime,
                         app_name: str = None) -> Dict[int, float]:
        """
        取得每小時的使用秒數分佈（0-23 小時）。
        用於繪製 24 小時使用分佈圖。
        """
        sessions = self.db.get_sessions_in_range(start, end, app_name)
        hourly: Dict[int, float] = defaultdict(float)

        for s in sessions:
            try:
                s_start = datetime.fromisoformat(s['start_time'])
                s_end = datetime.fromisoformat(s['end_time']) if s['end_time'] else None
                if not s_end:
                    continue
                
                # 白名單過濾
                if self.settings and self.settings.is_whitelisted(s['app_name']):
                    continue

                # 將 session 分配到各小時
                current = s_start
                while current < s_end:
                    hour = current.hour
                    next_hour = current.replace(
                        minute=0, second=0, microsecond=0
                    ) + timedelta(hours=1)

                    if next_hour > s_end:
                        hourly[hour] += (s_end - current).total_seconds()
                    else:
                        hourly[hour] += (next_hour - current).total_seconds()
                    current = next_hour

            except (ValueError, TypeError):
                continue

        return dict(hourly)

    # ─── 每日趨勢（過去 N 天的使用量） ───

    def get_daily_trend(self, days: int = 7,
                        app_name: str = None,
                        app_type: str = None) -> List[Dict[str, Any]]:
        """取得過去 N 天每天的總使用時長，可依名稱或類型篩選"""
        today = date.today()
        trend = []
        for i in range(days - 1, -1, -1):
            day = today - timedelta(days=i)
            start = datetime.combine(day, datetime.min.time())
            end = datetime.combine(day + timedelta(days=1), datetime.min.time())
            
            # 這裡需要一個過濾 app_type 的 get_total_usage
            if app_type:
                sessions = self.db.get_sessions_in_range(start, end)
                total = sum(s.get('duration_seconds', 0) or 0 
                            for s in sessions if s.get('app_type') == app_type 
                            and not (self.settings and self.settings.is_whitelisted(s['app_name'])))
            else:
                if app_name: # Specific app
                    total = self.get_total_usage(start, end, app_name)
                else: # Global total, apply whitelist
                    sessions = self.db.get_sessions_in_range(start, end)
                    total = sum(s.get('duration_seconds', 0) or 0 
                                for s in sessions 
                                if not (self.settings and self.settings.is_whitelisted(s['app_name'])))
                
            trend.append({
                'date': day,
                'date_str': day.strftime('%m/%d'),
                'total_seconds': total,
                'formatted_time': self.format_duration(total),
            })
        return trend

    # ─── 工具方法 ───

    @staticmethod
    def format_duration(seconds: float) -> str:
        """格式化時間長度為可讀字串"""
        if seconds < 0:
            seconds = 0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def get_all_apps_today(self) -> List[str]:
        """取得今天所有使用過的程式"""
        start, end = self.get_today_range()
        return self.db.get_unique_apps(start, end)

    def get_all_apps_in_range(self, start: datetime, end: datetime) -> List[str]:
        """取得指定範圍內所有使用過的程式"""
        return self.db.get_unique_apps(start, end)
