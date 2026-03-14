import os
import json
import sys

# Get absolute paths
current_dir = os.path.dirname(os.path.abspath(__file__))
p_py = os.path.join(current_dir, 'native_messaging', 'native_host.py')
p_bat = os.path.join(current_dir, 'native_messaging', 'run_host.bat')
p_json = os.path.join(current_dir, 'native_messaging', 'com.screenget.host.json')
ext_id = 'chrome-extension://eociggeoliljeoidbbhkeoelaainhkcp/'

# 1. Write Batch File
# Use 'cp950' for Traditional Chinese Windows CMD or just 'utf-8' and hope for the best
# Actually, if we use double quotes around the path, 'utf-8' might work if the system supports it.
# Safer: Use absolute path without spaces/special chars if possible, but we can't.
with open(p_bat, 'w', encoding='utf-8') as f:
    # Use 'py' to run the script
    f.write(f'@echo off\npy -u "{p_py}" %*\n')

# 2. Write JSON File
json_data = {
    "name": "com.screenget.host",
    "description": "ScreenGet Native Messaging Host",
    "path": p_bat,
    "type": "stdio",
    "allowed_origins": [ext_id]
}
with open(p_json, 'w', encoding='utf-8') as f:
    json.dump(json_data, f, indent=4, ensure_ascii=False)

print(f"Successfully generated files in:\n{current_dir}")
