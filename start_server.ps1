# start_server.ps1
# Starts the Python HTTP server in a hidden window and waits for it to exit.
# Task Scheduler tracks this process via this wrapper.

$proc = Start-Process `
    -FilePath "python" `
    -ArgumentList "-m http.server 8000 --bind 0.0.0.0" `
    -WorkingDirectory "C:\Users\bb\taskpwa" `
    -WindowStyle Hidden `
    -PassThru

$proc.WaitForExit()
