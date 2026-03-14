$currentDir = $PSScriptRoot
if (-not $currentDir) { $currentDir = Get-Location }

$p_py = "$currentDir\native_messaging\native_host.py"
$p_bat = "$currentDir\native_messaging\run_host.bat"
$p_json = "$currentDir\native_messaging\com.screenget.host.json"
$ext_id = 'chrome-extension://eociggeoliljeoidbbhkeoelaainhkcp/'

# Chrome registry path
$regPath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.screenget.host"

# 1. Update JSON file
$json_content = @{
    name            = "com.screenget.host"
    description     = "ScreenGet Native Messaging Host"
    path            = $p_bat
    type            = "stdio"
    allowed_origins = @($ext_id)
}
$json_str = $json_content | ConvertTo-Json
Set-Content -Path $p_json -Value $json_str -Force

# 2. Update Batch file
$bat_content = "@echo off`r`npy -u `"$p_py`" %*"
Set-Content -Path $p_bat -Value $bat_content -Force

# 3. Registry
if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }
Set-Item -Value $p_json -Path $regPath

Write-Host "Success! Paths updated relative to: $currentDir"
