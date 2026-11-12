# OCR every manifest document that needs it, using Surya via Ollama's bundled llama-server (CUDA).
# Resumable: a document whose results.json exists is skipped. Run on the office desktop:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ocr_corpus.ps1
$ErrorActionPreference = "Stop"
$root = "C:\dev\Bharatlang"
$docs = "$root\backend\data\documents"
$log = "$root\logs\ocr.log"
# Official llama.cpp CUDA build (Ollama's bundled llama-server silently falls back to CPU here).
$llamaDir = "$root\tools\llama.cpp"

New-Item -ItemType Directory -Force "$root\logs", "$docs\ocr" | Out-Null
if (-not (Test-Path "$llamaDir\llama-server.exe")) { throw "llama-server.exe not found in $llamaDir" }
$env:PATH = "$llamaDir;$env:PATH"
$env:SURYA_INFERENCE_BACKEND = "llamacpp"
$env:LLAMA_CPP_BINARY = "$llamaDir\llama-server.exe"

function Write-Log([string]$msg) {
    $line = "{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $msg
    Add-Content -Path $log -Value $line -Encoding utf8
}

function Stop-SuryaServers {
    # Surya cannot stop its llama-server on Windows; kill only servers running the Surya model,
    # never Ollama's own runner (same binary, different model).
    # Non-fatal: the server may already be exiting by the time we look.
    Get-CimInstance Win32_Process -Filter "Name = 'llama-server.exe'" |
        Where-Object { $_.CommandLine -like "*surya-ocr*" } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Log "killed surya llama-server pid=$($_.ProcessId)"
        }
}

function Invoke-IsolatedSurya([string[]]$suryaArgs) {
    # Surya's cleanup calls os.kill(pid, 0) to probe its server; on Windows signal 0 is
    # CTRL_C_EVENT, which hits every process on the console, killing this driver too.
    # So run it in its own hidden console (CreateNoWindow) via cmd, and return its exit code.
    $quoted = ($suryaArgs | ForEach-Object { '"' + $_ + '"' }) -join " "
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "cmd.exe"
    $psi.Arguments = '/c ""' + "$root\.venv-ocr\Scripts\surya_ocr.exe" + '" ' + $quoted + ' >> "' + "$root\logs\ocr_surya.log" + '" 2>&1"'
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $proc = [System.Diagnostics.Process]::Start($psi)
    $proc.WaitForExit()
    return $proc.ExitCode
}

trap { Write-Log "DRIVER ERROR: $_ at line $($_.InvocationInfo.ScriptLineNumber)"; break }

$manifest = Get-Content "$docs\manifest.json" -Raw -Encoding utf8 | ConvertFrom-Json
foreach ($d in $manifest.documents) {
    if ($d.ocr_pages -eq "text-layer") { Write-Log "skip $($d.doc_id): clean text layer"; continue }
    $outDir = "$docs\ocr\$($d.doc_id)"
    if (Get-ChildItem $outDir -Recurse -Filter results.json -ErrorAction SilentlyContinue) {
        Write-Log "skip $($d.doc_id): already OCR'd"; continue
    }
    $pdf = Join-Path $docs $d.path
    $suryaArgs = @($pdf, "--output_dir", $outDir)
    if ($d.ocr_pages) { $suryaArgs += @("--page_range", $d.ocr_pages) }
    Write-Log "start $($d.doc_id) pages=$($d.ocr_pages)"
    $t0 = Get-Date
    try {
        $exit = Invoke-IsolatedSurya $suryaArgs
        if ($exit -ne 0) { throw "surya_ocr exit code $exit" }
        Write-Log ("done  {0} in {1:N1} min" -f $d.doc_id, ((Get-Date) - $t0).TotalMinutes)
    } catch {
        Write-Log "FAILED $($d.doc_id): $_"
    } finally {
        Stop-SuryaServers
    }
}
Write-Log "all documents processed"
