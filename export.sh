#!/usr/bin/env bash
# Activate the MCU development environment in the current shell session.
# Usage:
#   source /path/to/mcu-env/export.sh
#
# After activation:
#   mcuenv.py doctor
#   mcuenv.py build
#   deactivate

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

if [[ "${MCUENV_ACTIVE:-}" == "1" ]]; then
  echo "mcuenv is already active. Run 'deactivate' first." >&2
  return 1 2>/dev/null || exit 1
fi

export MCUENV_OLD_PATH="${PATH:-}"
for name in OPENOCD_SCRIPTS CMAKE_TOOLCHAIN_FILE; do
  backup="MCUENV_OLD_${name}"
  if [[ -n "${!name:-}" ]]; then
    export "${backup}=${!name}"
  else
    unset "${backup}" 2>/dev/null || true
  fi
done

eval "$("$PYTHON" "$MCUENV_ROOT/mcuenv.py" export --format bash)"

export MCUENV_OLD_PS1="${PS1:-}"
MCUENV_PROMPT_BASH="$("$PYTHON" "$MCUENV_ROOT/mcuenv.py" prompt-segment --format bash | tr -d '\r\n')"
export PS1="${MCUENV_PROMPT_BASH}${PS1}"

deactivate() {
  eval "$("$PYTHON" "$MCUENV_ROOT/mcuenv.py" deactivate --format bash)"
}

mcuenv.py() {
  if [[ "${1:-}" == "deactivate" ]]; then
    deactivate
    return 0
  fi

  "$PYTHON" "$MCUENV_ROOT/mcuenv.py" "$@"
}

export MCUENV_ACTIVE=1

echo "mcuenv activated: $MCUENV_ROOT"
echo "Run 'mcuenv.py doctor' to verify the environment."
echo "Run 'deactivate' when you want to leave this environment."
