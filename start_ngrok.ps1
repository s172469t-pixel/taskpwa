# start_ngrok.ps1
# Starts ngrok in a hidden window, polls the local API until the public HTTPS
# URL is available, writes it to ngrok_url.txt, then waits for ngrok to exit.

$urlFile = "C:\Users\bb\taskpwa\ngrok_url.txt"

$ngrokProc = Start-Process `
    -FilePath "ngrok" `
    -ArgumentList "http 8000" `
    -WindowStyle Hidden `
    -PassThru

# Poll ngrok local API (up to ~60 s) for the public tunnel URL
$tunnelUrl = $null
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 3
    try {
        $resp     = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -TimeoutSec 5
        $tunnelUrl = $resp.tunnels |
                     Where-Object { $_.proto -eq "https" } |
                     Select-Object -First 1 -ExpandProperty public_url
        if ($tunnelUrl) { break }
    } catch { }
}

if ($tunnelUrl) {
    $tunnelUrl | Out-File -FilePath $urlFile -Encoding UTF8 -NoNewline
} else {
    "ERROR: could not retrieve ngrok URL" | Out-File -FilePath $urlFile -Encoding UTF8
}

# Keep wrapper alive so Task Scheduler tracks the ngrok process lifetime
$ngrokProc.WaitForExit()
