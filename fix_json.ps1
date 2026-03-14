$p = 'C:\Users\USER\Downloads\vibe_coding專案\screenget\native_messaging\run_host.bat'
$id = 'chrome-extension://eociggeoliljeoidbbhkeoelaainhkcp/'
$json = @{
    name            = "com.screenget.host"
    description     = "ScreenGet Native Messaging Host"
    path            = $p
    type            = "stdio"
    allowed_origins = @($id)
}
$json | ConvertTo-Json | Set-Content -Path '.\native_messaging\com.screenget.host.json' -Encoding utf8
