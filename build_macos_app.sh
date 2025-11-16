#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv-macos-app"
APP_BUNDLE="$PROJECT_ROOT/dist/Bed Level Editor Pro.app"
RESOURCES_PATH="$APP_BUNDLE/Contents/Resources"
PYTHON_BIN="${PYTHON_BIN:-}"

if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.12)"
  else
    PYTHON_BIN="$(command -v python3)"
  fi
fi

echo "Using Python interpreter: $PYTHON_BIN"

echo "==> Creating virtual environment at $VENV_PATH"
"$PYTHON_BIN" -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

echo "==> Upgrading pip"
"$VENV_PATH/bin/pip" install --upgrade pip

echo "==> Installing dependencies"
"$VENV_PATH/bin/pip" install -r "$PROJECT_ROOT/requirements.txt"
"$VENV_PATH/bin/pip" install py2app

PYTHON_TAG=$("$VENV_PATH/bin/python" - <<'PY'
import sys
print(f"python{sys.version_info.major}.{sys.version_info.minor}")
PY
)
PYTHON_LIB_DIR="$RESOURCES_PATH/lib/${PYTHON_TAG}"
SITE_PACKAGES_DIR="$VENV_PATH/lib/${PYTHON_TAG}/site-packages"

echo "==> Building Bed Level Editor Pro macOS app"
pushd "$PROJECT_ROOT" >/dev/null
"$VENV_PATH/bin/python" macos_app/setup.py py2app
popd >/dev/null

echo "==> Copying namespace packages"
if [ -d "$SITE_PACKAGES_DIR/mpl_toolkits" ]; then
  mkdir -p "$PYTHON_LIB_DIR"
  rsync -a --delete "$SITE_PACKAGES_DIR/mpl_toolkits" "$PYTHON_LIB_DIR/"
fi

APP_PATH="$PROJECT_ROOT/dist/Bed Level Editor Pro.app"
echo "Build complete. App bundle located at:"
echo "  $APP_PATH"
echo ""
echo "Open the app by double-clicking it in Finder, or run:"
echo "  open \"$APP_PATH\""
