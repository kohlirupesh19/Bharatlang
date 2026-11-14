# Start Ollama (:11434), backend uvicorn (:8000) and Vite (:5173) on the office desktop.
# Each is launched detached via WMI so it survives the SSH session; a port that is
# already listening is left alone. On-demand only (no boot persistence by design).
$ErrorActionPreference = 'Stop'
$root = 'C:\dev\Bharatlang'
$logs = Join-Path $root 'logs'

function Test-Listening([int]$port) {
  [bool](Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
}

function Start-Detached([string]$name, [int]$port, [string]$commandLine, [string]$cwd) {
  if (Test-Listening $port) { Write-Output "$name already listening on :$port"; return }
  $r = Invoke-CimMethod Win32_Process -MethodName Create -Arguments @{ CommandLine = $commandLine; CurrentDirectory = $cwd }
  if ($r.ReturnValue -ne 0) { throw "$name failed to start (Win32_Process.Create returned $($r.ReturnValue))" }
  foreach ($i in 1..60) {
    if (Test-Listening $port) { Write-Output "$name up on :$port (pid $($r.ProcessId))"; return }
    Start-Sleep -Seconds 2
  }
  throw "$name did not open :$port within 120 s; see its log in $logs"
}

$ollama = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
$ollamaLog = Join-Path $env:USERPROFILE '.ollama\serve.log'
Start-Detached 'ollama' 11434 "cmd /c set OLLAMA_HOST=127.0.0.1:11434&& `"$ollama`" serve >> `"$ollamaLog`" 2>&1" $root

Start-Detached 'backend' 8000 "cmd /c .venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 >> logs\backend.log 2>&1" $root

Start-Detached 'frontend' 5173 "cmd /c pnpm exec vite --host 127.0.0.1 --port 5173 --strictPort >> ..\logs\frontend.log 2>&1" (Join-Path $root 'frontend')
