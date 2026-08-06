"""
analyzer.py - 資料分析模組
對使用時長資料庫中的資料進行分析，提供日/週/月統計。
"""

import re
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from urllib.parse import urlparse

from core.database import UsageDatabase
from core.settings_manager import SettingsManager
from core.units import format_duration as format_duration_value, credibility_from_ratio

BROWSER_TITLE_SUFFIXES = (
    ' - Google Chrome',
    ' - Microsoft Edge',
    ' - Mozilla Firefox',
    ' - Brave',
    ' - Opera',
    ' - Vivaldi',
    ' - Arc',
    ' — Mozilla Firefox',
)

KNOWN_SITE_KEYWORDS = (
    ('bilibili', 'bilibili'),
    ('哔哩哔哩', 'bilibili'),
    ('youtube', 'YouTube'),
    ('gmail', 'Gmail'),
    ('google gemini', 'Google Gemini'),
    ('gemini', 'Google Gemini'),
    ('chatgpt', 'ChatGPT'),
    ('github', 'GitHub'),
    ('notion', 'Notion'),
    ('twitter', 'X/Twitter'),
    ('x.com', 'X/Twitter'),
    ('facebook', 'Facebook'),
    ('instagram', 'Instagram'),
    ('reddit', 'Reddit'),
    ('linkedin', 'LinkedIn'),
    ('netflix', 'Netflix'),
    ('spotify', 'Spotify'),
)


