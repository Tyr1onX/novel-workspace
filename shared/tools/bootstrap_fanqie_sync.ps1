param(
    [string]$RuntimeDir = "$HOME\.novel-workspace\fanqie-publisher",
    [string]$RunnerDir = "$HOME\.novel-workspace\github-runner",
    [string]$RunnerName = "$env:COMPUTERNAME-fanqie"
)

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/Tyr1onX/novel-workspace"
$RunnerTaskName = "NovelWorkspaceFanqieRunner"
$SetupRuntime = Join-Path $PSScriptRoot "setup_fanqie_runtime.ps1"

function ConvertFrom-SecureToken([Security.SecureString]$Secure) {
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Install-GitHubRunner([string]$Destination) {
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    if (Test-Path (Join-Path $Destination "config.cmd")) {
        return
    }

    Write-Host "Downloading the latest GitHub Actions runner..."
    $release = Invoke-RestMethod -Headers @{ "User-Agent" = "novel-workspace-bootstrap" } `
        -Uri "https://api.github.com/repos/actions/runner/releases/latest"
    $asset = $release.assets | Where-Object { $_.name -match '^actions-runner-win-x64-.*\.zip$' } | Select-Object -First 1
    if (-not $asset) {
        throw "Could not locate the Windows x64 GitHub Actions runner asset."
    }

    $zip = Join-Path $env:TEMP $asset.name
    Invoke-WebRequest -Headers @{ "User-Agent" = "novel-workspace-bootstrap" } `
        -Uri $asset.browser_download_url -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $Destination -Force
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
}

function Configure-GitHubRunner([string]$Destination) {
    $marker = Join-Path $Destination ".runner"
    if (Test-Path $marker) {
        Write-Host "GitHub runner is already configured."
        return
    }

    Write-Host ""
    Write-Host "Open GitHub -> repository Settings -> Actions -> Runners -> New self-hosted runner."
    Write-Host "Copy only the short-lived registration token. Do not paste that token into chat or commit it anywhere."
    $secure = Read-Host "Runner registration token" -AsSecureString
    $token = ConvertFrom-SecureToken $secure
    try {
        Push-Location $Destination
        & .\config.cmd --unattended `
            --url $RepoUrl `
            --token $token `
            --name $RunnerName `
            --labels "fanqie" `
            --work "_work" `
            --replace
        if ($LASTEXITCODE -ne 0) {
            throw "GitHub runner configuration failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        $token = $null
        Pop-Location
    }
}

function Install-RunnerAutostart([string]$Destination) {
    $launcher = Join-Path $Destination "run-fanqie-runner.ps1"
    @"
`$ErrorActionPreference = "Stop"
Set-Location "$Destination"
& ".\run.cmd"
"@ | Set-Content -Path $launcher -Encoding UTF8

    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcher`""
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType Interactive `
        -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit ([TimeSpan]::Zero)

    try {
        Register-ScheduledTask `
            -TaskName $RunnerTaskName `
            -Action $action `
            -Trigger $trigger `
            -Principal $principal `
            -Settings $settings `
            -Description "GitHub self-hosted runner for novel-workspace Fanqie sync" `
            -Force | Out-Null
        Write-Host "Registered runner autostart task: $RunnerTaskName"
    }
    catch {
        Write-Warning "Task Scheduler registration failed: $($_.Exception.Message)"
        Write-Warning "The runner is configured, but you will need to start $launcher after Windows login until autostart is fixed."
    }

    $existing = Get-CimInstance Win32_Process -Filter "Name = 'Runner.Listener.exe'" -ErrorAction SilentlyContinue
    if (-not $existing) {
        Start-Process powershell.exe `
            -ArgumentList "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", $launcher `
            -WindowStyle Hidden
        Write-Host "Started the GitHub runner for this Windows session."
    }
}

Write-Host "=== Novel Workspace / Fanqie zero-touch bootstrap ==="

if (-not (Test-Path $SetupRuntime)) {
    throw "Missing runtime setup script: $SetupRuntime"
}

Write-Host "Step 1/3: install pinned Fanqie publisher and save one local login session."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $SetupRuntime -RuntimeDir $RuntimeDir
if ($LASTEXITCODE -ne 0) {
    throw "Fanqie runtime setup failed with exit code $LASTEXITCODE."
}

Write-Host "Step 2/3: install and configure the GitHub self-hosted runner."
Install-GitHubRunner $RunnerDir
Configure-GitHubRunner $RunnerDir

Write-Host "Step 3/3: start the runner automatically whenever this Windows account logs in."
Install-RunnerAutostart $RunnerDir

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host "Platform sync is still disabled in the repository, so this setup cannot publish anything yet."
Write-Host "After telling the assistant that login + runner setup succeeded, the repository policy can be activated safely."
