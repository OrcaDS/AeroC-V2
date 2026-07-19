param(
    [string]$EvidenceRoot = "staging-evidence"
)

$ErrorActionPreference = "Stop"
$projectName = "aeroc-gate7"
$composeFile = "compose.smoke.yml"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$evidenceDirectory = Join-Path $EvidenceRoot "gate7-$timestamp"
New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null
$imageTag = "aeroc-gate7-backend:local"
$imageId = "unavailable"
$testResult = "NOT_RUN"

function Save-Text {
    param([string]$Name, [object]$Value)
    $Value | Out-File -FilePath (Join-Path $evidenceDirectory $Name) -Encoding utf8
}

function Invoke-DockerCompose {
    param(
        [string]$EvidenceName,
        [string[]]$Arguments,
        [switch]$AllowFailure
    )
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        # Windows PowerShell 5.1 surfaces native stderr as ErrorRecord objects.
        # Docker Compose writes normal progress output to stderr, so rely on its
        # process exit code instead of promoting progress lines to exceptions.
        $ErrorActionPreference = "Continue"
        $output = & docker compose -p $projectName -f $composeFile @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    Save-Text $EvidenceName $output
    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "docker compose $($Arguments -join ' ') failed with exit code $exitCode"
    }
    return @{ Output = $output; ExitCode = $exitCode }
}

function Wait-Ready {
    param([int]$TimeoutSeconds = 60)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            return Invoke-RestMethod http://localhost:18080/health/ready -TimeoutSec 5
        }
        catch {
            Start-Sleep -Seconds 2
        }
    } while ((Get-Date) -lt $deadline)
    throw "AeroC readiness did not become healthy within $TimeoutSeconds seconds"
}

