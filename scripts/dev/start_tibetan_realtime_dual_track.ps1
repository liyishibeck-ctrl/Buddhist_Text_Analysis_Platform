param(
    [string]$MainStateFile = "data/processed/logs/latest_realtime_embedding_worker_tibetan_main.txt",
    [string]$SlowStateFile = "data/processed/logs/latest_realtime_embedding_worker_tibetan_slow.txt"
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root

& (Join-Path $root 'scripts\dev\start_realtime_embedding_supervisor.ps1') `
    -TraditionId 'trad-tibetan' `
    -ContentField 'normalized_content' `
    -StateFile $MainStateFile `
    -Concurrency 4 `
    -MaxSegmentsPerRequest 256 `
    -MaxSegmentsPerRun 1024 `
    -PauseSeconds 1 `
    -MaxTextLength 1999 `
    -MaxRoutingTokens 3499

& (Join-Path $root 'scripts\dev\start_realtime_embedding_supervisor.ps1') `
    -TraditionId 'trad-tibetan' `
    -ContentField 'normalized_content' `
    -StateFile $SlowStateFile `
    -Concurrency 1 `
    -MaxSegmentsPerRequest 64 `
    -MaxSegmentsPerRun 64 `
    -PauseSeconds 2 `
    -MinTextLength 2000

Write-Host ""
Write-Host "Main watchdog:"
Write-Host "python scripts/analysis/watch_realtime_embedding_worker.py --state-file $MainStateFile --interval 30 --stall-seconds 180"
Write-Host ""
Write-Host "Slow watchdog:"
Write-Host "python scripts/analysis/watch_realtime_embedding_worker.py --state-file $SlowStateFile --interval 30 --stall-seconds 180"
