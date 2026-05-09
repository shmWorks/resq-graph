param([string]$Command = "help")

$PYTHON = Join-Path $PSScriptRoot "venv\Scripts\python.exe"

if ($Command -eq "baseline") {
    Write-Host "[Sprint 8] Running baseline batch ..." -ForegroundColor Cyan
    & $PYTHON src\run_baseline.py --headless --config headless_baseline.yaml

} elseif ($Command -eq "ai") {
    Write-Host "[Sprint 9] Running AI fleet batch ..." -ForegroundColor Green
    & $PYTHON src\run_ai_fleet.py --headless --config headless_ai.yaml

} elseif ($Command -eq "analyze") {
    Write-Host "[Sprint 9] Running comparison analysis ..." -ForegroundColor Green
    & $PYTHON src\analyze_comparison.py

} elseif ($Command -eq "demo") {
    Write-Host "[Sprint 9] Launching split-screen demo (press ENTER in window to start) ..." -ForegroundColor Yellow
    & $PYTHON src\split_screen_demo.py

} elseif ($Command -eq "test") {
    Write-Host "[Tests] Running full pytest suite ..." -ForegroundColor Magenta
    & $PYTHON -m pytest tests/ -q --tb=short

} elseif ($Command -eq "all") {
    Write-Host "[Sprint 9] Running full Sprint 9 pipeline ..." -ForegroundColor White
    Write-Host "Step 1/3 - AI fleet runs" -ForegroundColor Green
    & $PYTHON src\run_ai_fleet.py --headless --config headless_ai.yaml
    Write-Host "Step 2/3 - Statistical analysis + plots + report" -ForegroundColor Green
    & $PYTHON src\analyze_comparison.py
    Write-Host "Step 3/3 - Split-screen demo" -ForegroundColor Yellow
    & $PYTHON src\split_screen_demo.py

} else {
    Write-Host ""
    Write-Host "ResQ-Graph Sprint 9 Runner" -ForegroundColor Cyan
    Write-Host "--------------------------"
    Write-Host "  .\run.ps1 ai       - Run 10x AI fleet headless simulations"
    Write-Host "  .\run.ps1 analyze  - Statistical comparison + 4 plots + report"
    Write-Host "  .\run.ps1 demo     - Pygame split-screen demo"
    Write-Host "  .\run.ps1 all      - Run all three steps above in sequence"
    Write-Host "  .\run.ps1 baseline - Re-run Sprint 8 baseline (if needed)"
    Write-Host "  .\run.ps1 test     - Run full pytest suite"
    Write-Host ""
    Write-Host "Outputs:" -ForegroundColor Gray
    Write-Host "  outputs/ai_results.csv"
    Write-Host "  outputs/comparison_metrics.json"
    Write-Host "  outputs/figures/ (4 comparison plots)"
    Write-Host "  outputs/comparison_report.md"
}
