# First-Run Setup Script for ONYX 100% Local Multimodal RAG
$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  ONYX 100% LOCAL MULTIMODAL RAG — FIRST-RUN SETUP" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1-5. Run environment check
& "$PSScriptRoot\check_environment.ps1"

# 6. Copy .env.example to .env if missing
if (-not (Test-Path "$RootDir\.env")) {
    Copy-Item "$RootDir\.env.example" "$RootDir\.env"
    Write-Host "[✓] Created .env from .env.example" -ForegroundColor Green
}

# 7. Install Python dependencies
Write-Host "`n[Step] Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install -r "$RootDir\requirements.txt"

# 8. Install Frontend dependencies
Write-Host "`n[Step] Installing Frontend dependencies..." -ForegroundColor Yellow
Push-Location "$RootDir\frontend"
npm install
Pop-Location

# 9. Download required local embedding model & initialize SQLite + ChromaDB
Write-Host "`n[Step] Initializing SQLite database, ChromaDB vector store, and local embedding model..." -ForegroundColor Yellow
python -c "from backend.auth.auth_handler import init_db_and_defaults; from backend.embeddings.embedding_service import embedding_service; from backend.database.vector_store import vector_store; init_db_and_defaults(); embedding_service.load_model(); print('Vector DB status:', vector_store.get_status())"

Write-Host "`n[✓] Setup completed! Run .\scripts\start_all.ps1 to launch the application." -ForegroundColor Green
