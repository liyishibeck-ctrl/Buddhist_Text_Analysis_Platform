param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$SkipDocker,
    [switch]$ForceRestart
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $RepoRoot ("data\\processed\\uvicorn-main-{0}.pid" -f $Port)
Set-Location $RepoRoot

function Test-TcpPort {
    param(
        [string]$TargetHost,
        [int]$TargetPort,
        [int]$TimeoutMs = 750
    )

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $asyncResult = $client.BeginConnect($TargetHost, $TargetPort, $null, $null)
        if (-not $asyncResult.AsyncWaitHandle.WaitOne($TimeoutMs)) {
            return $false
        }
        $client.EndConnect($asyncResult)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Wait-PostgresHealthy {
    param(
        [int]$MaxAttempts = 30,
        [int]$DelaySeconds = 2
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $status = docker inspect --format "{{.State.Health.Status}}" buddha-postgres 2>$null
        if ($LASTEXITCODE -eq 0 -and $status.Trim() -eq "healthy") {
            return
        }
        Start-Sleep -Seconds $DelaySeconds
    }

    throw "Postgres container buddha-postgres did not become healthy in time."
}

function Stop-ManagedAppProcess {
    if (-not (Test-Path -LiteralPath $PidFile)) {
        return $false
    }

    $pidText = (Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not $pidText) {
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
        return $false
    }

    $managedPid = [int]$pidText
    $process = Get-Process -Id $managedPid -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
        return $false
    }

    Write-Host ("Stopping stale managed app process {0}..." -f $managedPid)
    Stop-Process -Id $managedPid -Force

    for ($attempt = 1; $attempt -le 10; $attempt++) {
        if (-not (Test-TcpPort -TargetHost $BindHost -TargetPort $Port)) {
            Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
            return $true
        }
        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Get-ListeningProcessId {
    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $connection) {
            return [int]$connection.OwningProcess
        }
    }
    catch {
    }

    $line = netstat -ano -p TCP | Select-String (":{0}\s+.*LISTENING\s+(\d+)$" -f $Port) | Select-Object -First 1
    if ($line -and $line.Matches.Count -gt 0) {
        return [int]$line.Matches[0].Groups[1].Value
    }

    return $null
}

function Stop-ListeningProcess {
    $listeningPid = Get-ListeningProcessId
    if ($null -eq $listeningPid) {
        return $false
    }

    $process = Get-Process -Id $listeningPid -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        return $false
    }

    Write-Host ("Stopping process on port {0}: pid={1} name={2}" -f $Port, $listeningPid, $process.ProcessName)
    Stop-Process -Id $listeningPid -Force

    for ($attempt = 1; $attempt -le 10; $attempt++) {
        if (-not (Test-TcpPort -TargetHost $BindHost -TargetPort $Port)) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }

    return $false
}

if (Test-TcpPort -TargetHost $BindHost -TargetPort $Port) {
    try {
        $response = Invoke-WebRequest -Uri ("http://{0}:{1}/" -f $BindHost, $Port) -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            Write-Host ("App already running at http://{0}:{1}/" -f $BindHost, $Port)
            exit 0
        }
    }
    catch {
        $recovered = Stop-ManagedAppProcess
        if (-not $recovered -and $ForceRestart) {
            $recovered = Stop-ListeningProcess
        }
        if (-not $recovered) {
            throw ("Port {0} is already in use, but the web app did not answer on http://{1}:{0}/." -f $Port, $BindHost)
        }
    }
}

if (-not $SkipDocker) {
    Write-Host "Starting PostgreSQL container..."
    docker compose up -d postgres | Out-Host
    Wait-PostgresHealthy
}

python scripts/dev/launch_uvicorn_detached.py --host $BindHost --port $Port --root $RepoRoot

Write-Host ""
Write-Host ("Home:    http://{0}:{1}/" -f $BindHost, $Port)
Write-Host ("Catalog: http://{0}:{1}/works" -f $BindHost, $Port)
Write-Host ("Han:     http://{0}:{1}/works?tradition_id=trad-han" -f $BindHost, $Port)
Write-Host ("Pali:    http://{0}:{1}/works?tradition_id=trad-pali" -f $BindHost, $Port)
Write-Host ("Tibetan: http://{0}:{1}/works?tradition_id=trad-tibetan" -f $BindHost, $Port)
