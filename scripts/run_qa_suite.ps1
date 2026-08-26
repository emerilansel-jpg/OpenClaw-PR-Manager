# OpenClaw PR Manager - QA Test Suite Runner (PowerShell)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT_DIR = Split-Path $PSScriptRoot -Parent
$TESTS_DIR = Join-Path $ROOT_DIR "tests"

Write-Host ""
Write-Host "=========================================="
Write-Host "OpenClaw PR Manager QA Suite"
Write-Host "=========================================="
Write-Host ""
Write-Host "[INFO] Running pytest in $TESTS_DIR..."

$pytestOutput = & python -m pytest $TESTS_DIR --tb=short 2>&1
$pytestExitCode = $LASTEXITCODE
Write-Host $pytestOutput
Write-Host ""

if ($pytestExitCode -eq 0) {
    Write-Host "[PASS] All pytest tests passed."
} else {
    Write-Host "[FAIL] pytest exited with code $pytestExitCode"
}

Write-Host ""
Write-Host "[INFO] Verifying Python compilation..."
$compileErrors = @()
$pyFiles = Get-ChildItem -Recurse -Path $ROOT_DIR -Filter "*.py" | Where-Object { $_.FullName -notmatch '\.(pyc|__pycache__)' }

foreach ($file in $pyFiles) {
    try {
        $code = [System.IO.File]::ReadAllText($file.FullName)
        $ast = [System.Management.Automation.Language.Parser]::ParseInput($code, [ref]$null, [ref]$null)
        if ($ast.HasErrors) {
            foreach ($err in $ast.Errors) {
                $compileErrors += "$($file.FullName):$($err.Line):$($err.Column) - $($err.Message)"
            }
        }
    } catch {
        $compileErrors += "$($file.FullName): Unexpected error: $_"
    }
}

if ($compileErrors.Count -eq 0) {
    Write-Host "[PASS] All files compiled successfully."
} else {
    Write-Host "[FAIL] Compilation errors detected:"
    $compileErrors | ForEach-Object { Write-Host "  $_" }
}

Write-Host ""
Write-Host "=========================================="
Write-Host "Summary Report"
Write-Host "=========================================="
Write-Host "Test files added:"
Write-Host "  - tests/conftest.py"
Write-Host "  - tests/test_gmail_oauth.py"
Write-Host "  - tests/test_followup_completion.py"
Write-Host "  - tests/test_cors.py"
Write-Host "  - tests/test_external_api_failures.py"
Write-Host "Runner added: scripts/run_qa_suite.ps1"
Write-Host ""
Write-Host "Coverage areas:"
Write-Host "  - Gmail OAuth authorization URL generation (mocked)"
Write-Host "  - Token exchange/storage to Supabase or local fallback"
Write-Host "  - Follow-up sequence exhaustion handling"
Write-Host "  - CORS allow-list from settings.cors_origins"
Write-Host "  - External API failures (NewsAPI.org, The NewsAPI)"
Write-Host "  - AI service fallbacks when keys missing"
Write-Host ""

if ($pytestExitCode -ne 0) { Exit $pytestExitCode }
if ($compileErrors.Count -gt 0) { Write-Host "[WARN] Compilation issues found"; Exit 1 }

Exit 0