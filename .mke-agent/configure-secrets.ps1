param([string]$SecretPath = "$env:LOCALAPPDATA\MKE\secrets\openai_api_key.dpapi")

$ErrorActionPreference = "Stop"
$Parent = Split-Path -Parent $SecretPath
New-Item -ItemType Directory -Force -Path $Parent | Out-Null
$Secret = Read-Host "OpenAI API key (stored encrypted for this Windows user)" -AsSecureString
$Secret | ConvertFrom-SecureString | Set-Content -LiteralPath $SecretPath -Encoding ASCII
$Acl = Get-Acl -LiteralPath $SecretPath
$Acl.SetAccessRuleProtection($true, $false)
$Rule = New-Object System.Security.AccessControl.FileSystemAccessRule($env:USERNAME, "FullControl", "Allow")
$Acl.SetAccessRule($Rule)
Set-Acl -LiteralPath $SecretPath -AclObject $Acl
Write-Host "Encrypted MKE OpenAI credential saved for the current Windows user."
