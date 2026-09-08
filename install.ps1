param([string]$Python = "python", [string]$Npm = "npm.cmd")

$ErrorActionPreference = "Stop"
$venvPython = Join-Path $PSScriptRoot "backend\.venv\Scripts\python.exe"
Push-Location $PSScriptRoot
try {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        if (Test-Path -LiteralPath "backend\.venv") {
            throw "backend/.venv already exists but is not a Windows Python environment. Check it before reinstalling."
        }
        & $Python -m venv backend/.venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
        if (-not (Test-Path -LiteralPath $venvPython)) {
            throw "Use -Python with a standard Windows Python 3.11+ executable."
        }
    }
    & $venvPython -m pip install -e './backend[dev]'
    if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }
    & $Npm --prefix frontend ci
    if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." }
    Write-Host "Installation complete. Run .\start.ps1 to launch the app."
}
finally { Pop-Location }
