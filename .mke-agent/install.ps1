param(
    [string]$RepoPath = "D:\Math Knowledge Engine",
    [string]$ControlPath = "D:\mke_agent_control"
)

$ErrorActionPreference = "Stop"
$ControlBranch = "automation/mke-agent-loop"

function Write-Step([string]$Message) {
    Write-Host "[MKE] $Message" -ForegroundColor Cyan
}

Write-Step "Checking Git repository"
if (-not (Test-Path $RepoPath)) {
    throw "Repository path not found: $RepoPath"
}
git -C $RepoPath rev-parse --git-dir | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Not a Git repository: $RepoPath"
}

Write-Step "Checking Python"
$PythonPrefix = @()
$RepoVenvPython = Join-Path $RepoPath ".venv\\Scripts\\python.exe"
if (Test-Path $RepoVenvPython) {
    $PythonExe = $RepoVenvPython
} else {
    $PythonCmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $PythonCmd) {
        $PythonCmd = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($PythonCmd) {
            $PythonPrefix = @("-3")
        }
    }
    if (-not $PythonCmd) {
        throw "Python 3 was not found in PATH."
    }
    $PythonExe = $PythonCmd.Source
}

Write-Step "Checking Antigravity CLI"
$AgyCmd = Get-Command agy.exe -ErrorAction SilentlyContinue
if (-not $AgyCmd) {
    $AgyCmd = Get-Command agy -ErrorAction SilentlyContinue
}
if (-not $AgyCmd) {
    Write-Step "Installing Antigravity CLI from the official Google installer"
    irm https://antigravity.google/cli/install.ps1 | iex
    $AgyDir = Join-Path $env:LOCALAPPDATA "agy\bin"
    if ($env:PATH -notlike "*$AgyDir*") {
        $env:PATH = "$AgyDir;$env:PATH"
    }
    $AgyCmd = Get-Command agy.exe -ErrorAction SilentlyContinue
    if (-not $AgyCmd) {
        $AgyCmd = Get-Command agy -ErrorAction SilentlyContinue
    }
}
if (-not $AgyCmd) {
    throw "Antigravity CLI installation could not be verified."
}

Write-Step "Testing Antigravity headless authentication"
$ProbeOutput = & $AgyCmd.Source -p "Reply exactly MKE_AGY_OK" --output-format text 2>&1
$ProbeExit = $LASTEXITCODE
$ProbeText = $ProbeOutput -join [Environment]::NewLine
if ($ProbeExit -ne 0 -or $ProbeText -match "authentication required") {
    Write-Host ""
    Write-Host "Antigravity needs one interactive sign-in. Complete login/setup, then exit the Antigravity TUI." -ForegroundColor Yellow
    & $AgyCmd.Source
    Write-Step "Re-testing Antigravity authentication"
    $ProbeOutput = & $AgyCmd.Source -p "Reply exactly MKE_AGY_OK" --output-format text 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Antigravity headless authentication is still unavailable."
    }
}

Write-Step "Fetching control branch"
git -C $RepoPath fetch origin $ControlBranch
if ($LASTEXITCODE -ne 0) {
    throw "Could not fetch $ControlBranch"
}

if (Test-Path $ControlPath) {
    Write-Step "Control path already exists; updating it"
    git -C $ControlPath fetch origin $ControlBranch
    git -C $ControlPath reset --hard "origin/$ControlBranch"
} else {
    Write-Step "Creating isolated control worktree"
    git -C $RepoPath worktree add -B automation/mke-agent-loop-local $ControlPath "origin/$ControlBranch"
}
if ($LASTEXITCODE -ne 0) {
    throw "Could not prepare control worktree."
}

$Runner = Join-Path $ControlPath ".mke-agent\runner.py"
if (-not (Test-Path $Runner)) {
    throw "Runner file not found: $Runner"
}

Write-Step "Registering per-user scheduled task"
$Quote = [char]34
$ArgumentParts = @()
$ArgumentParts += $PythonPrefix
$ArgumentParts += @(
    ($Quote + $Runner + $Quote),
    "--daemon",
    "--repo",
    ($Quote + $RepoPath + $Quote),
    "--control",
    ($Quote + $ControlPath + $Quote)
)
$Arguments = $ArgumentParts -join " "

try {
    $Action = New-ScheduledTaskAction -Execute $PythonExe -Argument $Arguments -WorkingDirectory $ControlPath
    $Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    $Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
    Register-ScheduledTask -TaskName "MKE Antigravity Agent Runner" -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null
    Start-ScheduledTask -TaskName "MKE Antigravity Agent Runner"
    Write-Step "Scheduled task started"
}
catch {
    Write-Host "Scheduled Task registration failed; installing Startup fallback." -ForegroundColor Yellow
    $Startup = [Environment]::GetFolderPath("Startup")
    $StartupCmd = Join-Path $Startup "MKE-Agent-Runner.cmd"
    $CmdLine = "@echo off" + [Environment]::NewLine +
        "start " + $Quote + $Quote + " /min " + $Quote + $PythonExe + $Quote + " " + $Arguments
    Set-Content -Path $StartupCmd -Value $CmdLine -Encoding ASCII
    Start-Process -FilePath $PythonExe -ArgumentList $Arguments -WorkingDirectory $ControlPath -WindowStyle Hidden
    Write-Step "Startup fallback installed and runner started"
}

Write-Host ""
Write-Host "MKE automation bootstrap completed." -ForegroundColor Green
Write-Host "Control branch: $ControlBranch"
Write-Host "Control worktree: $ControlPath"
Write-Host "Runner log: $ControlPath\.mke-agent\logs\runner.log"
Write-Host "The queued THPT-COV-P1 task will be picked up automatically."
