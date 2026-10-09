# Check Environment & Local AI Stack Status
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  ONYX LOCAL MULTIMODAL RAG — ENVIRONMENT DIAGNOSTICS" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. OS & Hardware
$cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
$gpus = Get-CimInstance Win32_VideoController | ForEach-Object { "$($_.Name) ($([math]::Round($_.AdapterRAM / 1GB, 1)) GB)" }

Write-Host "[Hardware]" -ForegroundColor Yellow
Write-Host "  CPU : $cpu"
Write-Host "  RAM : $ramGB GB"
Write-Host "  GPU : $($gpus -join ', ')"

# 2. Core Developer Tools
Write-Host "`n[Core Tools]" -ForegroundColor Yellow
try {
    $pyVer = python --version 2>&1
    Write-Host "  Python  : $pyVer" -ForegroundColor Green
} catch {
    Write-Host "  Python  : NOT FOUND (Install Python 3.11+ from https://python.org)" -ForegroundColor Red
}

try {
    $nodeVer = node --version 2>&1
    Write-Host "  Node.js : $nodeVer" -ForegroundColor Green
} catch {
    Write-Host "  Node.js : NOT FOUND (Install Node.js LTS from https://nodejs.org)" -ForegroundColor Red
}

try {
    $gitVer = git --version 2>&1
    Write-Host "  Git     : $gitVer" -ForegroundColor Green
} catch {
    Write-Host "  Git     : NOT FOUND" -ForegroundColor Red
}

# 3. Local LLM Runtime (Ollama / LM Studio)
Write-Host "`n[Local LLM Runtime]" -ForegroundColor Yellow
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCmd) {
    Write-Host "  Ollama Binary : Found at $($ollamaCmd.Source)" -ForegroundColor Green
    $models = ollama list 2>&1
    Write-Host "  Ollama Models :`n$models"
} else {
    $installer = "$env:USERPROFILE\Downloads\OllamaSetup.exe"
    if (Test-Path $installer) {
        Write-Host "  Ollama Binary : Currently uninstalled, but installer found at $installer" -ForegroundColor Yellow
        Write-Host "  To restore your Lexi Llama 3.1 8B model, run:" -ForegroundColor Cyan
        Write-Host "    Start-Process '$installer' -Wait"
        Write-Host "    ollama run hf.co/bartowski/Llama-3.1-8B-Lexi-Uncensored-V2-GGUF:Q4_K_M"
    } else {
        Write-Host "  Ollama Binary : Not found in PATH (Local Extractive Grounding Engine will act as fallback)" -ForegroundColor Yellow
    }
}

try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "  Ollama API    : ONLINE (http://127.0.0.1:11434)" -ForegroundColor Green
} catch {
    Write-Host "  Ollama API    : OFFLINE (http://127.0.0.1:11434 not listening)" -ForegroundColor Yellow
}

Write-Host "==========================================================" -ForegroundColor Cyan
