"""
database.py - SQLite 資料庫模組
負責儲存與查詢使用時長資料，記錄每次使用事件的開始/結束時間。
資料保留 30 天，自動清理過期資料。
"""

import sqlite3
import os
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any


class UsageDatabase:
    """使用時長資料庫管理器"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            app_data = os.path.join(os.getenv('APPDATA', ''), 'ScreenGet')
            os.makedirs(app_data, exist_ok=True)
            db_path = os.path.join(app_data, 'screenget.db')
        self.db_path = db_path
        self._persistent_conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        # For :memory: databases, reuse one connection (each new connection = new db)
        if self.db_path == ':memory:':
            if self._persistent_conn is None:
                conn = sqlite3.connect(':memory:')
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys=ON")
                self._persistent_conn = conn
            return self._persistent_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _release_conn(self, conn: sqlite3.Connection):
        """Release a connection. For :memory: dbs, keep it open."""
        if self.db_path != ':memory:':
            conn.close()

    def _init_db(self):
        """初始化資料庫表結構"""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS usage_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT NOT NULL,
                    window_title TEXT,
                    exe_path TEXT,
                    app_type TEXT DEFAULT 'app',
                    url TEXT,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    duration_seconds REAL,
                    is_idle_excluded BOOLEAN DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_start_time ON usage_sessions(start_time);
                CREATE INDEX IF NOT EXISTS idx_app_name ON usage_sessions(app_name);
                CREATE INDEX IF NOT EXISTS idx_end_time ON usage_sessions(end_time);
                CREATE INDEX IF NOT EXISTS idx_app_type ON usage_sessions(app_type);
            """)
            conn.commit()
        finally:
            self._release_conn(conn)

    def start_session(self, app_name: str, window_title: str = "",
                      exe_path: str = "", app_type: str = "app",
                      url: str = "") -> int:
        """開始一個新的使用 session，回傳 session ID"""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            cursor = conn.execute(
                """INSERT INTO usage_sessions
                   (app_name, window_title, exe_path, app_type, url, start_time)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (app_name, window_title, exe_path, app_type, url, now)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            self._release_conn(conn)

    def end_session(self, session_id: int, end_time: datetime = None):
        """結束一個 session，記錄結束時間並計算持續秒數"""
        conn = self._get_conn()
        try:
            now = end_time if end_time else datetime.now()
            row = conn.execute(
                "SELECT start_time FROM usage_sessions WHERE id = ?",
                (session_id,)
            ).fetchone()
            if row:
                start_time = datetime.fromisoformat(row['start_time'])
                duration = (now - start_time).total_seconds()
                conn.execute(
                    """UPDATE usage_sessions
                       SET end_time = ?, duration_seconds = ?
                       WHERE id = ?""",
                    (now.isoformat(), duration, session_id)
                )
                conn.commit()
        finally:
            self._release_conn(conn)

    def end_session_at(self, session_id: int, end_time: datetime):
        """結束一個 session，使用指定的結束時間"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT start_time FROM usage_sessions WHERE id = ?",
                (session_id,)
            ).fetchone()
            if row:
                start_time = datetime.fromisoformat(row['start_time'])
                duration = (end_time - start_time).total_seconds()
                conn.execute(
                    """UPDATE usage_sessions
                       SET end_time = ?, duration_seconds = ?, is_idle_excluded = 1
                       WHERE id = ?""",
                    (end_time.isoformat(), duration, session_id)
                )
                conn.commit()
        finally:
            self._release_conn(conn)

    def get_sessions_in_range(self, start: datetime, end: datetime,
                              app_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """查詢指定時間範圍內的 sessions"""
        conn = self._get_conn()
        try:
            query = """
                SELECT * FROM usage_sessions
                WHERE start_time >= ? AND start_time < ?
                  AND (end_time IS NOT NULL)
                  AND duration_seconds > 0
            """
            params = [start.isoformat(), end.isoformat()]
            if app_name:
                query += " AND app_name = ?"
                params.append(app_name)
            query += " ORDER BY start_time ASC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            self._release_conn(conn)

    def get_active_session(self) -> Optional[Dict[str, Any]]:
        """取得目前進行中的 session（end_time 為 NULL）"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                """SELECT * FROM usage_sessions
                   WHERE end_time IS NULL
                   ORDER BY start_time DESC LIMIT 1"""
            ).fetchone()
            return dict(row) if row else None
        finally:
            self._release_conn(conn)

    def get_unique_apps(self, start: datetime, end: datetime) -> List[str]:
        """取得指定時間範圍內的所有不重複程式名稱"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT DISTINCT app_name FROM usage_sessions
                   WHERE start_time >= ? AND start_time < ?
                     AND end_time IS NOT NULL AND duration_seconds > 0
                   ORDER BY app_name""",
                (start.isoformat(), end.isoformat())
            ).fetchall()
            return [r['app_name'] for r in rows]
        finally:
            self._release_conn(conn)

    def cleanup_old_data(self, days: int = 30):
        """清理超過指定天數的舊資料"""
        conn = self._get_conn()
        try:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            conn.execute(
                "DELETE FROM usage_sessions WHERE start_time < ?",
                (cutoff,)
            )
            conn.commit()
        finally:
            self._release_conn(conn)

    def close_all_open_sessions(self):
        """關閉所有未完成的 sessions（程式異常退出時使用）"""
        conn = self._get_conn()
        try:
            now = datetime.now()
            rows = conn.execute(
                "SELECT id, start_time FROM usage_sessions WHERE end_time IS NULL"
            ).fetchall()
            for row in rows:
                start_time = datetime.fromisoformat(row['start_time'])
                duration = (now - start_time).total_seconds()
                conn.execute(
                    """UPDATE usage_sessions
                       SET end_time = ?, duration_seconds = ?
                       WHERE id = ?""",
                    (now.isoformat(), duration, row['id'])
                )
            conn.commit()
        finally:
            self._release_conn(conn)

    def get_browser_sessions_in_range(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """查詢指定時間範圍內的瀏覽器 sessions（app_type='browser'）"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT * FROM usage_sessions
                   WHERE start_time >= ? AND start_time < ?
                     AND app_type = 'browser'
                     AND end_time IS NOT NULL
                     AND duration_seconds > 0
                   ORDER BY start_time ASC""",
                (start.isoformat(), end.isoformat())
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            self._release_conn(conn)

    def update_session_url(self, session_id: int, url: str, window_title: str = ""):
        """更新 session 的 URL（來自瀏覽器擴充套件）"""
        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    "UPDATE usage_sessions SET url = ?, window_title = ? WHERE id = ?",
                    (url, window_title, session_id)
                )
        finally:
            self._release_conn(conn)

    def get_all_active_dates(self) -> List[date]:
        """取得所有有紀錄的日期（用於日曆標記）"""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            # 取得 start_time 的日期部分並去重
            cursor.execute("SELECT DISTINCT date(start_time) FROM usage_sessions")
            dates = []
            for row in cursor.fetchall():
                if row[0]:
                    try:
                        d = datetime.strptime(row[0], '%Y-%m-%d').date()
                        dates.append(d)
                    except ValueError:
                        continue
            return sorted(dates)
        finally:
            self._release_conn(conn)
