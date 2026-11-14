$ErrorActionPreference = 'Continue'
# Overnight ASR queue: wait for any running bench, then (re)run every model/dataset pair lacking a finished summary.
Set-Location C:\dev\Bharatlang
function Wait-Idle { while (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*asr_bench.run bench*' }) { Start-Sleep 30 } }
$plan = @(
  @{ model = 'medium'; tag = 'medium' },
  @{ model = 'models\ct2\indicwhisper-medium-mr'; tag = 'indicwhisper-medium-mr' }
)
foreach ($p in $plan) { foreach ($d in 'respin','fleurs') {
  Wait-Idle
  $done = Get-ChildItem eval_data\runs -Directory -Filter "*_$($d)_$($p.tag)_cuda" | Where-Object { Test-Path (Join-Path $_.FullName 'summary.json') }
  if ($done) { Add-Content logs\asr_queue.log "skip $($p.tag) $d (done)"; continue }
  Add-Content logs\asr_queue.log "$(Get-Date -Format s) start $($p.tag) $d"
  & .venv\Scripts\python.exe -m backend.app.evaluation.asr_bench.run bench --dataset $d --model $p.model *>> logs\asr_queue.log
  Add-Content logs\asr_queue.log "$(Get-Date -Format s) end $($p.tag) $d exit=$LASTEXITCODE"
} }
Add-Content logs\asr_queue.log "$(Get-Date -Format s) queue finished"