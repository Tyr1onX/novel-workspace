param(
    [string]$RuntimeDir = "$HOME\.novel-workspace\fanqie-publisher",
    [switch]$SkipLogin
)

$ErrorActionPreference = "Stop"
$Repo = "https://github.com/rockbenben/fanqie-publisher.git"
$PinnedCommit = "91d8efe487c441b516e0ffa1986f7c5b73a1c0a9"

Write-Host "Fanqie runtime directory: $RuntimeDir"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found in PATH. Install Python 3.10+ first."
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git was not found in PATH. Install Git first."
}

$parent = Split-Path -Parent $RuntimeDir
New-Item -ItemType Directory -Force -Path $parent | Out-Null

if (-not (Test-Path "$RuntimeDir\.git")) {
    git clone $Repo $RuntimeDir
}

Push-Location $RuntimeDir
try {
    git fetch origin --tags --prune
    git checkout --detach $PinnedCommit

    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    python -m playwright install chromium

    Write-Host "Pinned fanqie-publisher runtime installed at commit $PinnedCommit"

    if (-not $SkipLogin) {
        Write-Host "A browser will open for the one-time Fanqie login."
        python fanqie_upload.py login
    }
}
finally {
    Pop-Location
}

Write-Host "Runtime setup complete."
Write-Host "Next, register this PC as a GitHub self-hosted runner with label: fanqie"
