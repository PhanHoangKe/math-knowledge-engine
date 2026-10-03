param(
    [int]$Port = 8765,
    [string]$HostAddress = "127.0.0.1",
    [string]$RepoPath = "D:\Math Knowledge Engine",
    [string]$WorktreesPath = "D:\mke_agent_worktrees",
    [switch]$Stdio = $false
)

$ErrorActionPreference = "Stop"

$BridgeServer = Join-Path $PSScriptRoot "bridge\server.py"
$PythonExe = (Get-Command python.exe).Source

if ($Stdio) {
    & $PythonExe $BridgeServer --stdio --repo $RepoPath --worktrees $WorktreesPath
} else {
    Write-Host "[MKE BRIDGE] Starting dual REST & MCP Bridge on http://${HostAddress}:$Port ..." -ForegroundColor Cyan
    & $PythonExe $BridgeServer --port $Port --host $HostAddress --repo $RepoPath --worktrees $WorktreesPath
}
