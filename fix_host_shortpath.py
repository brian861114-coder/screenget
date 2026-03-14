import os
import json
import ctypes
from ctypes import wintypes

def get_short_path_name(long_name):
    """取得 Windows 短路徑 (8.3)"""
    buf_size = 256
    gui_buf = ctypes.create_unicode_buffer(buf_size)
    ctypes.windll.kernel32.GetShortPathNameW(long_name, gui_buf, buf_size)
    return gui_buf.value

# Get absolute paths
current_dir = os.path.dirname(os.path.abspath(__file__))
p_py = os.path.join(current_dir, 'native_messaging', 'native_host.py')
p_bat = os.path.join(current_dir, 'native_messaging', 'run_host.bat')
p_json = os.path.join(current_dir, 'native_messaging', 'com.screenget.host.json')
ext_id = 'chrome-extension://eociggeoliljeoidbbhkeoelaainhkcp/'

# Convert to short paths to avoid encoding issues in CMD
short_p_py = get_short_path_name(p_py)
short_p_bat = get_short_path_name(p_bat)
short_p_json = get_short_path_name(p_json)

print(f"Long path: {p_py}")
print(f"Short path: {short_p_py}")

# 1. Write Batch File (Use short path)
with open(p_bat, 'w', encoding='ascii') as f:
    f.write(f'@echo off\npy -u "{short_p_py}" %*\n')

# 2. Write JSON File (Use short path for 'path' field)
json_data = {
    "name": "com.screenget.host",
    "description": "ScreenGet Native Messaging Host",
    "path": short_p_bat,
    "type": "stdio",
    "allowed_origins": [ext_id]
}
with open(p_json, 'w', encoding='utf-8') as f:
    json.dump(json_data, f, indent=4)

# 3. Registry update with short path for JSON manifest
import winreg
key_path = r"Software\Google\Chrome\NativeMessagingHosts\com.screenget.host"
try:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, short_p_json)
    
    # Also for Edge
    edge_key_path = r"Software\Microsoft\Edge\NativeMessagingHosts\com.screenget.host"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, edge_key_path) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, short_p_json)
        
    print("Successfully updated registry and files using short paths.")
except Exception as e:
    print(f"Registry update failed: {e}")
