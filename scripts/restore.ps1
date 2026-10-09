# Local Restore Script for ONYX Multimodal RAG
param(
    [Parameter(Mandatory=$true)]
    [string]$BackupZipPath
)
$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path $BackupZipPath)) {
    Write-Error "Backup archive not found: $BackupZipPath"
    exit 1
}

$DataDir = Join-Path $RootDir "data"
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

Expand-Archive -Path $BackupZipPath -DestinationPath $DataDir -Force
Write-Host "[✓] Successfully restored local vector_db, metadata, and uploads from $BackupZipPath" -ForegroundColor Green
