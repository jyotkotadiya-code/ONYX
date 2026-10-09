# Start Local Multimodal RAG Backend (FastAPI on 127.0.0.1:8000)
$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

Write-Host "Starting ONYX Local Multimodal RAG Backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
if (Test-Path "$RootDir\.venv\Scripts\python.exe") {
    & "$RootDir\.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
} else {
    python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
}
