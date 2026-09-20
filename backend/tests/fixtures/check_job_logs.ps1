param([string]$Launcher, [string]$Python, [string]$Fixture)
$ErrorActionPreference = "Stop"
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Launcher, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw "Launcher syntax error" }
# Execute the real launcher's monitoring loop against a harmless native process.
$loop = $ast.Find({ param($node)
    $node -is [System.Management.Automation.Language.ForEachStatementAst] -and
    $node.Extent.Text.Contains('Receive-Job')
}, $true)
if (-not $loop) { throw "Launcher monitoring loop not found" }
$monitor = [scriptblock]::Create($loop.Extent.Text)
$job = Start-Job -ArgumentList $Python, $Fixture -ScriptBlock {
    param($PythonExecutable, $FixturePath)
    & $PythonExecutable $FixturePath
    throw "Fixture exited with code $LASTEXITCODE"
}
$jobs = @($job)
try {
    $deadline = (Get-Date).AddSeconds(20)
    while (-not $job.HasMoreData -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 25 }
    if ($job.State -ne 'Running') { throw "Fixture did not stay running for log verification" }
    & $monitor
    Write-Host 'HEALTHY_STDERR_ACCEPTED'
    Wait-Job $job -Timeout 15 | Out-Null
    try {
        & $monitor
        throw "Service exit was not detected"
    }
    catch {
        if ($_.Exception.Message -notlike 'A service stopped.*') { throw }
        Write-Host 'SERVICE_EXIT_DETECTED'
    }
}
finally {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -Force -ErrorAction SilentlyContinue
}
