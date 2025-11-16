#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv-pyinstaller"
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
if [[ -d "$VENV_PATH" ]]; then
  /bin/rm -rf "$VENV_PATH"
fi
"$PYTHON_BIN" -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

echo "==> Upgrading pip"
"$VENV_PATH/bin/pip" install --upgrade pip

echo "==> Installing dependencies"
"$VENV_PATH/bin/pip" install -r "$PROJECT_ROOT/requirements.txt"
"$VENV_PATH/bin/pip" install pyinstaller

APP_NAME="Bed Level Editor Pro"
BUNDLE_ID="com.bedlevel.editorpro"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"

if [[ -d "$DIST_DIR" ]]; then
  /bin/rm -rf "$DIST_DIR"
fi
if [[ -d "$BUILD_DIR" ]]; then
  /bin/rm -rf "$BUILD_DIR"
fi

PYINSTALLER_ARGS=(
  --noconfirm
  --clean
  --windowed
  --name "$APP_NAME"
  --osx-bundle-identifier "$BUNDLE_ID"
  --hidden-import tkinter
  --hidden-import tkinter._fix
  --hidden-import matplotlib.backends.backend_tkagg
  --hidden-import matplotlib.backends._tkagg
  --hidden-import mpl_toolkits.mplot3d
  --collect-submodules matplotlib
  --collect-data matplotlib
  --collect-submodules mpl_toolkits
  --collect-data mpl_toolkits
  --collect-data matplotlib
)

pushd "$PROJECT_ROOT" >/dev/null
"$VENV_PATH/bin/pyinstaller" "${PYINSTALLER_ARGS[@]}" bed_level_editor_pro.py
popd >/dev/null

APP_PATH="$DIST_DIR/$APP_NAME.app"
echo "PyInstaller build complete: $APP_PATH"
echo "Launch with: open '$APP_PATH'"
