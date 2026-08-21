# run_all.ps1
# This script automates the execution of the entire benchmarking suite across all databases.

# Activate virtual environment if it exists
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    .\.venv\Scripts\Activate.ps1
}

$databases = @("cognodb", "neo4j", "memgraph", "arangodb")

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Starting Graph Database Benchmarking Suite" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

foreach ($db in $databases) {
    Write-Host "`n>>> Processing Database: $db <<<" -ForegroundColor Yellow
    
    # 1. Ingest Data
    Write-Host "--> Running Ingestion for $db..." -ForegroundColor Green
    python -m src.benchmark.main ingest $db
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Ingestion failed for $db. Skipping benchmark run." -ForegroundColor Red
        continue
    }

    # 2. Run Benchmarks
    Write-Host "--> Running Benchmarks for $db..." -ForegroundColor Green
    python -m src.benchmark.main run $db --runs 100 --warmup 20
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[+] Benchmarks completed successfully for $db." -ForegroundColor Green
    } else {
        Write-Host "[!] Benchmarks failed for $db." -ForegroundColor Red
    }
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "All benchmark runs completed!" -ForegroundColor Cyan
Write-Host "Run 'python src/benchmark/generate_report.py' to create charts." -ForegroundColor Cyan
