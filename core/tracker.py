"""
tracker.py - 前景視窗追蹤引擎
使用 Windows API 偵測當前前景視窗，記錄各程式的使用時間。
"""

import ctypes  # 用於呼叫 Windows DLL (動態連結函式庫)
import ctypes.wintypes  # 定義 Windows 常用的資料型別 (如 DWORD, HANDLE)
import time  # 用於時間延遲或取得時間戳
import threading  # 用於多執行緒操作，讓追蹤在背景執行
import logging  # 用於記錄程式執行過程中的資訊 or 錯誤
from typing import Optional, Callable  # 用於型別提示，增加程式碼可讀性

import psutil  # 用於獲取系統程序 (Process) 的詳細資訊 (如名稱、路徑)

from core.database import UsageDatabase  # 匯入資料庫操作類別，用於儲存追蹤結果
from core.process_filter import ProcessFilter  # 匯入程序過濾類別，決定哪些程式需要追蹤

# 初始化日誌記錄器
logger = logging.getLogger(__name__)

# Windows API 定義：載入 user32.dll 與 kernel32.dll
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 從 DLL 中提取特定的 Windows 函式
GetForegroundWindow = user32.GetForegroundWindow  # 取得目前焦點視窗的控制代碼
GetWindowTextW = user32.GetWindowTextW  # 取得視窗的標題文字 (Unicode 版本)
GetWindowTextLengthW = user32.GetWindowTextLengthW  # 取得視窗標題的長度
GetWindowThreadProcessId = user32.GetWindowThreadProcessId  # 根據視窗控制代碼取得其所屬的程序 ID (PID)


def get_foreground_window_info() -> Optional[dict]:
    """
    實作細節：取得當前前景視窗的詳細資訊
    返回一個包含 hwnd, title, pid, process_name, exe_path 的字典，或是在失敗時返回 None
    """
    try:
        # 1. 取得當前焦點視窗的控制代碼 (句柄)
        hwnd = GetForegroundWindow()
        if not hwnd:
            # 如果沒有找到焦點視窗 (例如桌面剛好沒有任何視窗或是螢幕鎖定)，直接返回 None
            return None

        # 2. 取得視窗標題的長度，以便準備緩衝區
        length = GetWindowTextLengthW(hwnd)
        if length == 0:
            # 如果標題長度為 0，通常代表這不是一個具備標題的標準視窗，不進行記錄
            return None
        
        # 3. 建立一個 Unicode 緩衝區來接收標題文字
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value  # 取得緩衝區內的字串值

        # 4. 如果標題是空的或只有空白字元，則不記錄
        if not title.strip():
            return None

        # 5. 定義一個 DWORD 型別來儲存程序 ID (PID)
        pid = ctypes.wintypes.DWORD()
        # 透過視窗控制代碼 (hwnd)查詢該視窗所屬的程序 ID
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        pid_value = pid.value

        if pid_value == 0:
            # 如果無法取得有效的 PID，則返回 None
            return None

        # 6. 使用 psutil 庫根據 PID 獲取更詳細的程序資訊
        try:
            proc = psutil.Process(pid_value)
            process_name = proc.name()  # 執行檔名稱 (例: chrome.exe)
            exe_path = proc.exe()      # 執行檔的完整路徑
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # 如果程序不存在、無權限訪問或是殭屍程序，則無法獲取資訊
            return None

        # 7. 組裝並返回視窗資訊字典
        return {
            'hwnd': hwnd,           # 視窗控制代碼
            'title': title,         # 視窗標題
            'pid': pid_value,       # 程序 ID
            'process_name': process_name, # 程序名稱
            'exe_path': exe_path,    # 程式完整路徑
        }
    except Exception as e:
        # 捕捉任何非預期的錯誤並記錄到日誌
        logger.error(f"Error getting foreground window: {e}")
        return None


