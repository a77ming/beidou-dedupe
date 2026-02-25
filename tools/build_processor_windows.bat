@echo off
setlocal enabledelayedexpansion

echo Building Windows processor...

set VENV_DIR=.build\processor-win64\venv
set WORK_DIR=.build\processor-win64\work
set SPEC_DIR=.build\processor-win64\spec
set DIST_DIR=build\bin

:: Create directories
if not exist "%VENV_DIR%" (
    python -m venv "%VENV_DIR%"
)

:: Install dependencies
call "%VENV_DIR%\Scripts\activate.bat"
pip install --upgrade pip setuptools wheel
pip install pyinstaller moviepy>=2.0.0 opencv-python>=4.8.0 Pillow>=10.0.0 numpy>=1.24.0 imageio-ffmpeg>=0.4.9

:: Build with PyInstaller
pyinstaller --onefile ^
    --name video_dedupe_processor ^
    --distpath "%DIST_DIR%" ^
    --workpath "%WORK_DIR%" ^
    --specpath "%SPEC_DIR%" ^
    --add-data "processor;processor" ^
    --add-data "config.json;." ^
    tools\process_video.py

echo Built: %DIST_DIR%\video_dedupe_processor.exe
