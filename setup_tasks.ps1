#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Registers TaskPWA_Server and TaskPWA_Ngrok in Windows Task Scheduler.
    Both tasks trigger at user logon.

.DESCRIPTION
    TaskPWA_Server : runs  python -m http.server 8000 --bind 0.0.0.0
                     working directory C:\Users\bb\taskpwa
    TaskPWA_Ngrok  : runs  ngrok http 8000
                     saves the public HTTPS URL to C:\Users\bb\taskpwa\ngrok_url.txt

.NOTES
    Run once from an elevated (Administrator) PowerShell session.
    Helper scripts start_server.ps1 and start_ngrok.ps1 must exist in the same folder.
#>

$ErrorActionPreference = "Stop"

$workDir     = "C:\Users\bb\taskpwa"
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

Write-Host "Registering tasks for user: $currentUser"
Write-Host "Working directory          : $workDir"
Write-Host ""

# ---------------------------------------------------------------
# Shared settings factory
# ---------------------------------------------------------------
function New-PWASettings {
    New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit ([System.TimeSpan]::Zero) `
        -RestartCount 10 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable
}

function New-PWAPrincipal {
    New-ScheduledTaskPrincipal `
        -UserId $currentUser `
        -LogonType Interactive `
        -RunLevel Highest
}

# ---------------------------------------------------------------
# Task 1: TaskPWA_Server
# ---------------------------------------------------------------
$taskName1      = "TaskPWA_Server"
$serverHelper   = "$workDir\start_server.ps1"

if (-not (Test-Path $serverHelper)) {
    Write-Error "Helper script not found: $serverHelper"
    exit 1
}

if (Get-ScheduledTask -TaskName $taskName1 -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName1 -Confirm:$false
    Write-Host "Removed existing task : $taskName1"
}

$action1 = New-ScheduledTaskAction `
    -Execute    "powershell.exe" `
    -Argument   "-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$serverHelper`"" `
    -WorkingDirectory $workDir

$trigger1 = New-ScheduledTaskTrigger -AtLogOn -User $currentUser

Register-ScheduledTask `
    -TaskName   $taskName1 `
    -Action     $action1 `
    -Trigger    $trigger1 `
    -Settings   (New-PWASettings) `
    -Principal  (New-PWAPrincipal) `
    -Description "Start Python HTTP server for TaskPWA on port 8000 (bind 0.0.0.0)" `
    | Out-Null

Write-Host "Registered task       : $taskName1"

# ---------------------------------------------------------------
# Task 2: TaskPWA_Ngrok
# ---------------------------------------------------------------
$taskName2    = "TaskPWA_Ngrok"
$ngrokHelper  = "$workDir\start_ngrok.ps1"

if (-not (Test-Path $ngrokHelper)) {
    Write-Error "Helper script not found: $ngrokHelper"
    exit 1
}

if (Get-ScheduledTask -TaskName $taskName2 -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName2 -Confirm:$false
    Write-Host "Removed existing task : $taskName2"
}

$action2 = New-ScheduledTaskAction `
    -Execute    "powershell.exe" `
    -Argument   "-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ngrokHelper`"" `
    -WorkingDirectory $workDir

$trigger2 = New-ScheduledTaskTrigger -AtLogOn -User $currentUser

Register-ScheduledTask `
    -TaskName   $taskName2 `
    -Action     $action2 `
    -Trigger    $trigger2 `
    -Settings   (New-PWASettings) `
    -Principal  (New-PWAPrincipal) `
    -Description "Start ngrok tunnel for TaskPWA and save public URL to ngrok_url.txt" `
    | Out-Null

Write-Host "Registered task       : $taskName2"

# ---------------------------------------------------------------
# Summary
# ---------------------------------------------------------------
Write-Host ""
Write-Host "All done. Both tasks will run at next logon."
Write-Host ""
Write-Host "  TaskPWA_Server  ->  python -m http.server 8000 --bind 0.0.0.0"
Write-Host "  TaskPWA_Ngrok   ->  ngrok http 8000"
Write-Host "                      URL saved to: $workDir\ngrok_url.txt"
Write-Host ""
Write-Host "To start immediately without rebooting, run:"
Write-Host "  Start-ScheduledTask -TaskName TaskPWA_Server"
Write-Host "  Start-ScheduledTask -TaskName TaskPWA_Ngrok"
