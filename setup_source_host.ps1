# setup_source_host.ps1
$currentDir = $PSScriptRoot
if (-not $currentDir) { $currentDir = Get-Location }

$nativeMessagingDir = "$currentDir\native_messaging"
$jsonPath = "$nativeMessagingDir\com.screenget.host.json"
$batPath = "$nativeMessagingDir\run_host.bat"

# Update JSON
if (Test-Path $jsonPath) {
    $content = Get-Content $jsonPath -Raw | ConvertFrom-Json
    $content.path = $batPath
    $content | ConvertTo-Json | Set-Content $jsonPath
    Write-Host "JSON updated." -ForegroundColor Cyan
}

# Chrome
$chromePath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.screenget.host"
if (-not (Test-Path $chromePath)) { New-Item -Path $chromePath -Force | Out-Null }
Set-Item -Path $chromePath -Value $jsonPath
Write-Host "Chrome registered." -ForegroundColor Green

# Edge
$edgePath = "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\com.screenget.host"
if (-not (Test-Path $edgePath)) { New-Item -Path $edgePath -Force | Out-Null }
Set-Item -Path $edgePath -Value $jsonPath
Write-Host "Edge registered." -ForegroundColor Green

Write-Host "Done. Restart browser."
