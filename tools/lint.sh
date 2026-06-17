#!/usr/bin/env bash
# Local runner for the skill format linter (macOS / Linux).
# Mirrors the CI step: ensure PyYAML is available, then lint every SKILL.md.
# Usage:
#   bash tools/lint.sh                                  # lint all skills (recursive discovery)
#   bash tools/lint.sh examples/dependabot-maintenance  # lint a specific skill
set -euo pipefail
cd "$(dirname "$0")/.."

if ! python3 -c "import yaml" 2>/dev/null; then
  echo "PyYAML not found; installing into the current Python..."
  python3 -m pip install --quiet pyyaml
fi

exec python3 tools/lint_skill.py "$@"
