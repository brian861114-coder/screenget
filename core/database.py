"""
database.py - SQLite 資料庫模組
負責儲存與查詢使用時長資料，記錄每次使用事件的開始/結束時間。
資料保留 30 天，自動清理過期資料。
"""

import sqlite3
import os
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class UsageDatabase:
    """使用時長資料庫管理器"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            app_data = os.path.join(os.getenv('APPDATA', ''), 'ScreenGet')
            os.makedirs(app_data, exist_ok=True)
            db_path = os.path.join(app_data, 'screenget.db')
        self.db_path = db_path
        self._persistent_conn: Optional[sqlite3.Connection] = None
        self._local = threading.local()
        self._init_db()

    def _configure_conn(self, conn: sqlite3.Connection):
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")

    def _get_conn(self) -> sqlite3.Connection:
        # For :memory: databases, reuse one connection (each new connection = new db)
        if self.db_path == ':memory:':
            if self._persistent_conn is None:
                conn = sqlite3.connect(':memory:', timeout=30.0)
                self._configure_conn(conn)
                self._persistent_conn = conn
            return self._persistent_conn

        # 執行緒本地連線重用，降低開開關關與鎖競爭
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            self._configure_conn(conn)
            self._local.conn = conn
        return conn

    def _release_conn(self, conn: sqlite3.Connection):
        """檔案 DB 使用執行緒本地連線，不在每次查詢後關閉。"""
        return

    def close(self):
        """關閉執行緒本地／記憶體連線（關閉應用時呼叫）。"""
        if self._persistent_conn is not None:
            try:
                self._persistent_conn.close()
            except Exception:
                pass
            self._persistent_conn = None
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

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

    def end_session(self, session_id: int):
        """結束一個 session，記錄結束時間並計算持續秒數"""
        conn = self._get_conn()
        try:
            now = datetime.now()
            row = conn.execute(
                "SELECT start_time FROM usage_sessions WHERE id = ?",
                (session_id,)
            ).fetchone()
            if row:
                start_time = datetime.fromisoformat(row['start_time'])
                duration = max(0.0, (now - start_time).total_seconds())
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
        """結束一個 session，使用指定的結束時間（例如進入閒置時）"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT start_time FROM usage_sessions WHERE id = ?",
                (session_id,)
            ).fetchone()
            if row:
                start_time = datetime.fromisoformat(row['start_time'])
                if end_time < start_time:
                    end_time = start_time
                duration = max(0.0, (end_time - start_time).total_seconds())
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
                              app_name: Optional[str] = None,
                              include_active: bool = True) -> List[Dict[str, Any]]:
        """
        查詢與指定時間範圍重疊的 sessions。
        會裁切到 [start, end)，並可把進行中的 session 以目前時間計入。
        回傳的每筆會帶 clipped_start / clipped_end / duration_seconds（裁切後）。
        """
        conn = self._get_conn()
        try:
            # 與區間重疊：start_time < range_end AND (end_time IS NULL OR end_time > range_start)
            query = """
                SELECT * FROM usage_sessions
                WHERE start_time < ?
                  AND (end_time IS NULL OR end_time > ?)
            """
            params: List[Any] = [end.isoformat(), start.isoformat()]
            if app_name:
                query += " AND app_name = ?"
                params.append(app_name)
            query += " ORDER BY start_time ASC"
            rows = conn.execute(query, params).fetchall()

            now = datetime.now()
            results = []
            for r in rows:
                session = dict(r)
                try:
                    s_start = datetime.fromisoformat(session['start_time'])
                except (ValueError, TypeError):
                    continue

                if session.get('end_time'):
                    try:
                        s_end = datetime.fromisoformat(session['end_time'])
                    except (ValueError, TypeError):
                        continue
                elif include_active:
                    s_end = now
                else:
                    continue

                clipped_start = max(s_start, start)
                clipped_end = min(s_end, end)
                if clipped_end <= clipped_start:
                    continue

                duration = (clipped_end - clipped_start).total_seconds()
                if duration <= 0:
                    continue

                session['clipped_start'] = clipped_start
                session['clipped_end'] = clipped_end
                session['duration_seconds'] = duration
                results.append(session)
            return results
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
        """取得指定時間範圍內的所有不重複程式名稱（DISTINCT，不載入全部列）"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """
                SELECT DISTINCT app_name FROM usage_sessions
                WHERE start_time < ?
                  AND (end_time IS NULL OR end_time > ?)
                  AND app_name IS NOT NULL
                  AND app_name != ''
                ORDER BY app_name COLLATE NOCASE
                """,
                (end.isoformat(), start.isoformat()),
            ).fetchall()
            return [r["app_name"] for r in rows]
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

    def close_all_open_sessions(self, max_orphan_seconds: float = 1200):
        """
        關閉所有未完成的 sessions（程式啟動/退出時使用）。
        若 orphan session 已開超過 max_orphan_seconds，視為異常殘留，
        不把停機時間算進使用時長（duration=0）。
        """
        conn = self._get_conn()
        try:
            now = datetime.now()
            rows = conn.execute(
                "SELECT id, start_time FROM usage_sessions WHERE end_time IS NULL"
            ).fetchall()
            for row in rows:
                start_time = datetime.fromisoformat(row['start_time'])
                age = (now - start_time).total_seconds()
                if age > max_orphan_seconds:
                    # 異常殘留：不記入使用時長
                    conn.execute(
                        """UPDATE usage_sessions
                           SET end_time = ?, duration_seconds = 0, is_idle_excluded = 1
                           WHERE id = ?""",
                        (start_time.isoformat(), row['id'])
                    )
                    logger.warning(
                        f"Discarded orphan session {row['id']} "
                        f"(open for {age/3600:.1f}h)"
                    )
                else:
                    duration = max(0.0, age)
                    conn.execute(
                        """UPDATE usage_sessions
                           SET end_time = ?, duration_seconds = ?
                           WHERE id = ?""",
                        (now.isoformat(), duration, row['id'])
                    )
            conn.commit()
        finally:
            self._release_conn(conn)

    def repair_inflated_sessions(self, max_hours: float = 8.0) -> int:
        """
        修復歷史異常超長 session（多半是重啟時把殘留 session 算到現在）。
        超過 max_hours 的 session 會被截斷為 20 分鐘並標記 is_idle_excluded。
        回傳修復筆數。
        """
        conn = self._get_conn()
        try:
            max_seconds = max_hours * 3600
            rows = conn.execute(
                """SELECT id, start_time, duration_seconds FROM usage_sessions
                   WHERE duration_seconds > ?""",
                (max_seconds,)
            ).fetchall()
            repaired = 0
            for row in rows:
                start_time = datetime.fromisoformat(row['start_time'])
                # 保守估計：只保留進入閒置門檻前的 20 分鐘
                capped = timedelta(minutes=20)
                end_time = start_time + capped
                conn.execute(
                    """UPDATE usage_sessions
                       SET end_time = ?, duration_seconds = ?, is_idle_excluded = 1
                       WHERE id = ?""",
                    (end_time.isoformat(), capped.total_seconds(), row['id'])
                )
                repaired += 1
            if repaired:
                conn.commit()
                logger.info(f"Repaired {repaired} inflated session(s) (> {max_hours}h)")
            return repaired
        finally:
            self._release_conn(conn)

    def update_session_url(self, session_id: int, url: str, window_title: str = ""):
        """更新 session 的 URL（來自瀏覽器擴充套件）"""
        conn = self._get_conn()
        try:
            updates = ["url = ?"]
            params: List[Any] = [url]
            if window_title:
                updates.append("window_title = ?")
                params.append(window_title)
            params.append(session_id)
            conn.execute(
                f"UPDATE usage_sessions SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
        finally:
            self._release_conn(conn)
