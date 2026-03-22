# Update History - screenget

## [2026-03-18]
- 建立 Python 虛擬環境 (`.venv`) 以隔離專案依賴。
- 安裝必要依賴套件：`PyQt6` (6.10.2), `psutil` (7.2.2), `matplotlib` (3.10.8)。
- 更新 `setup_guide.md` 以記錄虛擬環境啟動方式。
- 準備將專案推送到 GitHub。

## [2026-03-19]
- 修正儀表板日期切換與圖表刷新 Bug
- 修正跨日 Session 計時數據溢流問題
- 解決閒置偵測 (Idle Detection) 之線程死結 (Deadlock) 與虛胖時數
- 優化虛幻/統一引擎之遊戲名稱識別 (例如：鳴潮)
- 更新日曆為 Style 1 現代極簡潮流風格
- 建立「歷史問題與解決.md」紀錄文件

## [2026-03-19] (Bug Fixes)
- **修復 Bug 1 (Dashboard)**: 修正特定程式篩選時圖表日期寫死為今日的問題。
- **修復 Bug 2 (IdleDetector)**: 修正閒置開始時間計算邏輯，確保暫停時間戳記準確。
- **修復 Bug 3 (NativeHost)**: 在程式結束時正確關閉資料庫連線，確保 WAL 回寫。
- **修復 Bug 4 (Settings)**: 使用上下文管理器 (`with`) 保護註冊表操作，防止 Handle 洩漏。
- **修復 Bug 5 (Dashboard)**: 簡化週/月篩選之冗餘條件判斷。
- **修復 Bug 6 (Database)**: 調整持續時間過濾邏輯（`> 0` 改為 `>= 0`）以包含最短有效 session。
- **修復 Bug 7 (Database)**: 加入 `timeout=10` 參數，防止多進程同時存取時的鎖定錯誤。
- **修復 Bug 8 (ProcessFilter)**: 在 `get_display_name` 加入回退機制，防止回傳空字串。

## [2026-03-19] (性能優化)
- **Matplotlib 記憶體管理**: 在 Chart 類別加入 `__del__` 方法以釋放資源。
- **Dashboard 介面優化**:
    - 新增載入中的等候游標與 `QApplication.processEvents()`。
    - 大幅優化日曆元件的日期格式化效率（從 366 次調用減至 ~10 次）。
    - 抽取靜態樣式為常數以提高可維護性。
- **核心分析效能優化**:
    - 資料庫 `get_sessions_in_range` 支持 SQL 層級的 `app_type` 篩選。
    - 分析器改用 SQL 篩選以減少 Python 處理負擔與記憶體佔用。
- **瀏覽器擴充套件優化**:
    - 為 `onUpdated` 事件加入 300ms debounce (節流) 機制，減少重複處理。
- **代碼風格**: 統一各模組的 logger 定義與調用方式。

## [2026-03-22]
- **代碼文件化**: 為 `core/tracker.py` 加入極詳細的中文註解，涵蓋 Windows API 調用、多執行緒邏輯、視窗資訊取得流程及資料庫 Session 管理機制。
