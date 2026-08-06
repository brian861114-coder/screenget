"""
health_check.py - 資料與系統健康檢查
"""

from __future__ import annotations

import os
import sqlite3
import winreg
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Optional, Callable

from core.browser_bridge import (
    BrowserBridgeWatcher,
    HOST_NAME,
    bridge_state_path,
    read_bridge_event,
)
from core.database import UsageDatabase
from core.settings_manager import SettingsManager
from core.i18n import t


@dataclass
class HealthIssue:
    level: str  # ok | warn | error
    code: str
    message: str
    fixable: bool = False
    detail: str = ""


def _registry_host_path(browser: str) -> Optional[str]:
    bases = {
        "chrome": r"Software\Google\Chrome\NativeMessagingHosts",
        "edge": r"Software\Microsoft\Edge\NativeMessagingHosts",
    }
    base = bases.get(browser)
    if not base:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{base}\\{HOST_NAME}") as key:
            value, _ = winreg.QueryValueEx(key, None)
            return value
    except OSError:
        return None


def run_health_check(
    db: UsageDatabase,
    settings: SettingsManager,
    *,
    is_tracking: Optional[Callable[[], bool]] = None,
    is_idle: Optional[Callable[[], bool]] = None,
    is_paused: Optional[Callable[[], bool]] = None,
) -> List[HealthIssue]:
    issues: List[HealthIssue] = []

    # 資料庫檔案
    db_path = db.db_path
    if db_path != ":memory:" and not os.path.exists(db_path):
        issues.append(HealthIssue("error", "db_missing", f"資料庫不存在：{db_path}"))
    else:
        size = os.path.getsize(db_path) if db_path != ":memory:" and os.path.exists(db_path) else 0
        issues.append(HealthIssue(
            "ok", "db_ok",
            f"資料庫正常（{size/1024:.1f} KB）" if size else "資料庫正常",
            detail=db_path,
        ))

    conn = db._get_conn()
    try:
        open_count = conn.execute(
            "SELECT COUNT(*) FROM usage_sessions WHERE end_time IS NULL"
        ).fetchone()[0]
        if open_count > 1:
            issues.append(HealthIssue(
                "warn", "multi_open",
                f"有 {open_count} 筆未結束 session（正常最多 1 筆進行中）",
                fixable=True,
            ))
        elif open_count == 1:
            issues.append(HealthIssue("ok", "one_open", "目前有 1 筆進行中的 session"))
        else:
            issues.append(HealthIssue("ok", "no_open", "沒有異常未結束的 session"))

        # 超長 session
        inflated = conn.execute(
            "SELECT COUNT(*) FROM usage_sessions WHERE duration_seconds > ?",
            (8 * 3600,),
        ).fetchone()[0]
        if inflated:
            issues.append(HealthIssue(
                "warn", "inflated",
                f"發現 {inflated} 筆超過 8 小時的異常 session",
                fixable=True,
            ))
        else:
            issues.append(HealthIssue("ok", "no_inflated", "沒有異常超長 session"))

        # 負時長 / 結束早於開始
        bad = conn.execute(
            """SELECT COUNT(*) FROM usage_sessions
               WHERE duration_seconds < 0
                  OR (end_time IS NOT NULL AND end_time < start_time)"""
        ).fetchone()[0]
        if bad:
            issues.append(HealthIssue(
                "error", "bad_duration",
                f"發現 {bad} 筆時長／時間異常的紀錄",
                fixable=True,
            ))
        else:
            issues.append(HealthIssue("ok", "duration_ok", "時長欄位看起來正常"))

        # 近期活動
        day_ago = (datetime.now() - timedelta(days=1)).isoformat()
        recent = conn.execute(
            "SELECT COUNT(*) FROM usage_sessions WHERE start_time >= ?",
            (day_ago,),
        ).fetchone()[0]
        if recent == 0:
            issues.append(HealthIssue(
                "warn", "no_recent",
                "過去 24 小時沒有任何使用紀錄（可能未追蹤或剛安裝）",
            ))
        else:
            issues.append(HealthIssue("ok", "recent_ok", f"過去 24 小時有 {recent} 筆紀錄"))

        # 瀏覽器有 URL 的比例（近 7 天）
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        browser_total = conn.execute(
            """SELECT COUNT(*) FROM usage_sessions
               WHERE app_type='browser' AND start_time >= ? AND end_time IS NOT NULL""",
            (week_ago,),
        ).fetchone()[0]
        browser_with_url = conn.execute(
            """SELECT COUNT(*) FROM usage_sessions
               WHERE app_type='browser' AND start_time >= ? AND end_time IS NOT NULL
                 AND url IS NOT NULL AND url != ''""",
            (week_ago,),
        ).fetchone()[0]
        if browser_total > 10 and browser_with_url == 0:
            issues.append(HealthIssue(
                "warn", "no_url",
                f"近 7 天 {browser_total} 筆瀏覽器紀錄皆無 URL（橋接可能未運作）",
            ))
        elif browser_total > 0:
            pct = 100.0 * browser_with_url / browser_total
            level = "ok" if pct >= 20 else "warn"
            issues.append(HealthIssue(
                level, "url_rate",
                f"近 7 天瀏覽器 URL 覆蓋率 {pct:.0f}%（{browser_with_url}/{browser_total}）",
            ))
        else:
            issues.append(HealthIssue("ok", "no_browser", "近 7 天尚無瀏覽器紀錄"))
    finally:
        db._release_conn(conn)

    # Native Messaging 註冊
    chrome_path = _registry_host_path("chrome")
    edge_path = _registry_host_path("edge")
    if chrome_path and os.path.exists(chrome_path):
        issues.append(HealthIssue("ok", "chrome_host", f"Chrome 橋接已註冊", detail=chrome_path))
    else:
        issues.append(HealthIssue(
            "warn", "chrome_host_missing",
            "Chrome Native Messaging 尚未註冊或路徑無效",
            fixable=True,
        ))
    if edge_path and os.path.exists(edge_path):
        issues.append(HealthIssue("ok", "edge_host", "Edge 橋接已註冊", detail=edge_path))
    else:
        issues.append(HealthIssue(
            "warn", "edge_host_missing",
            "Edge Native Messaging 尚未註冊或路徑無效",
            fixable=True,
        ))

    # 橋接即時狀態
    if BrowserBridgeWatcher.is_connected(120):
        ev = read_bridge_event() or {}
        issues.append(HealthIssue(
            "ok", "bridge_live",
            f"擴充套件近期有回報（{ev.get('domain') or ev.get('type') or 'ping'}）",
        ))
    else:
        age = ""
        ev = read_bridge_event()
        if ev and ev.get("timestamp"):
            age = f"（最後：{ev['timestamp'][:19]}）"
        issues.append(HealthIssue(
            "warn", "bridge_stale",
            f"擴充套件超過 2 分鐘無回報{age}",
        ))

    # 執行狀態
    if is_paused and is_paused():
        issues.append(HealthIssue("warn", "paused", "追蹤目前為暫停狀態"))
    elif is_idle and is_idle():
        issues.append(HealthIssue("ok", "idle", "目前處於閒置暫停（正常）"))
    elif is_tracking and is_tracking():
        issues.append(HealthIssue("ok", "tracking", "追蹤引擎運作中"))

    # 設定
    idle_m = settings.get_idle_timeout_minutes()
    issues.append(HealthIssue("ok", "idle_setting", f"閒置門檻：{idle_m} 分鐘"))

    return issues


