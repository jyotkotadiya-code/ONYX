# Start Local Multimodal RAG Frontend (Vite on 0.0.0.0:3000 for LAN/Team access)
$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location "$RootDir\frontend"

Write-Host "Starting ONYX Local Multimodal RAG Frontend on http://0.0.0.0:3000 ..." -ForegroundColor Green
npm run dev
