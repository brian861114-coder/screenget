# screenget

## 中文

`screenget` 是一個 Windows 桌面使用行為追蹤工具，目標是記錄前景視窗 / App 使用時間，並提供本地分析、系統匣控制與桌面儀表板。

### 核心能力
- 追蹤目前前景視窗與對應行程
- 自動記錄 App 使用時間
- 閒置偵測與自動暫停 / 恢復
- 本地資料庫儲存與歷史清理
- PyQt6 桌面儀表板
- 系統匣操作
- 專案中也包含 `browser_extension` 與 `native_messaging`，顯示它有擴充到瀏覽器整合的方向

### 主要檔案與模組
- `main.py`: 應用程式入口
- `core/tracker.py`: 使用 Windows API 追蹤前景視窗
- `core/database.py`: 使用資料儲存
- `core/analyzer.py`: 分析邏輯
- `ui/`: 主視窗與系統匣 UI
- `browser_extension/`, `native_messaging/`: 延伸整合元件

### 技術棧
- Python
- PyQt6
- Windows API (`ctypes`)
- `psutil`
- `matplotlib`

### 專案定位
這不是雲端 SaaS，而是偏本機優先的 Windows 生產力工具。它的重點在於個人使用資料蒐集與可視化，而不是多人同步或遠端服務。

## English

`screenget` is a Windows desktop usage-tracking application focused on recording foreground app / window time and presenting the data through local analytics, a system tray controller, and a desktop dashboard.

### Core capabilities
- Track the current foreground window and process
- Record app usage time locally
- Detect idle state and automatically pause / resume tracking
- Store history in a local database and clean old data
- Provide a PyQt6 dashboard
- Offer system tray controls
- Include `browser_extension` and `native_messaging`, indicating browser-integration work

### Key files and modules
- `main.py`: application entry point
- `core/tracker.py`: foreground-window tracking via Windows APIs
- `core/database.py`: storage layer
- `core/analyzer.py`: analysis logic
- `ui/`: main window and tray UI
- `browser_extension/`, `native_messaging/`: integration components

### Tech stack
- Python
- PyQt6
- Windows API via `ctypes`
- `psutil`
- `matplotlib`

### Project positioning
This is a local-first Windows productivity tool rather than a cloud SaaS product. Its center of gravity is personal usage tracking and visualization.