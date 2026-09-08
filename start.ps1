param([string]$Node = "node")

$ErrorActionPreference = "Stop"
$backendDir = Join-Path $PSScriptRoot "backend"
$frontendDir = Join-Path $PSScriptRoot "frontend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython) -or
    -not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules\vite\bin\vite.js"))) {
    throw "Dependencies are missing. Run .\install.ps1 first."
}
$nodeCommand = (Get-Command $Node -ErrorAction Stop).Source
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
    while ($true) {
        foreach ($job in $jobs) {
            Receive-Job $job
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
