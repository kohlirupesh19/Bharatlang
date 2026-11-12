$ErrorActionPreference = 'Continue'
while (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*asr_bench.run bench*' }) { Start-Sleep 30 }
Set-Location C:\dev\Bharatlang
foreach ($d in 'respin','fleurs') { & .venv\Scripts\python.exe -m backend.app.evaluation.asr_bench.run bench --dataset $d --model models\ct2\indicwhisper-medium-mr *>> logs\asr_queue.log }