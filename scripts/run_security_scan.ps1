# CodeVault Security Scan Script
# Execute all security tools and output to .security_reports/

$ReportDir = ".security_reports"

if (!(Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null
}

Write-Host "🥒 Pickle Rick Security Scan Initiated..." -ForegroundColor Green

# Helper function to run command and ignore exit code
function Run-Scan {
    param(
        [string]$Name,
        [scriptblock]$Command
    )
    Write-Host "[$Name] Scanning..." -ForegroundColor Cyan
    try {
        & $Command
        Write-Host "[$Name] Done." -ForegroundColor Green
    } catch {
        Write-Host "[$Name] Failed/Found Issues: $_" -ForegroundColor Yellow
    }
}

# 1. TruffleHog (Git History)
Run-Scan "TruffleHog" {
    # Check if .git exists first
    if (Test-Path ".git") {
        # Scan current directory history, exclude heavy dirs
        cmd /c "trufflehog3 . --depth 5 --exclude node_modules --exclude venv --exclude .venv --exclude .git -f JSON > ""$ReportDir/trufflehog.json"" 2>nul"
    } else {
        Write-Host "Skipping TruffleHog (No .git directory)" -ForegroundColor Red
    }
}

# 2. Detect-Secrets (Current State)
Run-Scan "Detect-Secrets" {
    detect-secrets scan | Out-File -Encoding utf8 "$ReportDir/detect-secrets.json"
}

# 3. Bandit (Python SAST)
Run-Scan "Bandit" {
    # Bandit returns 1 on issues found, we need to allow that
    cmd /c "bandit -r . -f json -o ""$ReportDir/bandit.json"" -x ""tests,test_projects,.venv,venv"" 2>nul"
}

# 4. Safety (Python Dependencies)
Run-Scan "Safety" {
    cmd /c "safety check --json > ""$ReportDir/safety.json"" 2>nul"
}

# 5. Pip-Audit (Python Dependencies)
Run-Scan "Pip-Audit" {
    cmd /c "pip-audit -f json > ""$ReportDir/pip-audit.json"" 2>nul"
}

# 6. NPM Audit (Node Dependencies)
Run-Scan "NPM Audit" {
    cmd /c "npm audit --json > ""$ReportDir/npm-audit.json"" 2>nul"
}

Write-Host "🥒 Scan Complete. Reports saved to $ReportDir" -ForegroundColor Green
