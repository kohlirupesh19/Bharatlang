# Open the reverse SSH tunnel that lets the AWS front door (Caddy on the t4g.micro) reach
# this desktop's backend: AWS 127.0.0.1:18000 -> office 127.0.0.1:8000.
# The reconnect loop runs detached via WMI (like start_services.ps1) so it survives the
# SSH session, and redials 30 s after any drop. On demand only: no boot persistence.
#
#   powershell -File scripts\start_tunnel.ps1            # start (no-op if already running)
#   powershell -File scripts\start_tunnel.ps1 -Status    # show loop / ssh processes
#   powershell -File scripts\start_tunnel.ps1 -Stop      # stop loop and ssh
#
# The key can only open this one forward (restrict,permitlisten on the AWS side).
param(
  [ValidatePattern('^[A-Za-z0-9.-]+$')]
  [string]$Target = 'bharatlang.ideasfreshly.store',
  [switch]$Stop,
  [switch]$Status,
  [switch]$Loop
)
$ErrorActionPreference = 'Stop'

$root = 'C:\dev\Bharatlang'
$logs = Join-Path $root 'logs'
$log = Join-Path $logs 'tunnel.log'
$sshErr = Join-Path $logs 'tunnel-ssh.err'
$sshDir = Join-Path $env:USERPROFILE '.ssh'
$key = Join-Path $sshDir 'bharatlang_tunnel'
$knownHosts = Join-Path $sshDir 'bharatlang_tunnel_known_hosts'
$sshExe = 'C:\Windows\System32\OpenSSH\ssh.exe'
$hostAlias = 'bharatlang-front'
$remoteForward = '127.0.0.1:18000:127.0.0.1:8000'
$backendPort = 8000
$retrySeconds = 30

function Write-Log([string]$message) {
  Add-Content -Path $log -Value "$(Get-Date -Format s) $message" -Encoding utf8
}

function Get-TunnelProcesses {
  Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='ssh.exe'" |
    Where-Object {
      $_.ProcessId -ne $PID -and $_.CommandLine -and
      (($_.CommandLine -like '*start_tunnel.ps1*-Loop*') -or ($_.CommandLine -like '*bharatlang_tunnel*'))
    }
}

function Invoke-TunnelLoop {
  $sshArgs = @(
    '-N', '-T',
    '-i', "`"$key`"",
    '-o', 'IdentitiesOnly=yes',
    '-o', 'BatchMode=yes',
    # ssh splits this option on spaces ("Admin pc"), so pass the ~ form it expands itself.
    '-o', 'UserKnownHostsFile=~/.ssh/bharatlang_tunnel_known_hosts',
    '-o', "HostKeyAlias=$hostAlias",
    '-o', 'StrictHostKeyChecking=yes',
    '-o', 'ServerAliveInterval=30',
    '-o', 'ServerAliveCountMax=3',
    '-o', 'ExitOnForwardFailure=yes',
    '-R', $remoteForward,
    "tunnel@$Target"
  )
  while ($true) {
    Write-Log "connecting tunnel@$Target ($remoteForward)"
    $p = Start-Process -FilePath $sshExe -ArgumentList $sshArgs -NoNewWindow -Wait -PassThru `
      -RedirectStandardError $sshErr
    $detail = (Get-Content -Path $sshErr -Raw -ErrorAction SilentlyContinue)
    if ($detail) { $detail = $detail.Trim() } else { $detail = '' }
    Write-Log "ssh exited with code $($p.ExitCode) $detail; retrying in $retrySeconds s"
    Start-Sleep -Seconds $retrySeconds
  }
}

if ($Loop) { Invoke-TunnelLoop; return }

$running = @(Get-TunnelProcesses)

if ($Status) {
  if ($running.Count -eq 0) { Write-Output 'tunnel not running' }
  $running | ForEach-Object { Write-Output "$($_.Name) pid $($_.ProcessId)" }
  return
}

if ($Stop) {
  if ($running.Count -eq 0) { Write-Output 'tunnel not running'; return }
  $running | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Output "stopped $($_.Name) pid $($_.ProcessId)" }
  Write-Log 'stopped by start_tunnel.ps1 -Stop'
  return
}

if ($running.Count -gt 0) { Write-Output "tunnel already running (pids $($running.ProcessId -join ', '))"; return }
foreach ($required in @($key, $knownHosts, $sshExe)) {
  if (-not (Test-Path $required)) { throw "missing $required; see the thin-front plan, step 4" }
}
if (-not (Get-NetTCPConnection -State Listen -LocalPort $backendPort -ErrorAction SilentlyContinue)) {
  Write-Output "warning: backend is not listening on :$backendPort yet; the site shows 'unavailable' until it is (run start_services.ps1)"
}

$commandLine = "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`" -Loop -Target $Target"
$r = Invoke-CimMethod Win32_Process -MethodName Create -Arguments @{ CommandLine = $commandLine; CurrentDirectory = $root }
if ($r.ReturnValue -ne 0) { throw "tunnel loop failed to start (Win32_Process.Create returned $($r.ReturnValue))" }

Start-Sleep -Seconds 8
$ssh = @(Get-TunnelProcesses | Where-Object { $_.Name -eq 'ssh.exe' })
if ($ssh.Count -gt 0) {
  Write-Output "tunnel up: loop pid $($r.ProcessId), ssh pid $($ssh[0].ProcessId) -> tunnel@$Target"
} else {
  Write-Output "tunnel loop started (pid $($r.ProcessId)) but ssh is not connected yet; see $log"
}
