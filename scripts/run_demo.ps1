# run_demo.ps1
# Starts the RailMesh backend, frontend, and injects a disruption to start the demo.

$ErrorActionPreference = "Stop"

Write-Host "🚂 Starting RailMesh Demo..." -ForegroundColor Cyan

# 1. Start Backend
Write-Host "Starting FastAPI backend..." -ForegroundColor Yellow
$BackendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd backend; .\.venv\Scripts\activate; uvicorn api.main:app --reload --port 8000" -PassThru
Start-Sleep -Seconds 3

# 2. Start Frontend
Write-Host "Starting Vite frontend..." -ForegroundColor Yellow
$FrontendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev" -PassThru
Start-Sleep -Seconds 4

# 3. Inject Disruption
Write-Host "Injecting Scenario 1 disruption..." -ForegroundColor Green
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/scenarios/inject" -Method Post -Body '{"scenario_id": "scenario_1_two_train_conflict"}' -ContentType "application/json"
    Write-Host "Disruption injected successfully. Session ID: $($response.session_id)" -ForegroundColor Green
} catch {
    Write-Host "Failed to inject disruption. Is the backend running on port 8000?" -ForegroundColor Red
}

Write-Host "Demo is running! Open http://localhost:5173 to view the dashboard." -ForegroundColor Cyan
Write-Host "Press any key to stop all services..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Cleanup
Write-Host "Stopping services..."
Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $FrontendProcess.Id -Force -ErrorAction SilentlyContinue
Write-Host "Done."