class UsageTracker:
    """
    使用量追蹤器類別
    核心邏輯：在背景執行緒中持續輪詢 (Polling) 前景視窗，並與資料庫互動記錄使用時間。
    """

    def __init__(self, db: UsageDatabase, poll_interval: float = 1.0):
        """
        初始化追蹤器
        :param db: 資料庫物件，用於寫入記錄
        :param poll_interval: 輪詢間隔秒數 (預設 1 秒)
        """
        self.db = db
        self.poll_interval = poll_interval
        self._running = False  # 控制追蹤執行緒是否應該繼續運行的旗標
        self._paused = False   # 是否處於暫停狀態 (例如使用者閒置時)
        self._thread: Optional[threading.Thread] = None  # 背景執行緒實例
        self._current_session_id: Optional[int] = None   # 目前正在記錄的資料庫 Session ID
        self._current_app: Optional[str] = None          # 目前追蹤的程式顯示名稱
        self._current_title: Optional[str] = None        # 目前追蹤的視窗標題
        
        # 使用可重入鎖 (RLock) 以確保多執行緒安全，且允許同一個執行緒多次獲得同一個鎖
        # 這可以避免死結狀況，特別是在呼叫 pause() 與結束 session 之間
        self._lock = threading.RLock()
        self._on_app_change: Optional[Callable] = None  # 當視窗切換時要呼叫的回呼函式

    def set_on_app_change(self, callback: Callable):
        """
        設定視窗切換時的回呼函式，通常用於 UI 更新
        :param callback: 函式簽名應為 (app_name, title, app_type)
        """
        self._on_app_change = callback

    def start(self):
        """
        啟動追蹤引擎
        會建立一個守護執行緒 (Daemon Thread) 來執行追蹤迴圈
        """
        if self._running:
            return  # 如果已經在運行則直接返回
        
        self._running = True
        self._paused = False
        # 建立執行緒：目標設定為 _tracking_loop，並標記為守護執行緒
        self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._thread.start()
        logger.info("Tracker started")

    def stop(self):
        """
        停止追蹤引擎
        """
        self._running = False  # 設定旗標讓迴圈結束
        if self._thread:
            self._thread.join(timeout=5)  # 等待執行緒結束，最多等 5 秒
        self._end_current_session()  # 停止時務必關閉當前的 session 記錄
        logger.info("Tracker stopped")

    def pause(self, idle_start_time=None):
        """
        暫停追蹤
        通常在偵測到使用者一段時間沒操作 (閒置) 時會被呼叫
        :param idle_start_time: 閒置開始的時間點
        """
        with self._lock:
            if not self._paused:
                self._paused = True
                self._end_current_session(end_time=idle_start_time)
                logger.info("Tracker paused (idle)")

    def resume(self):
        """
        恢復追蹤
        當偵測到使用者重新開始操作時呼叫
        """
        with self._lock:
            if self._paused:
                self._paused = False
                logger.info("Tracker resumed")

    @property
    def is_paused(self) -> bool:
        """回傳目前是否處於暫停狀態"""
        return self._paused

    @property
    def is_running(self) -> bool:
        """回傳目前是否正在運行追蹤"""
        return self._running

    def _tracking_loop(self):
        """
        背景追蹤主迴圈 (核心邏輯)
        這是一個 while 迴圈，會根據 poll_interval 定時檢查一次前景視窗
        """
        while self._running:
            try:
                # 檢查是否暫停，如果暫停則持續等待但不執行檢查邏輯
                with self._lock:
                    if self._paused:
                        time.sleep(self.poll_interval)
                        continue

                # 呼叫外部函式取得當前前景視窗資訊
                info = get_foreground_window_info()
                if info:
                    # 如果有取得資訊，交給處理函式判斷是否需要切換記錄
                    self._handle_window_change(info)

            except Exception as e:
                # 記錄迴圈中的任何錯誤，確保追蹤執行緒不會因為單次錯誤而崩潰退出
                logger.error(f"Tracking error: {e}")

            # 根據設定的間隔時間進行休眠，避免過度消耗 CPU
            time.sleep(self.poll_interval)

    def _handle_window_change(self, info: dict):
        """
        處理視窗切換事件
        判斷目前的視窗是否與上一次記錄的視窗相同，或是是否符合過濾條件
        """
        process_name = info['process_name']
        window_title = info['title']
        exe_path = info['exe_path']

        # 1. 檢查此程式是否在黑名單中，或者是否屬於系統關鍵程序
        if not ProcessFilter.should_track(process_name, exe_path):
            # 如果切換到了不應該追蹤的程式 (例: 工作管理員、桌面)，則結束目前正在記錄的 session
            if self._current_app is not None:
                self._end_current_session()
                self._current_app = None
                self._current_title = None
            return

        # 2. 取得漂亮的程式顯示名稱 (例: Chrome) 與程式分類 (例: 瀏覽器)
        display_name = ProcessFilter.get_display_name(process_name, window_title)
        app_type = ProcessFilter.get_app_type(process_name, exe_path)

        # 3. 檢查是否跟目前的 session 是一致的：
        # 如果顯示名稱與視窗標題都沒變，表示使用者還在看同一個畫面，不需要做任何事
        if display_name == self._current_app and window_title == self._current_title:
            return

        # 4. 到這裡代表偵測到了「有效的切換」 (切換了程式或切換了標題/分頁)
        # 先結束舊的 session
        self._end_current_session()

        # 5. 開始一個新的資料庫 session
        with self._lock:
            self._current_app = display_name
            self._current_title = window_title
            # 在資料庫中插入一筆新的紀錄，並取得其 ID
            self._current_session_id = self.db.start_session(
                app_name=display_name,
                window_title=window_title,
                exe_path=exe_path,
                app_type=app_type,
            )
            logger.debug(f"New session: {display_name} - {window_title}")

            # 6. 如果有註冊回呼函式 (例如 UI 要更新)，則呼叫它
            if self._on_app_change:
                try:
                    self._on_app_change(display_name, window_title, app_type)
                except Exception as e:
                    logger.error(f"App change callback error: {e}")

    def _end_current_session(self, end_time=None):
        """
        在資料庫中結束目前的 session
        會更新結束時間戳，並計算總使用時數
        """
        with self._lock:
            if self._current_session_id is not None:
                try:
                    # 調用資料庫物件來終止 session 紀錄
                    self.db.end_session(self._current_session_id, end_time=end_time)
                except Exception as e:
                    logger.error(f"Error ending session: {e}")
                # 清除目前持有的 session ID，避免重複結束
                self._current_session_id = None


    def update_browser_url(self, url: str, title: str = ""):
        """
        更新當前瀏覽器 session 的 URL
        這通常是由「瀏覽器擴充套件」透過 Native Messaging 傳回 URL 時呼叫的。
        讓我們能記錄下具体的網站網址而不只是視窗標題。
        """
        with self._lock:
            if self._current_session_id is not None:
                try:
                    # 在資料庫中更新該 session 的 URL 欄位
                    self.db.update_session_url(self._current_session_id, url, title)
                except Exception as e:
                    logger.error(f"Error updating URL: {e}")