def repair_health_issues(db: UsageDatabase, settings: SettingsManager,
                         issues: List[HealthIssue]) -> int:
    """修復可自動處理的問題，回傳修復次數。"""
    from core.browser_bridge import register_native_host

    fixed = 0
    codes = {i.code for i in issues if i.fixable}

    if "multi_open" in codes or "inflated" in codes:
        # 關閉多餘 orphan（保留最新一筆 open）
        conn = db._get_conn()
        try:
            rows = conn.execute(
                """SELECT id, start_time FROM usage_sessions
                   WHERE end_time IS NULL ORDER BY start_time DESC"""
            ).fetchall()
            for row in rows[1:]:
                start_time = datetime.fromisoformat(row["start_time"])
                conn.execute(
                    """UPDATE usage_sessions
                       SET end_time=?, duration_seconds=0, is_idle_excluded=1
                       WHERE id=?""",
                    (start_time.isoformat(), row["id"]),
                )
                fixed += 1
            conn.commit()
        finally:
            db._release_conn(conn)

        n = db.repair_inflated_sessions(max_hours=8.0)
        fixed += n

    if "bad_duration" in codes:
        conn = db._get_conn()
        try:
            cur = conn.execute(
                """UPDATE usage_sessions
                   SET duration_seconds=0, is_idle_excluded=1
                   WHERE duration_seconds < 0
                      OR (end_time IS NOT NULL AND end_time < start_time)"""
            )
            fixed += cur.rowcount or 0
            conn.commit()
        finally:
            db._release_conn(conn)

    if "chrome_host_missing" in codes or "edge_host_missing" in codes:
        if register_native_host(settings.get_extension_id()):
            fixed += 1

    return fixed


def issues_to_text(issues: List[HealthIssue]) -> str:
    lines = []
    mark = {"ok": "[OK]", "warn": "[!]", "error": "[X]"}
    for i in issues:
        prefix = mark.get(i.level, "[-]")
        extra = " ［可修復］" if i.fixable else ""
        lines.append(f"{prefix} {i.message}{extra}")
    return "\n".join(lines)
