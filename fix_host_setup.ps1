$base = 'C:\Users\USER\Downloads\vibe_coding專案\screenget'
$p_py = "$base\native_messaging\native_host.py"
$p_bat = "$base\native_messaging\run_host.bat"
$p_json = "$base\native_messaging\com.screenget.host.json"
$ext_id = 'chrome-extension://eociggeoliljeoidbbhkeoelaainhkcp/'

# 1. Fix Batch File (ANSI encoding for CMD)
$bat_content = "@echo off`r`npy -u `"$p_py`" %*"
[System.IO.File]::WriteAllText($p_bat, $bat_content, [System.Text.Encoding]::Default)

# 2. Fix JSON File (UTF8 without BOM for Chrome)
$json_obj = @{
    name            = "com.screenget.host"
    description     = "ScreenGet Native Messaging Host"
    path            = $p_bat
    type            = "stdio"
    allowed_origins = @($ext_id)
}
$json_str = $json_obj | ConvertTo-Json
# Use UTF8 without BOM
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($p_json, $json_str, $utf8NoBom)

# 3. Registry
$regPath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.screenget.host"
if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }
Set-Item -Value $p_json -Path $regPath

Write-Host "Paths fixed successfully."
