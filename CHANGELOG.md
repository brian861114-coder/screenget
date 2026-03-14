# Changelog - ScreenGet

所有本專案的重大變更將記錄在此檔案中。

## [2026-03-14] - Chart Fixes & Connectivity Improvement

### 🎨 介面優化 (UI/UX)
- **修正圖表亂碼 (Chart Mojibake Fixed)**：
    - 在 `ui/charts.py` 中引入中文字體設定，優先使用「微軟正黑體 (Microsoft JhengHei)」，解決 Windows 系統下圖表標籤顯示為方塊的問題。
    - 更新「24 小時使用分布」圖表標籤：橫軸由「小時」改為「**當日時間**」，縱軸由「分鐘」改為「**使用比例**」。

### 🔧 修復與改進 (Fixed & Improved)
- **解決 Native Messaging 路徑問題**：
    - 針對專案目錄包含中文字元導致瀏覽器橋樑啟動失敗的問題，引入 **Windows 短路徑 (8.3 Path)** 技術。
    - 重構註冊流程：新增 `fix_host_shortpath.py` 工具，確保 Chrome 能夠透過純英文路徑格式穩定啟動 `native_host.py`。
    - 修正 `com.screenget.host.json` 的編碼問題，確保 UTF-8 JSON 格式被 Chrome 正確解析。
- **診斷工具升級**：
    - 在 `native_host.py` 中新增詳細的偵錯日誌，追蹤 Python 執行環境、資料庫路徑與訊息交換過程。

## [2026-03-13] - Packaging & Distribution

### ✨ 新增功能 (Added)
- **執行檔封裝 (Executable)**：
    - 將主程式打包成 `ScreenGet.exe`，支援在無 Python 環境下獨立執行。
    - 將瀏覽器橋樑打包成 `ScreenGetHost.exe`，提升瀏覽器統計的穩定性。
- **維護與部署工具**：
    - 新增 `install_host.ps1` 自動註冊指令碼，簡化瀏覽器 Native Messaging 的設定過程。
    - 提供全新的「使用說明.md」文檔，優化使用者初次安裝體驗。
- **資源路徑自動轉換**：在 `main.py` 引入 `resource_path` 機制，確保打包後的圖示與外部資源路徑正確無誤。

### 🎨 介面優化 (UI/UX)
- **核心監控引擎**：實作基於 Windows API 的前景視窗追蹤與閒置偵測（20 分鐘超時）。
- **資料庫架構**：建立 SQLite 基於 Session 的儲存機制，記錄應用程式與網頁的使用起止時間。
- **瀏覽器追蹤**：開發 Chrome 擴充套件，透過 Native Messaging 與桌面端連動，支援追蹤具體 URL。
- **內部頁面追蹤**：擴展監控範圍至瀏覽器內部頁面（如 `chrome://settings`, `chrome://history`）。
- **視覺化儀表板**：
    - 使用總覽頁面：統計今日/本週/本月的使用數據。
    - 軟體分析頁面：針對單一應用程式的歷史趨勢分析。
    - **瀏覽器分析頁面**（新增）：專屬的網站造訪排行與趨勢統計。
- **多維度圖表**：整合 Matplotlib 繪製時間段長條圖、24 小時分佈圖、使用排行圖與每日趨勢圖。

### 🎨 介面優化 (UI/UX)
- **全新視覺主題**：將原有的深色模式全面改版為以 `#D7F5F2` (淺青色) 為底色的清新風格。
- **品牌圖示 (Branding)**：設計並實作了專屬的可愛風「視窗 + 沙漏」應用程式圖示，應用於系統匣與主視窗。
- **配色系統**：採用淺藍 (`#A2D2FF`)、淺綠 (`#B9FBC0`)、純白與純黑打造高對比且柔和的 UI。
- **圖表佈局**：更新所有圖表為「粉彩系列」配色，並優化滾動區域的捲軸樣式。

### 🔧 修復與改進 (Fixed & Improved)
- **資料庫連線修正**：解決 SQLite 在 `:memory:` 模式下因連線重複開啟導致資料表消失的問題。
- **Session 釋放機制**：引入 `_release_conn` 方法，確保在不關閉持續性連線的情況下妥善處理資料操作。
- **擴充套件載入修正**：移除 `manifest.json` 中缺失的圖示引用，解決無法載入擴充功能的問題。
- **域名識別優化**：改進 `native_host.py` 的解析邏輯，更精確地識別與分類內部瀏覽器頁面。
