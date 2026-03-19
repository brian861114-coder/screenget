"""
settings_manager.py - 設定管理模組
負責載入、儲存應用程式設定（語言、自動執行、白名單）。
"""

import json
import os
import sys
import logging

logger = logging.getLogger(__name__)

class SettingsManager:
    """設定管理類別"""
    
    def __init__(self):
        self.app_data = os.path.join(os.getenv('APPDATA', ''), 'ScreenGet')
        os.makedirs(self.app_data, exist_ok=True)
        self.settings_path = os.path.join(self.app_data, 'settings.json')
        
        # 預設設定
        self.settings = {
            'language': 'zh_TW',  # zh_TW, en_US, ja_JP
            'autostart': False,
            'whitelist': []  # 排除列表 (app_name 或 domain)
        }
        self.load_settings()

    def load_settings(self):
        """從檔案載入設定"""
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self.settings.update(saved)
            except Exception as e:
                logger.error(f"載入設定失敗: {e}")

    def save_settings(self):
        """儲存設定到檔案"""
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            
            # 處理開機啟動
            self._handle_autostart_registry()
        except Exception as e:
            logger.error(f"儲存設定失敗: {e}")

    def _handle_autostart_registry(self):
        """處理 Windows 註冊表以實現開機啟動"""
        if sys.platform != 'win32':
            return
        
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "ScreenGet"
        
        # 取得目前執行檔路徑 (如果不適打包後的 exe，則使用 python 路徑 + 脚本路徑，但通常建議打包後再用)
        if getattr(sys, 'frozen', False):
            # 打包後的 exe
            exe_path = sys.executable
        else:
            # 開發環境下指向 main.py
            executable = sys.executable
            # 在 Windows 上嘗試使用 pythonw.exe 以隱藏主控台
            if sys.platform == 'win32' and executable.lower().endswith('python.exe'):
                pw = executable.lower().replace('python.exe', 'pythonw.exe')
                if os.path.exists(pw):
                    executable = pw
            
            exe_path = f'"{executable}" "{os.path.abspath(sys.argv[0])}"'

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if self.settings.get('autostart'):
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                    except FileNotFoundError:
                        pass
        except Exception as e:
            logger.error(f"設定開機啟動失敗: {e}")

    def is_whitelisted(self, name: str) -> bool:
        """檢查是否在白名單中"""
        whitelist = self.settings.get('whitelist', [])
        return name in whitelist

    def add_to_whitelist(self, name: str):
        """加入白名單"""
        if name and name not in self.settings['whitelist']:
            self.settings['whitelist'].append(name)
            self.save_settings()

    def remove_from_whitelist(self, name: str):
        """移除白名單"""
        if name in self.settings['whitelist']:
            self.settings['whitelist'].remove(name)
            self.save_settings()

    def get_language(self):
        return self.settings.get('language', 'zh_TW')

    def set_language(self, lang: str):
        self.settings['language'] = lang
        self.save_settings()

    def set_autostart(self, enabled: bool):
        self.settings['autostart'] = enabled
        self.save_settings()
