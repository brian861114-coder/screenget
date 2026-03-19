"""
process_filter.py - 程式過濾器
負責過濾系統背景程式，只追蹤使用者的遊戲、瀏覽器和一般應用程式。
"""

import os
from typing import Optional

# Windows 系統程式 - 不追蹤
SYSTEM_PROCESSES = {
    # Windows 核心
    'explorer.exe', 'searchui.exe', 'searchapp.exe',
    'shellexperiencehost.exe', 'startmenuexperiencehost.exe',
    'systemsettings.exe', 'applicationframehost.exe',
    'lockapp.exe', 'logonui.exe', 'dwm.exe', 'csrss.exe',
    'smss.exe', 'wininit.exe', 'winlogon.exe', 'services.exe',
    'lsass.exe', 'svchost.exe', 'taskhostw.exe', 'sihost.exe',
    'fontdrvhost.exe', 'ctfmon.exe', 'conhost.exe',
    'runtimebroker.exe', 'dllhost.exe', 'audiodg.exe',
    'securityhealthsystray.exe', 'securityhealthservice.exe',
    'textinputhost.exe', 'widgetservice.exe', 'widgets.exe',
    'gamebarpresencewriter.exe', 'gamebar.exe',
    'phoneexperiencehost.exe', 'yourphone.exe',
    'windowsterminal.exe',

    # Windows 更新與維護
    'trustedinstaller.exe', 'tiworker.exe', 'musnotification.exe',
    'wuauclt.exe', 'usoclient.exe',

    # 系統工具
    'taskmgr.exe', 'perfmon.exe', 'mmc.exe', 'regedit.exe',
    'cmd.exe', 'powershell.exe', 'pwsh.exe',

    # 驅動與硬體
    'nvcontainer.exe', 'nvdisplay.container.exe',
    'nvspcaps64.exe', 'nvsphelper64.exe',
    'aaborkerservice.exe', 'igfxem.exe', 'igfxtray.exe',
    'realtek.exe', 'ravbg64.exe', 'rtkhdasvc.exe',
    'nahimicservice.exe',

    # 防毒軟體
    'msmpeng.exe', 'mpcmdrun.exe', 'nissrv.exe',
    'avgnt.exe', 'avguard.exe', 'avscan.exe',
    'mbam.exe', 'mbamservice.exe',
    'norton.exe', 'nortonsecurity.exe',
    'kavtray.exe', 'avp.exe',

    # 常見系統服務
    'spoolsv.exe', 'wlanext.exe', 'dashost.exe',
    'wmiprvse.exe', 'msiexec.exe', 'smartscreen.exe',

    # ScreenGet 自身
    'screenget.exe', 'python.exe', 'pythonw.exe',
}

# 系統目錄路徑 - 這些路徑下的程式通常是系統程式
SYSTEM_PATHS = [
    os.environ.get('WINDIR', r'C:\Windows'),
    os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'System32'),
    os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'SysWOW64'),
]

# 已知的瀏覽器進程
BROWSER_PROCESSES = {
    'chrome.exe', 'msedge.exe', 'firefox.exe', 'opera.exe',
    'brave.exe', 'vivaldi.exe', 'iexplore.exe', 'safari.exe',
    'arc.exe', 'whale.exe', 'chromium.exe',
}

# 已知的遊戲平台進程
GAME_PLATFORM_PROCESSES = {
    'steam.exe', 'steamwebhelper.exe',
    'epicgameslauncher.exe', 'easyanticheat.exe',
    'origin.exe', 'ea.exe',
    'gog.exe', 'galaxyclient.exe',
    'battlenet.exe', 'battle.net.exe',
    'upc.exe', 'ubisoftconnect.exe',
    'riotclientservices.exe',
}

# 常見遊戲目錄關鍵字
GAME_PATH_KEYWORDS = [
    'steamapps', 'epic games', 'riot games', 'origin games',
    'ubisoft', 'gog galaxy', 'games', 'battle.net',
    'program files\\steam', 'program files (x86)\\steam',
]


class ProcessFilter:
    """程式過濾器 - 決定是否追蹤一個程式"""

    @staticmethod
    def should_track(process_name: str, exe_path: str = "") -> bool:
        """判斷是否應該追蹤此程式"""
        if not process_name:
            return False

        name_lower = process_name.lower()

        # 排除已知系統程式
        if name_lower in SYSTEM_PROCESSES:
            return False

        # 排除系統目錄中的程式
        if exe_path:
            path_lower = exe_path.lower()
            for sys_path in SYSTEM_PATHS:
                if path_lower.startswith(sys_path.lower()):
                    # 但排除在系統目錄下的瀏覽器等用戶程式
                    if name_lower not in BROWSER_PROCESSES:
                        return False

        # 排除無視窗標題的程式（通常是背景服務）
        # 此判斷在 tracker 中實作，因為需要視窗標題

        return True

    @staticmethod
    def get_app_type(process_name: str, exe_path: str = "") -> str:
        """判斷程式類型: 'browser', 'game', 'app'"""
        name_lower = process_name.lower()

        # 瀏覽器
        if name_lower in BROWSER_PROCESSES:
            return 'browser'

        # 遊戲平台
        if name_lower in GAME_PLATFORM_PROCESSES:
            return 'game'

        # 根據路徑判斷遊戲
        if exe_path:
            path_lower = exe_path.lower()
            for keyword in GAME_PATH_KEYWORDS:
                if keyword in path_lower:
                    return 'game'

        return 'app'

    @staticmethod
    def get_display_name(process_name: str, window_title: str = "") -> str:
        """取得程式的顯示名稱"""
        name_lower = process_name.lower()

        # 瀏覽器使用特定的顯示名稱
        browser_names = {
            'chrome.exe': 'Google Chrome',
            'msedge.exe': 'Microsoft Edge',
            'firefox.exe': 'Mozilla Firefox',
            'opera.exe': 'Opera',
            'brave.exe': 'Brave',
            'vivaldi.exe': 'Vivaldi',
            'arc.exe': 'Arc',
        }
        if name_lower in browser_names:
            return browser_names[name_lower]

        # 針對遊戲引擎等常見的「泛用執行檔名稱」，優先使用視窗標題作為顯示名稱
        generic_names = {
            'client-win64-shipping.exe',
            'client-win64-test.exe',
            'ue4game-win64-shipping.exe',
            'ue5game-win64-shipping.exe',
            'unityplayer.exe',
            'game.exe',
        }
        if name_lower in generic_names and window_title and window_title.strip():
            return window_title.strip()

        # 移除 .exe 後綴作為預設顯示名稱
        display_name = process_name
        if display_name.lower().endswith('.exe'):
            display_name = display_name[:-4]

        return display_name or process_name
