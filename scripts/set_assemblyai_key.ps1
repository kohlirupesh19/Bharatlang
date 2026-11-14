<#
.SYNOPSIS
  Stores an AssemblyAI API key in the project's .env as ASSEMBLYAI_API_KEY.

.DESCRIPTION
  Prompts for the key with hidden input (it is never echoed, logged or put in shell history),
  checks it against AssemblyAI, backs up .env, then adds or replaces the ASSEMBLYAI_API_KEY line.
  With -Activate it also sets ASR_ACTIVE_MODEL=assemblyai (the previous value is printed so you
  can switch back). Restart the backend afterwards so the new settings load.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\dev\Bharatlang\scripts\set_assemblyai_key.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\dev\Bharatlang\scripts\set_assemblyai_key.ps1 -Activate
#>
param(
    [string]$EnvPath = (Join-Path (Split-Path -Parent $PSScriptRoot) ".env"),
    [string]$BaseUrl = "https://api.assemblyai.com",
    [switch]$Activate,
    [switch]$SkipCheck
)
$ErrorActionPreference = "Stop"

function Read-Key {
    # Piped input (used by tests) or a hidden prompt.
    if ([Console]::IsInputRedirected) { return [Console]::In.ReadLine() }
    $secure = Read-Host -AsSecureString "Paste your AssemblyAI API key (input is hidden)"
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Test-Key([string]$Key) {
    # Listing one transcript needs a valid key and costs nothing.
    try {
        Invoke-RestMethod -Uri "$BaseUrl/v2/transcript?limit=1" -Headers @{ authorization = $Key } -Method Get | Out-Null
        return $true
    } catch {
        $code = $null
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        if ($code -eq 401) { Write-Host "AssemblyAI rejected this key (401). Nothing was changed." -ForegroundColor Red; return $false }
        Write-Host "Could not check the key ($($_.Exception.Message)). Re-run with -SkipCheck to save it anyway." -ForegroundColor Yellow
        return $false
    }
}

function Set-EnvValue([string[]]$Lines, [string]$Name, [string]$Value) {
    $pattern = "^\s*#?\s*$([regex]::Escape($Name))\s*="
    $found = $false
    $out = foreach ($line in $Lines) {
        if (-not $found -and $line -match $pattern) { $found = $true; "$Name=$Value" } else { $line }
    }
    if (-not $found) { $out = @($out) + "$Name=$Value" }
    return ,@($out)
}

if (-not (Test-Path $EnvPath)) { Write-Host "No .env found at $EnvPath" -ForegroundColor Red; exit 1 }

$key = (Read-Key).Trim()
if (-not $key) { Write-Host "No key entered. Nothing was changed." -ForegroundColor Red; exit 1 }
if ($key -match "\s") { Write-Host "The key contains spaces; paste only the key. Nothing was changed." -ForegroundColor Red; exit 1 }
if (-not $SkipCheck -and -not (Test-Key $key)) { exit 1 }

$utf8 = New-Object System.Text.UTF8Encoding $false   # no BOM: the backend reads .env as plain UTF-8
$lines = [IO.File]::ReadAllLines($EnvPath, $utf8)
$backup = "$EnvPath.bak-" + (Get-Date -Format "yyyyMMdd-HHmmss")
Copy-Item $EnvPath $backup

$lines = Set-EnvValue $lines "ASSEMBLYAI_API_KEY" $key
if ($Activate) {
    $previous = ($lines | Where-Object { $_ -match "^\s*ASR_ACTIVE_MODEL\s*=" } | Select-Object -First 1)
    $lines = Set-EnvValue $lines "ASR_ACTIVE_MODEL" "assemblyai"
}
[IO.File]::WriteAllLines($EnvPath, $lines, $utf8)
$tail = $key.Substring([Math]::Max(0, $key.Length - 4))
$key = $null

Write-Host "ASSEMBLYAI_API_KEY saved (ends in ...$tail) in $EnvPath" -ForegroundColor Green
Write-Host "Backup of the old file: $backup"
if ($Activate) {
    Write-Host "ASR_ACTIVE_MODEL=assemblyai (was: $previous). To switch back, set that line again." -ForegroundColor Green
} else {
    Write-Host "Speech recognition is unchanged. To use AssemblyAI, set ASR_ACTIVE_MODEL=assemblyai (or re-run with -Activate)."
}
Write-Host "Restart the backend so the change loads."
