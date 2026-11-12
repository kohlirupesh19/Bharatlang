@echo off
rem Surya OCR via Ollama's bundled llama-server (CUDA). Usage: run_surya.cmd <pdf> <page_range> <out_dir>
set "OL=C:\Users\Admin pc\AppData\Local\Programs\Ollama\lib\ollama"
set "PATH=%OL%;%OL%\cuda_v13;%PATH%"
set "SURYA_INFERENCE_BACKEND=llamacpp"
set "LLAMA_CPP_BINARY=%OL%\llama-server.exe"
cd /d C:\dev\Bharatlang
.venv-ocr\Scripts\surya_ocr.exe "%~1" --page_range %2 --output_dir "%~3"
