#!/usr/bin/env pwsh
# Local runner for the skill format linter (Windows / PowerShell).
# Mirrors the CI step: ensure PyYAML is available, then lint every SKILL.md.
# Usage:
#   pwsh tools/lint.ps1                       # lint all skills (recursive discovery)
#   pwsh tools/lint.ps1 examples/dependabot-maintenance   # lint a specific skill
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

python -c "import yaml" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyYAML not found; installing into the current Python..."
    python -m pip install --quiet pyyaml
}

python tools/lint_skill.py @args
exit $LASTEXITCODE
