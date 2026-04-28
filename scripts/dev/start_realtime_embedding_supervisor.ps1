param(
    [Parameter(Mandatory = $true)]
    [string]$TraditionId,

    [Parameter(Mandatory = $true)]
    [string]$ContentField,

    [Parameter(Mandatory = $true)]
    [string]$StateFile,

    [int]$Concurrency = 1,
    [int]$MaxSegmentsPerRequest = 64,
    [int]$MaxSegmentsPerRun = 256,
    [double]$PauseSeconds = 1.0,
    [Nullable[int]]$MaxRuns = $null,
    [Nullable[int]]$MinTextLength = $null,
    [Nullable[int]]$MaxTextLength = $null,
    [Nullable[int]]$MinRoutingTokens = $null,
    [Nullable[int]]$MaxRoutingTokens = $null
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$logDir = Join-Path $root 'data\processed\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$slugParts = @($TraditionId, $ContentField)
if ($MinTextLength -ne $null) { $slugParts += "minlen$MinTextLength" }
if ($MaxTextLength -ne $null) { $slugParts += "maxlen$MaxTextLength" }
if ($MinRoutingTokens -ne $null) { $slugParts += "minrt$MinRoutingTokens" }
if ($MaxRoutingTokens -ne $null) { $slugParts += "maxrt$MaxRoutingTokens" }
$slug = ($slugParts -join '-').Replace('_', '-')

$stdoutPath = Join-Path $logDir ("realtime-{0}-supervisor-{1}.out.log" -f $slug, $timestamp)
$stderrPath = Join-Path $logDir ("realtime-{0}-supervisor-{1}.err.log" -f $slug, $timestamp)
$statePath = (Resolve-Path -LiteralPath (Split-Path -Parent $StateFile) -ErrorAction SilentlyContinue)
if (-not $statePath) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StateFile) | Out-Null
}
$stateFilePath = [System.IO.Path]::GetFullPath($StateFile)
$supervisorStatePath = [System.IO.Path]::ChangeExtension($stateFilePath, '.json')
$processArgs = @(
    '-u',
    'scripts/analysis/run_realtime_embedding_supervisor.py',
    '--state-file', $supervisorStatePath,
    '-TraditionId', $TraditionId,
    '-ContentField', $ContentField,
    '-Concurrency', $Concurrency.ToString(),
    '-MaxSegmentsPerRequest', $MaxSegmentsPerRequest.ToString(),
    '-MaxSegmentsPerRun', $MaxSegmentsPerRun.ToString(),
    '-PauseSeconds', $PauseSeconds.ToString([System.Globalization.CultureInfo]::InvariantCulture)
)
if ($MaxRuns -ne $null) { $processArgs += @('-MaxRuns', $MaxRuns.ToString()) }
if ($MinTextLength -ne $null) { $processArgs += @('-MinTextLength', $MinTextLength.ToString()) }
if ($MaxTextLength -ne $null) { $processArgs += @('-MaxTextLength', $MaxTextLength.ToString()) }
if ($MinRoutingTokens -ne $null) { $processArgs += @('-MinRoutingTokens', $MinRoutingTokens.ToString()) }
if ($MaxRoutingTokens -ne $null) { $processArgs += @('-MaxRoutingTokens', $MaxRoutingTokens.ToString()) }

$processArgs = $processArgs `
    -replace '^-TraditionId$', '--tradition-id' `
    -replace '^-ContentField$', '--content-field' `
    -replace '^-Concurrency$', '--concurrency' `
    -replace '^-MaxSegmentsPerRequest$', '--max-segments-per-request' `
    -replace '^-MaxSegmentsPerRun$', '--max-segments-per-run' `
    -replace '^-PauseSeconds$', '--pause-seconds' `
    -replace '^-MaxRuns$', '--max-runs' `
    -replace '^-MinTextLength$', '--min-text-length' `
    -replace '^-MaxTextLength$', '--max-text-length' `
    -replace '^-MinRoutingTokens$', '--min-routing-tokens' `
    -replace '^-MaxRoutingTokens$', '--max-routing-tokens'

$process = Start-Process `
    -FilePath 'python' `
    -ArgumentList $processArgs `
    -WorkingDirectory $root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath `
    -PassThru

@(
    "PID=$($process.Id)"
    "STDOUT=$stdoutPath"
    "STDERR=$stderrPath"
    "STARTED_AT=$([DateTime]::UtcNow.ToString('s'))Z"
    "SUPERVISOR_STATE=$supervisorStatePath"
    "TRADITION_ID=$TraditionId"
    "CONTENT_FIELD=$ContentField"
    "EMBEDDING_MODEL=text-embedding-3-large"
    "STORAGE_EMBEDDING_MODEL=text-embedding-3-large"
    "DIMENSION=2048"
) | Set-Content -Path $stateFilePath -Encoding UTF8

Write-Output "PID=$($process.Id)"
Write-Output "STDOUT=$stdoutPath"
Write-Output "STDERR=$stderrPath"
Write-Output "STATE=$stateFilePath"
Write-Output "SUPERVISOR_STATE=$supervisorStatePath"
