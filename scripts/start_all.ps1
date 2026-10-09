# Start Complete ONYX Local Multimodal RAG Application (Backend + Frontend)
$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  STARTING ONYX 100% LOCAL MULTIMODAL RAG SYSTEM" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Start Backend in a background PowerShell process
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$PSScriptRoot\start_backend.ps1"

# Start Frontend in a background PowerShell process
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$PSScriptRoot\start_frontend.ps1"

$lanIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch "Loopback" -and $_.IPAddress -notmatch "^169\.254" } | Select-Object -First 1).IPAddress
Write-Host "`nServices launched!" -ForegroundColor Green
Write-Host "  Local UI        : http://localhost:3000" -ForegroundColor Cyan
if ($lanIp) {
    Write-Host "  Team LAN Access : http://${lanIp}:3000" -ForegroundColor Cyan
}
Write-Host "  Backend API     : http://127.0.0.1:8000/docs" -ForegroundColor Cyan
