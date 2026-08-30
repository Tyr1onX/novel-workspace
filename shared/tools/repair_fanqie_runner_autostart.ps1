param(
    [string]$RunnerDir = "$HOME\.novel-workspace\github-runner"
)

$ErrorActionPreference = "Stop"
$TaskName = "NovelWorkspaceFanqieRunner"

function Write-HiddenRunnerLaunchers([string]$Destination) {
    $psLauncher = Join-Path $Destination "run-fanqie-runner.ps1"
    $vbsLauncher = Join-Path $Destination "run-fanqie-runner.vbs"

    @"
`$ErrorActionPreference = "Stop"
Set-Location "$Destination"
& ".\run.cmd"
exit `$LASTEXITCODE
"@ | Set-Content -Path $psLauncher -Encoding UTF8

    @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$Destination"
command = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""$psLauncher"""
exitCode = shell.Run(command, 0, True)
WScript.Quit exitCode
"@ | Set-Content -Path $vbsLauncher -Encoding Unicode

    return $vbsLauncher
}

if (-not (Test-Path (Join-Path $RunnerDir "run.cmd"))) {
    throw "GitHub runner run.cmd not found: $RunnerDir"
}

# Never interrupt a real workflow job just to repair autostart.
$worker = Get-Process -Name "Runner.Worker" -ErrorAction SilentlyContinue
if ($worker) {
    throw "A GitHub Actions job is currently running. Wait for it to finish, then run this repair again."
}

$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
}

# Stop an idle listener from the old visible-console launcher so only one listener exists.
Get-Process -Name "Runner.Listener" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

$vbsLauncher = Write-HiddenRunnerLaunchers $RunnerDir
$action = New-ScheduledTaskAction `
    -Execute "wscript.exe" `
    -Argument "//B //Nologo `"$vbsLauncher`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Hidden GitHub self-hosted runner for novel-workspace Fanqie sync" `
    -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 2

$listener = Get-Process -Name "Runner.Listener" -ErrorAction SilentlyContinue
$task = Get-ScheduledTask -TaskName $TaskName
if (-not $listener) {
    throw "Hidden runner task was registered, but Runner.Listener did not start."
}

Write-Host "Fanqie runner autostart repaired."
Write-Host "Task state: $($task.State)"
Write-Host "Runner.Listener PID: $($listener.Id -join ', ')"
Write-Host "The runner now starts hidden after Windows logon; no terminal window needs to remain open."
