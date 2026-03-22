# tracker.py 多執行緒完整詳細說明

---

## 一、架構概觀

```
主執行緒 (Main Thread)
│
├── UsageTracker.start()  ──建立──►  背景執行緒 (_tracking_loop)
│                                        │
│                                        ├── 每 1 秒輪詢前景視窗
│                                        ├── 檢查 _running 旗標
│                                        └── 檢查 _paused 旗標
│
├── UsageTracker.pause()  ──設旗標──►  執行緒繼續跑但略過偵測
├── UsageTracker.resume() ──清旗標──►  執行緒恢復偵測
└── UsageTracker.stop()   ──清旗標──►  執行緒自然退出迴圈
```

整個設計是「**單一背景執行緒 + 旗標控制**」的模式，主執行緒透過修改共享狀態來指揮背景執行緒的行為。

---

## 二、狀態變數的角色

```python
# 第 82-89 行
self._running = False          # 執行緒是否應該繼續存活
self._paused = False           # 執行緒是否應該暫停偵測
self._thread = None            # 背景執行緒的參考 (handle)
self._current_session_id = None  # 資料庫中當前 session 的 ID
self._current_app = None       # 當前追蹤的應用程式名稱
self._current_title = None     # 當前追蹤的視窗標題
self._lock = threading.RLock() # 保護上述共享狀態的鎖
```

這些變數**同時被主執行緒與背景執行緒存取**，因此需要鎖來保護。

---

## 三、執行緒開啟 `start()` 深入解析

```python
# 第 96-104 行
def start(self):
    if self._running:       # 防止重複啟動
        return
    self._running = True
    self._paused = False
    self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
    self._thread.start()
    logger.info("Tracker started")
```

### 重點細節

**① 防重複啟動保護**
```python
if self._running:
    return
```
若執行緒已在執行中，直接返回，避免同時存在兩個追蹤迴圈造成資料重複寫入。

**② `daemon=True` 的意義**
```python
threading.Thread(target=self._tracking_loop, daemon=True)
```

| 屬性 | 行為 |
|---|---|
| `daemon=True` | 主程式（視窗）關閉時，此執行緒**自動終止**，不阻擋程式退出 |
| `daemon=False`（預設）| 主程式會**等待**此執行緒結束才退出，可能導致程式無法關閉 |

因為追蹤迴圈是無限迴圈，若不設為 daemon，使用者關閉視窗後程式會卡住無法退出。

**③ `target=self._tracking_loop`**
將實例方法作為執行緒目標，背景執行緒啟動後會呼叫 `self._tracking_loop()`，此方法可以存取 `self` 的所有狀態。

---

## 四、執行緒主迴圈 `_tracking_loop()` 深入解析

```python
# 第 137-153 行
def _tracking_loop(self):
    while self._running:              # ← 存活條件
        try:
            with self._lock:
                if self._paused:      # ← 暫停檢查（在鎖內）
                    time.sleep(self.poll_interval)
                    continue

            info = get_foreground_window_info()   # ← 在鎖外執行（耗時操作）
            if info:
                self._handle_window_change(info)

        except Exception as e:
            logger.error(f"Tracking error: {e}")  # ← 捕捉異常避免執行緒崩潰

        time.sleep(self.poll_interval)   # ← 每輪結束後 sleep 1 秒
```

### 重點細節

**① `while self._running` — 旗標式退出**

這是標準的「協作式退出 (cooperative shutdown)」模式：
- 背景執行緒**主動**在每次迴圈開頭檢查旗標
- 主執行緒只需設定 `_running = False`，不需要強制殺死執行緒
- 相比 `thread.kill()` 等強制方法，此方式可確保資源（資料庫連線、session 記錄）被正確清理

**② 鎖的範圍刻意最小化**

```python
# 只在鎖內檢查 _paused 旗標
with self._lock:
    if self._paused:
        time.sleep(self.poll_interval)
        continue

# 耗時的 Windows API 呼叫在鎖外執行
info = get_foreground_window_info()
```

`get_foreground_window_info()` 涉及 Windows API 呼叫與 psutil 查詢，執行時間不固定。若將其放在鎖內，主執行緒（UI）呼叫 `pause()` 或 `resume()` 時會被迫等待，造成 UI 卡頓。

**③ `try/except` 保護執行緒不崩潰**

```python
except Exception as e:
    logger.error(f"Tracking error: {e}")
```

若偵測過程中出現任何未預期錯誤（例如 Windows API 回傳異常值），執行緒**不會崩潰退出**，而是記錄錯誤後繼續下一輪迴圈。這是長期背景執行緒的重要設計原則。

**④ `time.sleep(self.poll_interval)` 的位置**

```python
        time.sleep(self.poll_interval)  # 在 try/except 之外
```

sleep 在 `try/except` 區塊**外部**，確保即使發生錯誤也一定會等待 1 秒再重試，避免錯誤時進入瘋狂重試迴圈（busy-wait）吃滿 CPU。

---

## 五、執行緒關閉 `stop()` 深入解析

```python
# 第 106-112 行
def stop(self):
    self._running = False              # ① 通知執行緒停止
    if self._thread:
        self._thread.join(timeout=5)   # ② 等待執行緒確實結束
    self._end_current_session()        # ③ 清理資料庫 session
    logger.info("Tracker stopped")
```

### 關閉的三個階段