def extract_website_label(window_title: str = "", url: str = "") -> str:
    """從 URL 或視窗標題推導網站顯示名稱"""
    if url:
        try:
            parsed = urlparse(url)
            if parsed.scheme in ('chrome', 'edge', 'about', 'chrome-extension', 'brave'):
                host = parsed.netloc or 'internal'
                return f"{parsed.scheme}://{host}"
            if parsed.netloc:
                return parsed.netloc.removeprefix('www.')
        except Exception:
            pass

    title = (window_title or '').strip()
    if not title:
        return '未知網站'

    for suffix in BROWSER_TITLE_SUFFIXES:
        if title.endswith(suffix):
            title = title[:-len(suffix)].strip()
            break

    title = re.sub(
        r'\s*[-–—]\s*(Profile|Profiles|个人资料|個人資料)\s*\d+\s*$',
        '',
        title,
        flags=re.IGNORECASE,
    ).strip()

    lower = title.lower()
    for keyword, label in KNOWN_SITE_KEYWORDS:
        if keyword in lower:
            return label

    # 常見「頁面標題 - 網站名」格式，取最後一段作為網站
    if ' - ' in title:
        parts = [p.strip() for p in title.split(' - ') if p.strip()]
        if len(parts) >= 2 and len(parts[-1]) <= 40:
            return parts[-1]

    return title[:60] if title else '未知網站'


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

    def _is_whitelisted(self, name: str) -> bool:
        return bool(self.settings and self.settings.is_whitelisted(name))

    BROWSER_APP_NAMES = frozenset({
        "Google Chrome", "Microsoft Edge", "Mozilla Firefox",
        "Brave", "Opera", "Vivaldi", "Arc",
    })

    def site_label_for_session(self, session: Dict[str, Any]) -> Optional[str]:
        """從瀏覽器 session 解析網站標籤；非瀏覽器回傳 None。"""
        if session.get("app_type") != "browser":
            return None
        name = session.get("app_name", "") or ""
        url = session.get("url", "") or ""
        title = session.get("window_title", "") or ""
        if url:
            site = extract_website_label(title, url)
        elif name and name not in self.BROWSER_APP_NAMES:
            site = name
        else:
            site = extract_website_label(title, "")
        if self._is_whitelisted(site) or self._is_whitelisted(name):
            return None
        return site

    def _iter_website_sessions(self, start: datetime, end: datetime, site: str = None):
        for s in self.db.get_sessions_in_range(start, end):
            label = self.site_label_for_session(s)
            if not label:
                continue
            if site is not None and label != site:
                continue
            yield s, label

    # ─── 總使用時長 ───

    def get_total_usage(self, start: datetime, end: datetime,
                        app_name: str = None) -> float:
        """取得指定時間範圍的總使用秒數（已依區間裁切）"""
        sessions = self.db.get_sessions_in_range(start, end, app_name)
        return sum(
            s.get('duration_seconds', 0) or 0 for s in sessions
            if not self._is_whitelisted(s['app_name'])
        )

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

            if self._is_whitelisted(name):
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

    # ─── 瀏覽器網站排行 ───

    def get_website_rankings(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """
        以網站為單位統計瀏覽器使用時長。
        優先 URL；其次 bridge 寫入的網域 app_name；最後才用標題推斷。
        每筆含 credibility: exact / mixed / estimated。
        """
        site_usage: Dict[str, float] = defaultdict(float)
        site_url: Dict[str, float] = defaultdict(float)
        for s, site in self._iter_website_sessions(start, end):
            dur = s.get("duration_seconds", 0) or 0
            site_usage[site] += dur
            if (s.get("url") or "").strip():
                site_url[site] += dur

        rankings = []
        for name, total in sorted(site_usage.items(), key=lambda x: x[1], reverse=True):
            if total <= 0:
                continue
            cred = credibility_from_ratio(site_url[name], total)
            rankings.append({
                "app_name": name,
                "total_seconds": total,
                "app_type": "browser",
                "formatted_time": self.format_duration(total),
                "credibility": cred,
                "url_ratio": (site_url[name] / total) if total else 0.0,
            })
        return rankings

    def get_browser_credibility_summary(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """瀏覽器整體可信度摘要（依時長加權）。"""
        url_secs = 0.0
        total = 0.0
        for s, _ in self._iter_website_sessions(start, end):
            dur = s.get("duration_seconds", 0) or 0
            total += dur
            if (s.get("url") or "").strip():
                url_secs += dur
        cred = credibility_from_ratio(url_secs, total)
        ratio = (url_secs / total) if total else 0.0
        return {
            "credibility": cred,
            "url_ratio": ratio,
            "url_percent": int(round(ratio * 100)),
            "total_seconds": total,
        }

    def get_browser_rankings(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """瀏覽器分析頁使用網站排行（非瀏覽器進程名稱）"""
        return self.get_website_rankings(start, end)

    def get_daily_browser_rankings(self) -> List[Dict[str, Any]]:
        start, end = self.get_today_range()
        return self.get_browser_rankings(start, end)

    def get_all_websites_in_range(self, start: datetime, end: datetime) -> List[str]:
        sites = set()
        for _, site in self._iter_website_sessions(start, end):
            sites.add(site)
        return sorted(sites)

    def get_website_total(self, start: datetime, end: datetime, site: str) -> float:
        return sum(
            s.get("duration_seconds", 0) or 0
            for s, _ in self._iter_website_sessions(start, end, site)
        )

    def get_website_daily_total(self, site: str) -> float:
        start, end = self.get_today_range()
        return self.get_website_total(start, end, site)

    def get_website_weekly_total(self, site: str) -> float:
        start, end = self.get_week_range()
        return self.get_website_total(start, end, site)

    def get_website_monthly_total(self, site: str) -> float:
        start, end = self.get_month_range()
        return self.get_website_total(start, end, site)

    def get_website_time_blocks(self, start: datetime, end: datetime,
                                site: str) -> List[Dict[str, Any]]:
        blocks = []
        for s, label in self._iter_website_sessions(start, end, site):
            clipped_start = s.get("clipped_start")
            clipped_end = s.get("clipped_end")
            if not clipped_start or not clipped_end:
                continue
            blocks.append({
                "app_name": label,
                "app_type": "browser",
                "start": clipped_start,
                "end": clipped_end,
                "duration_seconds": s.get("duration_seconds", 0),
                "window_title": s.get("window_title", ""),
                "url": s.get("url", ""),
            })
        return blocks

    def get_website_hourly(self, start: datetime, end: datetime,
                           site: str) -> Dict[int, float]:
        hourly: Dict[int, float] = defaultdict(float)
        for s, _ in self._iter_website_sessions(start, end, site):
            s_start = s.get("clipped_start")
            s_end = s.get("clipped_end")
            if not s_start or not s_end:
                continue
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
        return dict(hourly)

    def get_website_trend(self, start: datetime, end: datetime,
                          site: str) -> List[Dict[str, Any]]:
        return self.get_trend_for_range(start, end, website=site)

    def get_website_credibility(self, start: datetime, end: datetime, site: str) -> Dict[str, Any]:
        url_secs = 0.0
        total = 0.0
        for s, _ in self._iter_website_sessions(start, end, site):
            dur = s.get("duration_seconds", 0) or 0
            total += dur
            if (s.get("url") or "").strip():
                url_secs += dur
        cred = credibility_from_ratio(url_secs, total)
        ratio = (url_secs / total) if total else 0.0
        return {
            "credibility": cred,
            "url_ratio": ratio,
            "url_percent": int(round(ratio * 100)),
            "total_seconds": total,
        }

    def get_website_pages(self, start: datetime, end: datetime,
                          site: str, max_items: int = 8) -> Tuple[List[Dict[str, Any]], str]:
        """單一網站內的頁面／標題排行（第三層細節）；回傳 (rankings, precision)。"""
        page_usage: Dict[str, float] = defaultdict(float)
        url_secs = 0.0
        total = 0.0
        for s, _ in self._iter_website_sessions(start, end, site):
            dur = s.get("duration_seconds", 0) or 0
            total += dur
            url = (s.get("url") or "").strip()
            title = (s.get("window_title") or "").strip()
            if url:
                url_secs += dur
                try:
                    parsed = urlparse(url)
                    path = parsed.path or "/"
                    if len(path) > 48:
                        path = path[:45] + "…"
                    label = f"{parsed.netloc.removeprefix('www.')}{path}"
                except Exception:
                    label = url[:60]
            elif title:
                for suffix in BROWSER_TITLE_SUFFIXES:
                    if title.endswith(suffix):
                        title = title[:-len(suffix)].strip()
                        break
                label = title[:60] if title else site
            else:
                label = site
            page_usage[label] += dur

        rankings = []
        for name, page_total in sorted(page_usage.items(), key=lambda x: x[1], reverse=True):
            if page_total <= 0:
                continue
            rankings.append({
                "app_name": name,
                "total_seconds": page_total,
                "app_type": "browser",
                "formatted_time": self.format_duration(page_total),
            })
            if len(rankings) >= max_items:
                break

        precision = credibility_from_ratio(url_secs, total)
        return rankings, precision

    # ─── 分類統計 ───

    def get_category_for(self, name: str, app_type: str = None) -> str:
        if self.settings:
            return self.settings.get_category(name, app_type)
        if app_type == "browser":
            return "瀏覽"
        if app_type == "game":
            return "遊戲"
        return "其他"

    def get_category_rankings(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """依分類彙總使用時長"""
        sessions = self.db.get_sessions_in_range(start, end)
        cat_usage: Dict[str, float] = defaultdict(float)

        for s in sessions:
            name = s["app_name"]
            if self._is_whitelisted(name):
                continue
            # 瀏覽器 session：以網站標籤做分類鍵更合理
            if s.get("app_type") == "browser":
                label = self.site_label_for_session(s)
                if not label:
                    continue
                category = self.get_category_for(label, "browser")
            else:
                category = self.get_category_for(name, s.get("app_type"))
            cat_usage[category] += s.get("duration_seconds", 0) or 0

        rankings = []
        for name, total in sorted(cat_usage.items(), key=lambda x: x[1], reverse=True):
            if total <= 0:
                continue
            rankings.append({
                "app_name": name,
                "total_seconds": total,
                "app_type": "category",
                "formatted_time": self.format_duration(total),
            })
        return rankings

    # ─── 時間段分析（用於長條圖） ───

    def get_time_blocks(self, start: datetime, end: datetime,
                        app_name: str = None) -> List[Dict[str, Any]]:
        """
        取得使用時間段（已裁切至查詢區間）。
        回傳格式：[{'app_name': ..., 'start': datetime, 'end': datetime, ...}, ...]
        """
        sessions = self.db.get_sessions_in_range(start, end, app_name)
        blocks = []
        for s in sessions:
            if self._is_whitelisted(s['app_name']):
                continue
            clipped_start = s.get('clipped_start')
            clipped_end = s.get('clipped_end')
            if not clipped_start or not clipped_end:
                continue
            blocks.append({
                'app_name': s['app_name'],
                'app_type': s.get('app_type', 'app'),
                'start': clipped_start,
                'end': clipped_end,
                'duration_seconds': s.get('duration_seconds', 0),
                'window_title': s.get('window_title', ''),
                'url': s.get('url', ''),
            })
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
            if self._is_whitelisted(s['app_name']):
                continue
            s_start = s.get('clipped_start')
            s_end = s.get('clipped_end')
            if not s_start or not s_end:
                continue

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

        return dict(hourly)

    # ─── 每日趨勢（過去 N 天的使用量） ───

    def get_daily_trend(self, days: int = 7,
                        app_name: str = None,
                        app_type: str = None) -> List[Dict[str, Any]]:
        """取得過去 N 天每天的總使用時長，可依名稱或類型篩選"""
        today = date.today()
        start = datetime.combine(today - timedelta(days=days - 1), datetime.min.time())
        end = datetime.combine(today + timedelta(days=1), datetime.min.time())
        return self.get_trend_for_range(start, end, app_name=app_name, app_type=app_type)

    def get_trend_for_range(self, start: datetime, end: datetime,
                            app_name: str = None,
                            app_type: str = None,
                            website: str = None) -> List[Dict[str, Any]]:
        """取得指定區間內每日趨勢（單次查詢後在記憶體分桶）。"""
        day = start.date()
        end_day = (end - timedelta(seconds=1)).date()
        buckets: Dict[date, float] = {}
        while day <= end_day:
            buckets[day] = 0.0
            day += timedelta(days=1)

        sessions = self.db.get_sessions_in_range(start, end)
        for s in sessions:
            if website:
                label = self.site_label_for_session(s)
                if label != website:
                    continue
            elif app_type == "browser":
                if s.get("app_type") != "browser":
                    continue
                if not self.site_label_for_session(s):
                    continue
            elif app_type:
                if s.get("app_type") != app_type:
                    continue
                if self._is_whitelisted(s.get("app_name", "")):
                    continue
            elif app_name:
                if s.get("app_name") != app_name:
                    continue
                if self._is_whitelisted(app_name):
                    continue
            else:
                if self._is_whitelisted(s.get("app_name", "")):
                    continue

            s_start = s.get("clipped_start")
            s_end = s.get("clipped_end")
            if not s_start or not s_end:
                continue

            current = s_start
            while current < s_end:
                d = current.date()
                next_midnight = datetime.combine(d + timedelta(days=1), datetime.min.time())
                slice_end = min(next_midnight, s_end)
                if d in buckets:
                    buckets[d] += (slice_end - current).total_seconds()
                current = slice_end

        trend = []
        day = start.date()
        while day <= end_day:
            total = buckets.get(day, 0.0)
            trend.append({
                "date": day,
                "date_str": day.strftime("%m/%d"),
                "total_seconds": total,
                "formatted_time": self.format_duration(total),
            })
            day += timedelta(days=1)
        return trend

    # ─── 工具方法 ───

    def format_duration(self, seconds: float, unit: str = None) -> str:
        """格式化時間長度；單位來自參數或設定（auto / hours / minutes）。"""
        if unit is None:
            unit = self.settings.get_duration_unit() if self.settings else "auto"
        return format_duration_value(seconds, unit)

    def get_all_apps_today(self) -> List[str]:
        """取得今天所有使用過的程式"""
        start, end = self.get_today_range()
        return self.db.get_unique_apps(start, end)

    def get_all_apps_in_range(self, start: datetime, end: datetime) -> List[str]:
        """取得指定範圍內所有使用過的程式"""
        return self.db.get_unique_apps(start, end)
