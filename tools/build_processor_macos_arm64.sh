#!/usr/bin/env bash
set -euo pipefail

# Build a self-contained macOS arm64 processor binary (PyInstaller onefile).
# This is used by the packaged Electron app so end-users don't need Python/pip.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OUT_BIN="$ROOT_DIR/build/bin/video_dedupe_processor"
BUILD_DIR="$ROOT_DIR/.build/processor-macos-arm64"
VENV_DIR="$BUILD_DIR/venv"
DIST_DIR="$BUILD_DIR/dist"
WORK_DIR="$BUILD_DIR/work"
SPEC_DIR="$BUILD_DIR/spec"
PYI_HOME="$BUILD_DIR/pyinstaller-home"

mkdir -p "$BUILD_DIR" "$ROOT_DIR/build/bin"

# Avoid using a global PyInstaller cache/config that may be owned by root.
export PYINSTALLER_CONFIG_DIR="$PYI_HOME"
export PYINSTALLER_CACHE_DIR="$PYI_HOME"

python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel >/dev/null

# Keep versions loosely pinned; wheels must exist for macOS arm64.
python -m pip install \
  "pyinstaller>=6.3,<7" \
  "moviepy>=2.0.0" \
  "imageio>=2.31.0" \
  "opencv-python>=4.8.0" \
  "Pillow>=10.0.0" \
  "numpy>=1.24.0" \
  "imageio-ffmpeg>=0.4.9" >/dev/null

rm -rf "$DIST_DIR" "$WORK_DIR" "$SPEC_DIR"

python -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name "video_dedupe_processor" \
  --distpath "$DIST_DIR" \
  --workpath "$WORK_DIR" \
  --specpath "$SPEC_DIR" \
  --paths "$ROOT_DIR/processor" \
  --copy-metadata "imageio" \
  --copy-metadata "moviepy" \
  --copy-metadata "imageio-ffmpeg" \
  --hidden-import "cv2" \
  --hidden-import "numpy" \
  --hidden-import "PIL" \
  --hidden-import "moviepy" \
  --hidden-import "imageio_ffmpeg" \
  "$ROOT_DIR/tools/process_video.py"

cp -f "$DIST_DIR/video_dedupe_processor" "$OUT_BIN"
chmod +x "$OUT_BIN"

echo "Built: $OUT_BIN"