try {
    Save-Text "00-metadata.txt" @(
        "captured_at=$((Get-Date).ToUniversalTime().ToString('o'))"
        "git_commit=$(git rev-parse HEAD)"
        "git_status="
        (git status --short)
        "docker_version="
        (docker version)
        "docker_compose_version=$(docker compose version)"
    )

    $engineOutput = & docker info --format "{{.OSType}} {{.ServerVersion}}" 2>&1
    $engineExitCode = $LASTEXITCODE
    Save-Text "00-docker-engine.txt" $engineOutput
    if ($engineExitCode -ne 0 -or ($engineOutput | Out-String) -notmatch "linux") {
        throw "Docker Linux engine is unavailable; Gate 7 requires a working Linux-container engine"
    }

    Invoke-DockerCompose "01-cleanup.log" @("down", "--volumes", "--remove-orphans") | Out-Null
    Invoke-DockerCompose "02-compose-config.yml" @("config") | Out-Null
    Invoke-DockerCompose "03-build.log" @("build") | Out-Null

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $imageOutput = & docker image inspect $imageTag --format "{{.Id}}" 2>&1
        $imageExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    Save-Text "03-image-identity.txt" @(
        "image_tag=$imageTag"
        "image_id=$(($imageOutput | Out-String).Trim())"
    )
    if ($imageExitCode -ne 0) {
        throw "Unable to inspect built image $imageTag"
    }
    $imageId = ($imageOutput | Out-String).Trim()

    $testContainerName = "aeroc-gate7-image-test-$timestamp"
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $testOutput = & docker run --rm --name $testContainerName `
            -e AEROC_ENV=test `
            -e AEROC_PROCESS_ROLE=api `
            -e DATABASE_HOST=localhost `
            -e DATABASE_PORT=5432 `
            -e DATABASE_NAME=aeroc_test `
            -e DATABASE_USER=aeroc_test `
            -e DATABASE_PASSWORD=gate7-test-only `
            -e DATABASE_SSLMODE=disable `
            $imageTag python -m pytest tests -q -p no:cacheprovider 2>&1
        $testExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    Save-Text "03-image-tests.log" $testOutput
    if ($testExitCode -ne 0) {
        $testResult = "FAIL"
        throw "Deployment image backend tests failed with exit code $testExitCode"
    }
    $testResult = "PASS"

    Invoke-DockerCompose "04-infrastructure-start.log" @("up", "-d", "postgres", "mock-open-meteo") | Out-Null
    Invoke-DockerCompose "05-migration.log" @("run", "--rm", "migrate") | Out-Null

    $revision = Invoke-DockerCompose "06-migration-revision.txt" @(
        "exec", "-T", "postgres", "psql", "-U", "aeroc_smoke", "-d", "aeroc_smoke",
        "-Atc", "SELECT version_num FROM alembic_version;"
    )
    if (($revision.Output | Out-String).Trim() -ne "d8a002901c1f") {
        throw "Unexpected Alembic revision"
    }

    Invoke-DockerCompose "07-seed-first.log" @("run", "--rm", "seed") | Out-Null
    Invoke-DockerCompose "08-seed-second.log" @("run", "--rm", "seed") | Out-Null

    Save-Text "09-mock-success.json" ((
        Invoke-RestMethod -Method Post "http://localhost:18081/control?mode=success"
    ) | ConvertTo-Json)
    Invoke-DockerCompose "10-collect-first.log" @("run", "--rm", "collect") | Out-Null
    Invoke-DockerCompose "11-collect-duplicate.log" @("run", "--rm", "collect") | Out-Null

    Save-Text "12-mock-partial.json" ((
        Invoke-RestMethod -Method Post "http://localhost:18081/control?mode=partial"
    ) | ConvertTo-Json)
    Invoke-DockerCompose "13-collect-partial.log" @("run", "--rm", "collect") | Out-Null
    Invoke-DockerCompose "14-partial-integrity.txt" @(
        "exec", "-T", "postgres", "psql", "-U", "aeroc_smoke", "-d", "aeroc_smoke",
        "-f", "/smoke/partial_integrity.sql"
    ) | Out-Null

    Save-Text "15-mock-recovery.json" ((
        Invoke-RestMethod -Method Post "http://localhost:18081/control?mode=recovery"
    ) | ConvertTo-Json)
    Invoke-DockerCompose "16-collect-recovery.log" @("run", "--rm", "collect") | Out-Null

    Invoke-DockerCompose "17-api-start.log" @("up", "-d", "api") | Out-Null
    $ready = Wait-Ready
    Save-Text "18-health-ready-initial.json" ($ready | ConvertTo-Json -Depth 10)
    Save-Text "19-health-live-initial.json" ((Invoke-RestMethod http://localhost:18080/health/live) | ConvertTo-Json -Depth 10)
    Save-Text "20-ops-status-initial.json" ((Invoke-RestMethod http://localhost:18080/ops/status) | ConvertTo-Json -Depth 10)

    $initialLogs = Invoke-DockerCompose "21-api-logs-initial.log" @("logs", "api")
    $initialStarts = @($initialLogs.Output | Select-String "event=scheduler_started").Count
    if ($initialStarts -ne 1) {
        throw "Expected exactly one scheduler startup before restart; found $initialStarts"
    }

    Invoke-DockerCompose "22-api-restart.log" @("restart", "api") | Out-Null
    $readyAfterRestart = Wait-Ready
    Save-Text "23-health-ready-after-restart.json" ($readyAfterRestart | ConvertTo-Json -Depth 10)
    Save-Text "24-ops-status-after-restart.json" ((Invoke-RestMethod http://localhost:18080/ops/status) | ConvertTo-Json -Depth 10)

    $restartLogs = Invoke-DockerCompose "25-api-logs-after-restart.log" @("logs", "api")
    $restartStarts = @($restartLogs.Output | Select-String "event=scheduler_started").Count
    if ($restartStarts -ne 2) {
        throw "Expected one scheduler startup per process generation; found $restartStarts total"
    }

    Invoke-DockerCompose "26-postgres-stop.log" @("stop", "postgres") | Out-Null
    $outageBodyPath = Join-Path $evidenceDirectory "27-health-during-outage-body.json"
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $statusOutput = & curl.exe --silent --show-error --max-time 10 `
            --output $outageBodyPath --write-out "%{http_code}" `
            http://localhost:18080/health/ready 2>&1
        $curlExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $statusText = ($statusOutput | Out-String).Trim()
    Save-Text "27-health-during-outage.txt" @(
        "expected_http_failure=true"
        "status_code=$statusText"
        "curl_exit_code=$curlExitCode"
    )
    if ($curlExitCode -ne 0 -or $statusText -ne "503") {
        throw "Expected readiness HTTP 503 during outage; received $statusText (curl exit $curlExitCode)"
    }

    Invoke-DockerCompose "28-postgres-start.log" @("start", "postgres") | Out-Null
    $readyAfterDatabaseRestart = Wait-Ready
    Save-Text "29-health-ready-after-database-restart.json" ($readyAfterDatabaseRestart | ConvertTo-Json -Depth 10)
    Save-Text "30-api-cities-after-database-restart.json" ((Invoke-RestMethod http://localhost:18080/api/v1/cities) | ConvertTo-Json -Depth 10)

    $scheduledBefore = @((Invoke-DockerCompose "31-api-logs-before-interval.log" @("logs", "api")).Output | Select-String "event=scheduled_collection_").Count
    $deadline = (Get-Date).AddSeconds(75)
    do {
        Start-Sleep -Seconds 3
        $intervalLogs = Invoke-DockerCompose "32-api-logs-after-interval.log" @("logs", "api")
        $scheduledAfter = @($intervalLogs.Output | Select-String "event=scheduled_collection_").Count
    } while ($scheduledAfter -le $scheduledBefore -and (Get-Date) -lt $deadline)
    if ($scheduledAfter -le $scheduledBefore) {
        throw "No recurring scheduled collection completed within the smoke interval"
    }

    Save-Text "33-mock-provider-stats.json" ((Invoke-RestMethod http://localhost:18081/stats) | ConvertTo-Json -Depth 10)
    Invoke-DockerCompose "34-final-integrity.txt" @(
        "exec", "-T", "postgres", "psql", "-U", "aeroc_smoke", "-d", "aeroc_smoke",
        "-f", "/smoke/integrity.sql"
    ) | Out-Null
    Invoke-DockerCompose "35-final-api-logs.log" @("logs", "api") | Out-Null
    Invoke-DockerCompose "36-final-container-state.txt" @("ps") | Out-Null

    Save-Text "RESULT.txt" @(
        "status=PASS"
        "completed_at=$((Get-Date).ToUniversalTime().ToString('o'))"
        "alembic_revision=d8a002901c1f"
        "postgres_major=17"
        "image_tag=$imageTag"
        "image_id=$imageId"
        "tests=$testResult"
        "scheduler_start_events=$restartStarts"
        "evidence_directory=$evidenceDirectory"
    )
    Write-Host "Gate 7 smoke test passed. Evidence: $evidenceDirectory"
}
catch {
    Save-Text "RESULT.txt" @(
        "status=FAIL"
        "failed_at=$((Get-Date).ToUniversalTime().ToString('o'))"
        "error=$($_.Exception.Message)"
        "image_tag=$imageTag"
        "image_id=$imageId"
        "tests=$testResult"
        "evidence_directory=$evidenceDirectory"
    )
    try {
        Invoke-DockerCompose "failure-container-state.txt" @("ps") -AllowFailure | Out-Null
        Invoke-DockerCompose "failure-api-logs.log" @("logs", "api") -AllowFailure | Out-Null
        Invoke-DockerCompose "failure-postgres-logs.log" @("logs", "postgres") -AllowFailure | Out-Null
    }
    catch {
    }
    throw
}
