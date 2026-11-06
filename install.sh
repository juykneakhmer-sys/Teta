#!/usr/bin/env sh
# ─────────────────────────────────────────────────────────────
# Teta installer សម្រាប់ Termux
# ប្រើ:  sh install.sh
# ─────────────────────────────────────────────────────────────
set -eu

SRC=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# ជ្រើសរើសថតដំឡើង (TETA_PREFIX អាចបង្ខំបាន — ងាយសម្រាប់សាកល្បង)
PREFIX=${TETA_PREFIX:-${PREFIX:-}}
if [ -n "$PREFIX" ]; then
  BIN_DIR="$PREFIX/bin"          # Termux
  LIB_DIR="$PREFIX/share/teta"
else
  BIN_DIR="/usr/local/bin"       # Linux
  LIB_DIR="/usr/local/share/teta"
fi

echo "→ ដំឡើង Teta ទៅ $LIB_DIR"

if ! command -v python >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
  echo "✖ រកមិនឃើញ python។ ដំណើរការ: pkg install python" >&2
  exit 1
fi

mkdir -p "$LIB_DIR" "$BIN_DIR"

# ចម្លង package
rm -rf "$LIB_DIR/teta"
cp -R "$SRC/teta" "$LIB_DIR/teta"

# បង្កើត launcher (shebang តាមប្រព័ន្ធ)
case "$BIN_DIR" in
  *com.termux*) SHEBANG="#!/data/data/com.termux/files/usr/bin/sh" ;;
  *)            SHEBANG="#!/usr/bin/env sh" ;;
esac

cat > "$BIN_DIR/teta" <<EOF
$SHEBANG
set -eu
DIR="$LIB_DIR"
PYTHON=\${TETA_PYTHON:-python}
command -v "\$PYTHON" >/dev/null 2>&1 || PYTHON=python3
PYTHONPATH="\$DIR\${PYTHONPATH:+:\$PYTHONPATH}" exec "\$PYTHON" -m teta "\$@"
EOF
chmod 755 "$BIN_DIR/teta"

echo "✔ ដំឡើងរួចរាល់ — សាកល្បង: teta --version"
echo "  ជំហានបន្ទាប់: teta init"
echo "  ជម្រើស: pkg install termux-api  (សម្រាប់ \`teta copy\` → clipboard)"
