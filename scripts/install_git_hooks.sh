#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Installs local Git hooks for this repository.
#
# Hooks are stored under .git/hooks and are not versioned by Git. This script is
# versioned so a clone can reproduce the same local guardrails.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".git" ]; then
  echo "This script must be run from inside a Git worktree." >&2
  exit 1
fi

mkdir -p .git/hooks

cat > .git/hooks/pre-push <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail

bash scripts/run_all_checks.sh
HOOK

chmod +x .git/hooks/pre-push

echo "Installed .git/hooks/pre-push"
echo "The hook runs: bash scripts/run_all_checks.sh"
