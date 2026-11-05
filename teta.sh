#!/usr/bin/env sh
# Teta launcher — ដំណើរការបានទាំង Termux និង Linux
# ប្រើ: ./teta <command>   ឬ  teta <command> (បន្ទាប់ពី ./install.sh)
set -eu

# រកថតដែលផ្ទុក package 'teta'
SELF=$(readlink -f "$0" 2>/dev/null || echo "$0")
DIR=$(CDPATH= cd -- "$(dirname -- "$SELF")" && pwd)

# បើ launcher ត្រូវបានដំឡើងក្នុង $PREFIX/bin សូមចង្អុលទៅកន្លែងដំឡើងពិត
if [ -n "${TETA_PREFIX:-}" ] && [ -d "$TETA_PREFIX/teta" ]; then
  DIR="$TETA_PREFIX"
fi

PYTHON=${TETA_PYTHON:-python}
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON=python3

PYTHONPATH="$DIR${PYTHONPATH:+:$PYTHONPATH}" exec "$PYTHON" -m teta "$@"
