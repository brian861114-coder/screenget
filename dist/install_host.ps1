# setup_screenget.ps1
# 這個腳本會自動將 ScreenGetHost.exe 註冊到 Chrome 的 Native Messaging 列表中

$currentDir = Get-Location
$jsonPath = "$currentDir\com.screenget.host.json"
$exePath = "$currentDir\ScreenGetHost.exe"

# 1. 更新 JSON 檔案中的路徑
$jsonContent = Get-Content $jsonPath | ConvertFrom-Json
$jsonContent.path = $exePath.Replace("\", "\\")
$jsonContent | ConvertTo-Json -Depth 10 | Set-Content $jsonPath

Write-Host "已更新 JSON 檔案路徑: $exePath" -ForegroundColor Cyan

# 2. 寫入 Windows 登錄檔 (Chrome)
$registryPath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.screenget.host"
if (-not (Test-Path "HKCU:\Software\Google\Chrome\NativeMessagingHosts")) {
    New-Item -Path "HKCU:\Software\Google\Chrome\NativeMessagingHosts" -Force
}
New-Item -Path $registryPath -Value $jsonPath -Force

# 3. 寫入 Windows 登錄檔 (Edge)
$edgeRegistryPath = "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\com.screenget.host"
if (-not (Test-Path "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts")) {
    New-Item -Path "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts" -Force
}
New-Item -Path $edgeRegistryPath -Value $jsonPath -Force

Write-Host "成功將 ScreenGetHost 註冊到 Chrome 與 Edge！" -ForegroundColor Green
Write-Host "請記得在 com.screenget.host.json 中填入正確的 Extension ID。" -ForegroundColor Yellow
pause