```
主執行緒                          背景執行緒
   │                                  │
   ├─ _running = False                │  (正在 sleep 1 秒)
   │                                  │
   ├─ thread.join(timeout=5) ──等待──►│  sleep 結束
   │        │                         ├─ while self._running → False
   │        │                         ├─ 退出迴圈
   │        │◄──────────── 執行緒結束 ┘
   │        │
   ├─ _end_current_session()  (安全地關閉最後一筆資料庫記錄)
   │
   └─ 完成
```

**① `_running = False`**
旗標翻轉後，背景執行緒在當次 `sleep` 結束後會發現 `while self._running` 為 False，自然退出。

**② `thread.join(timeout=5)`**
主執行緒等待背景執行緒真正結束。`timeout=5` 是安全措施：
- 最多等 5 秒，不會永久阻塞主執行緒
- 若 5 秒後執行緒還沒結束（理論上不應該發生），主執行緒繼續往下執行
- **若沒有 join**：主執行緒可能在執行緒還在寫入資料庫時就繼續跑 `_end_current_session()`，導致 race condition

**③ `_end_current_session()` 在 join 之後**
確保背景執行緒完全停止後，才由主執行緒去關閉最後一筆 session，避免兩個執行緒同時操作同一個 session_id。

---

## 六、鎖機制 `threading.RLock` 深入解析

### 為什麼不用普通 `Lock`？

```
呼叫鏈分析：

pause()
  └─► with self._lock:          ← 第一次取鎖
        └─► _end_current_session()
              └─► with self._lock:   ← 同一執行緒第二次取鎖
```

| 鎖類型 | 同執行緒第二次取鎖 | 結果 |
|---|---|---|
| `threading.Lock` | **死結** ─ 等待自己釋放 | 程式卡住 |
| `threading.RLock` | 成功，計數器 +1 | 正常執行 |

### RLock 的計數器機制

```
pause() 執行緒：
  acquire() → 計數器 = 1
    _end_current_session()
      acquire() → 計數器 = 2   ← RLock 允許，Lock 會卡死
      release() → 計數器 = 1
  release() → 計數器 = 0  ← 其他執行緒現在可以取鎖
```

### 哪些地方受鎖保護？

```python
# _tracking_loop 中：檢查暫停狀態
with self._lock:
    if self._paused: ...

# _handle_window_change 中：寫入新 session 資訊
with self._lock:
    self._current_app = display_name
    self._current_session_id = self.db.start_session(...)

# _end_current_session 中：讀取並清除 session_id
with self._lock:
    if self._current_session_id is not None:
        self.db.end_session(self._current_session_id)
        self._current_session_id = None

# pause / resume / update_browser_url：修改共享狀態
with self._lock: ...
```

---

## 七、暫停/恢復的設計哲學

```python
def pause(self, idle_start_time=None):    # 第 114 行
    with self._lock:
        if not self._paused:
            self._paused = True
            self._end_current_session(end_time=idle_start_time)

def resume(self):                          # 第 122 行
    with self._lock:
        if self._paused:
            self._paused = False
```

**為何不停止再重啟執行緒？**

| 方案 | 優點 | 缺點 |
|---|---|---|
| 停止再重啟執行緒 | 完全停止資源占用 | 建立執行緒有開銷；狀態難以保留 |
| 設 `_paused` 旗標（現行方案） | 輕量；狀態保留；恢復快速 | 執行緒仍在跑（但只是 sleep） |

閒置偵測會頻繁觸發 pause/resume，用旗標方式更適合這種短暫、頻繁的暫停需求。

---

## 八、整體執行緒生命週期圖

```
                    start()
                      │
                      ▼
            ┌─────────────────┐
            │  _running=True  │
            │  daemon thread  │◄──────────────────┐
            │  開始執行        │                   │
            └────────┬────────┘                   │
                     │                            │
            ┌────────▼────────┐                   │
            │  while running  │──False──► 退出迴圈 │
            └────────┬────────┘                   │
                     │True                        │
            ┌────────▼────────┐                   │
            │  paused?        │──Yes──► sleep ─────┘
            └────────┬────────┘
                     │No
            ┌────────▼────────┐
            │ 偵測前景視窗     │
            └────────┬────────┘
                     │
            ┌────────▼────────┐
            │ 視窗有變化?      │──No──► sleep ──────┐
            └────────┬────────┘                    │
                     │Yes                          │
            ┌────────▼────────┐                    │
            │ 結束舊 session   │                    │
            │ 開始新 session   │                    │
            └────────┬────────┘                    │
                     │                             │
                   sleep ◄───────────────────────── ┘
                     │
                  （下一輪）


          stop() 呼叫時：
            _running = False → 執行緒在下次迴圈開頭退出
            thread.join()   → 主執行緒等待確認
            _end_session()  → 清理最後一筆記錄
```

---

## 九、總結

| 機制 | 技術 | 目的 |
|---|---|---|
| 執行緒建立 | `Thread(daemon=True)` | 主程式關閉時自動終止 |
| 存活控制 | `_running` 旗標 | 協作式退出，確保資源清理 |
| 暫停控制 | `_paused` 旗標 | 閒置時停止偵測但保留執行緒 |
| 優雅關閉 | `thread.join(timeout=5)` | 等待執行緒結束再清理資料 |
| 競態保護 | `RLock` | 防止多執行緒同時修改 session 狀態 |
| 重入保護 | `RLock`（非 `Lock`）| 防止 pause→end_session 的巢狀鎖死結 |
| 執行緒穩健性 | `try/except` 包裹迴圈 | 錯誤時繼續執行而非崩潰退出 |
