#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT/mcuenv.py" "$@"
fi

if command -v python >/dev/null 2>&1; then
  exec python "$ROOT/mcuenv.py" "$@"
fi

echo "Python 3.11+ is required for mcuenv.py" >&2
exit 1
