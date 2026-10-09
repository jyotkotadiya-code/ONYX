# Local Backup Script for ONYX Multimodal RAG (Vector DB + SQLite Metadata + Uploads)
param(
    [string]$BackupRoot = "$PSScriptRoot\..\backups"
)
$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$TargetDir = Join-Path $BackupRoot "rag_backup_$Timestamp"

New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

foreach ($sub in @("vector_db", "metadata", "uploads")) {
    $src = Join-Path "$RootDir\data" $sub
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination (Join-Path $TargetDir $sub) -Recurse -Force
    }
}

$ArchivePath = "$TargetDir.zip"
Compress-Archive -Path "$TargetDir\*" -DestinationPath $ArchivePath -Force
Remove-Item -Path $TargetDir -Recurse -Force

Write-Host "[✓] Local backup created at: $ArchivePath" -ForegroundColor Green
