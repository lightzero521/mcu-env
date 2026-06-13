#!/usr/bin/env bash
# Activate the MCU development environment in the current shell session.
# Usage:
#   source /path/to/mcu-env/export.sh

set -euo pipefail

MCUENV_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "Python 3.11+ is required to activate mcuenv." >&2
  return 1 2>/dev/null || exit 1
fi

eval "$("$PYTHON" "$MCUENV_ROOT/mcuenv.py" export --format bash)"
echo "mcuenv activated: $MCUENV_ROOT"
