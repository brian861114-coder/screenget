"""
settings_manager.py - 設定管理模組
負責載入、儲存應用程式設定（語言、自動執行、白名單、閒置、分類、擴充套件）。
"""

import json
import os
import sys
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = ["工作", "娛樂", "通訊", "瀏覽", "遊戲", "其他"]

# 常見應用預設分類
DEFAULT_CATEGORY_MAP = {
    "Cursor": "工作",
    "Code": "工作",
    "Obsidian": "工作",
    "Notion": "工作",
    "Excel": "工作",
    "WINWORD": "工作",
    "POWERPNT": "工作",
    "ChatGPT": "工作",
    "Hermes": "工作",
    "JobTracker": "工作",
    "github.com": "工作",
    "GitHub": "工作",
    "Discord": "通訊",
    "Telegram": "通訊",
    "Slack": "通訊",
    "LINE": "通訊",
    "Steam": "遊戲",
    "bilibili": "娛樂",
    "bilibili.com": "娛樂",
    "YouTube": "娛樂",
    "youtube.com": "娛樂",
    "Netflix": "娛樂",
    "Spotify": "娛樂",
}


class SettingsManager:
    """設定管理類別"""

    def __init__(self):
        self.app_data = os.path.join(os.getenv("APPDATA", ""), "ScreenGet")
        os.makedirs(self.app_data, exist_ok=True)
        self.settings_path = os.path.join(self.app_data, "settings.json")

        self.settings = {
            "language": "zh_TW",
            "autostart": False,
            "whitelist": [],
            "idle_timeout_minutes": 20,
            "categories": list(DEFAULT_CATEGORIES),
            "category_map": dict(DEFAULT_CATEGORY_MAP),
            "extension_id": "eociggeoliljeoidbbhkeoelaainhkcp",
            "duration_unit": "auto",  # auto | hours | minutes
            "font_size": "medium",  # small | medium | large | xlarge
        }
        self.load_settings()

    def load_settings(self):
        """從檔案載入設定"""
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.settings.update(saved)
                # 合併預設分類對應（不覆蓋使用者已設值）
                merged = dict(DEFAULT_CATEGORY_MAP)
                merged.update(self.settings.get("category_map") or {})
                self.settings["category_map"] = merged
                if not self.settings.get("categories"):
                    self.settings["categories"] = list(DEFAULT_CATEGORIES)
            except Exception as e:
                logger.error(f"載入設定失敗: {e}")

    def save_settings(self):
        """儲存設定到檔案"""
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            self._handle_autostart_registry()
        except Exception as e:
            logger.error(f"儲存設定失敗: {e}")

    def _handle_autostart_registry(self):
        """處理 Windows 註冊表以實現開機啟動"""
        if sys.platform != "win32":
            return

        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "ScreenGet"

        if getattr(sys, "frozen", False):
            exe_path = sys.executable
        else:
            executable = sys.executable
            if sys.platform == "win32" and executable.lower().endswith("python.exe"):
                pw = executable.lower().replace("python.exe", "pythonw.exe")
                if os.path.exists(pw):
                    executable = pw
            exe_path = f'"{executable}" "{os.path.abspath(sys.argv[0])}"'

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
            )
            if self.settings.get("autostart"):
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"設定開機啟動失敗: {e}")

    def is_whitelisted(self, name: str) -> bool:
        whitelist = self.settings.get("whitelist", [])
        return name in whitelist

    def add_to_whitelist(self, name: str):
        if name and name not in self.settings["whitelist"]:
            self.settings["whitelist"].append(name)
            self.save_settings()

    def remove_from_whitelist(self, name: str):
        if name in self.settings["whitelist"]:
            self.settings["whitelist"].remove(name)
            self.save_settings()

    def get_language(self):
        return self.settings.get("language", "zh_TW")

    def set_language(self, lang: str):
        self.settings["language"] = lang
        self.save_settings()

    def set_autostart(self, enabled: bool):
        self.settings["autostart"] = enabled
        self.save_settings()

    def get_idle_timeout_minutes(self) -> int:
        try:
            value = int(self.settings.get("idle_timeout_minutes", 20))
            return max(1, min(value, 240))
        except (TypeError, ValueError):
            return 20

    def set_idle_timeout_minutes(self, minutes: int):
        self.settings["idle_timeout_minutes"] = max(1, min(int(minutes), 240))
        self.save_settings()

    def get_categories(self) -> List[str]:
        cats = self.settings.get("categories") or list(DEFAULT_CATEGORIES)
        return list(cats)

    def get_category_map(self) -> Dict[str, str]:
        return dict(self.settings.get("category_map") or {})

    def set_category(self, name: str, category: str):
        if not name:
            return
        if category not in self.get_categories():
            self.settings.setdefault("categories", list(DEFAULT_CATEGORIES)).append(category)
        self.settings.setdefault("category_map", {})[name] = category
        self.save_settings()

    def get_category(self, name: str, app_type: Optional[str] = None) -> str:
        """取得名稱對應分類；無對應時依 app_type 推斷"""
        mapping = self.settings.get("category_map") or {}
        if name in mapping:
            return mapping[name]
        # 僅做精確不區分大小寫匹配，避免過寬模糊（如短 key）
        lower = (name or "").lower()
        for key, cat in mapping.items():
            if key.lower() == lower:
                return cat
        if app_type == "browser":
            return "瀏覽"
        if app_type == "game":
            return "遊戲"
        return "其他"

    def get_extension_id(self) -> str:
        return self.settings.get("extension_id") or "eociggeoliljeoidbbhkeoelaainhkcp"

    def set_extension_id(self, extension_id: str):
        self.settings["extension_id"] = (extension_id or "").strip()
        self.save_settings()

    def get_duration_unit(self) -> str:
        unit = self.settings.get("duration_unit", "auto")
        return unit if unit in ("auto", "hours", "minutes") else "auto"

    def set_duration_unit(self, unit: str):
        if unit not in ("auto", "hours", "minutes"):
            unit = "auto"
        self.settings["duration_unit"] = unit
        self.save_settings()

    def get_font_size(self) -> str:
        size = self.settings.get("font_size", "medium")
        return size if size in ("small", "medium", "large", "xlarge") else "medium"

    def set_font_size(self, size: str):
        if size not in ("small", "medium", "large", "xlarge"):
            size = "medium"
        self.settings["font_size"] = size
        self.save_settings()
