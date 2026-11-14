<#
.SYNOPSIS
  From this laptop: store an AssemblyAI API key in the office desktop's .env.

.DESCRIPTION
  Asks for the key here with hidden input, then sends it over SSH's input stream (never on a
  command line, so it is not in either machine's history or process list) to
  scripts\set_assemblyai_key.ps1 on the office machine. That script checks the key with
  AssemblyAI, backs up .env and writes ASSEMBLYAI_API_KEY. -Activate also switches
  ASR_ACTIVE_MODEL to assemblyai.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\dev\bharatlang\scripts\set_assemblyai_key_remote.ps1 -Activate
.EXAMPLE
  ... -SshHost office-via-dell -Activate    # when away from the office LAN
#>
param(
    [string]$SshHost = "office",
    [string]$RemoteScript = "C:\dev\Bharatlang\scripts\set_assemblyai_key.ps1",
    [switch]$Activate
)
$ErrorActionPreference = "Stop"

$secure = Read-Host -AsSecureString "Paste your AssemblyAI API key (input is hidden)"
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try { $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
if (-not $key.Trim()) { Write-Host "No key entered. Nothing was changed." -ForegroundColor Red; exit 1 }

$flags = if ($Activate) { " -Activate" } else { "" }
$remote = "powershell -NoProfile -ExecutionPolicy Bypass -File $RemoteScript$flags"
Write-Host "Sending to $SshHost ..."
$key | ssh $SshHost $remote
$code = $LASTEXITCODE
$key = $null
exit $code
