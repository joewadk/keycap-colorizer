param([string]$Node = "node", [switch]$CheckOnly)

$ErrorActionPreference = "Stop"
$backendDir = Join-Path $PSScriptRoot "backend"
$frontendDir = Join-Path $PSScriptRoot "frontend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython) -or
    -not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules\vite\bin\vite.js"))) {
    throw "Dependencies are missing. Run .\install.ps1 first."
}
$nodeCommand = (Get-Command $Node -ErrorAction Stop).Source
# Avoid embedded quotes: Windows PowerShell 5 strips them from native arguments.
& $nodeCommand -e 'if (parseInt(process.versions.node) < 24) process.exit(1)'
if ($LASTEXITCODE -ne 0) { throw "Node.js check failed. Install Node.js 24+ or pass -Node with its executable path." }
Push-Location -LiteralPath $backendDir
try {
    & $venvPython -m app.startup
    if ($LASTEXITCODE -ne 0) { throw "Startup checks failed. Fix the issue above, then try again." }
}
finally { Pop-Location }
if ($CheckOnly) {
    Write-Host "Startup checks passed. No services started."
    return
}
$jobs = @()
try {
    $jobs += Start-Job -ArgumentList $backendDir, $venvPython -ScriptBlock {
        param($Directory, $PythonExecutable)
        Set-Location -LiteralPath $Directory
        & $PythonExecutable -m uvicorn app.main:app --host 127.0.0.1 --port 8000
        throw "Backend exited with code $LASTEXITCODE"
    }
    $jobs += Start-Job -ArgumentList $frontendDir, $nodeCommand -ScriptBlock {
        param($Directory, $NodeExecutable)
        Set-Location -LiteralPath $Directory
        & $NodeExecutable node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
        throw "Frontend exited with code $LASTEXITCODE"
    }
    Write-Host "Starting services. Open http://localhost:5173 when Vite reports ready."
    Write-Host "Press Ctrl+C to stop both services."
    Write-Host "Save design / Load saved designs are available below the preview. Product URL intake is not connected yet."
    while ($true) {
        foreach ($job in $jobs) {
            # Native stderr (including Uvicorn INFO logs) becomes an error record in
            # Windows PowerShell. Display it as text; job state below determines failure.
            Receive-Job $job -ErrorAction Continue 2>&1 | ForEach-Object { Write-Host $_.ToString() }
            if ($job.State -in @("Completed", "Failed", "Stopped")) {
                throw "A service stopped. See its output above."
            }
        }
        Start-Sleep -Milliseconds 250
    }
}
finally {
    foreach ($job in $jobs) {
        Stop-Job $job -ErrorAction SilentlyContinue
        Remove-Job $job -Force -ErrorAction SilentlyContinue
    }
}
