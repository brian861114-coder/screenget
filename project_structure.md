# Project Structure - screenget

```
screenget/
├── .git/                 # Git 版本管理
├── .gitignore            # Git 忽略檔案清單
├── .venv/                # Python 虛擬環境 (Git 忽略)
├── CHANGELOG.md          # 變更日誌
├── ScreenGet.spec        # PyInstaller 打包規格
├── ScreenGetHost.spec    # PyInstaller 宿主打包規格
├── browser_extension/    # 瀏覽器擴核套件原始碼
├── build/                # 編譯產出目錄
├── core/                 # 核心邏輯代碼
├── dist/                 # 發布、打包後的程式
├── example.pptx          # 範例檔案
├── native_messaging/     # 原生訊息傳遞配置 (與瀏覽器通訊)
├── requirements.txt      # Python 依賴清單
├── resources/            # 資源檔案 (圖示等)
├── ui/                   # 使用者介面代碼 (PyQt6)
├── main.py               # 程式進入點
├── update_history.md     # 更新歷史紀錄
├── project_structure.md  # 專案架構說明
└── 各類修復與安裝腳本 (*.py, *.ps1)
```
