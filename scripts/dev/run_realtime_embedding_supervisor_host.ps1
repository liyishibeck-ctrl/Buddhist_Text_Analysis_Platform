param(
    [Parameter(Mandatory = $true)]
    [string]$Root,

    [Parameter(Mandatory = $true)]
    [string]$StdoutPath,

    [Parameter(Mandatory = $true)]
    [string]$StderrPath,

    [Parameter(Mandatory = $true)]
    [string]$SupervisorStateFile,

    [Parameter(Mandatory = $true)]
    [string]$TraditionId,

    [Parameter(Mandatory = $true)]
    [string]$ContentField,

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

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StdoutPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StderrPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $SupervisorStateFile) | Out-Null

Set-Location $Root

$argList = @(
    '-u',
    'scripts/analysis/run_realtime_embedding_supervisor.py',
    '--state-file', $SupervisorStateFile,
    '--tradition-id', $TraditionId,
    '--content-field', $ContentField,
    '--concurrency', $Concurrency.ToString(),
    '--max-segments-per-request', $MaxSegmentsPerRequest.ToString(),
    '--max-segments-per-run', $MaxSegmentsPerRun.ToString(),
    '--pause-seconds', $PauseSeconds.ToString([System.Globalization.CultureInfo]::InvariantCulture)
)

if ($MaxRuns -ne $null) { $argList += @('--max-runs', $MaxRuns.ToString()) }
if ($MinTextLength -ne $null) { $argList += @('--min-text-length', $MinTextLength.ToString()) }
if ($MaxTextLength -ne $null) { $argList += @('--max-text-length', $MaxTextLength.ToString()) }
if ($MinRoutingTokens -ne $null) { $argList += @('--min-routing-tokens', $MinRoutingTokens.ToString()) }
if ($MaxRoutingTokens -ne $null) { $argList += @('--max-routing-tokens', $MaxRoutingTokens.ToString()) }

python @argList 1>> $StdoutPath 2>> $StderrPath
