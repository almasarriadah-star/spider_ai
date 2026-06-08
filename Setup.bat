@echo off
cd /d "%~dp0"

echo ============================================
echo    Spider-AI - Setup Script
echo ============================================
echo.

REM -- 1) Check Python --
echo [1/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python not found! Install Python 3.8+ from:
    echo    https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [OK] %PYVER%
echo.

REM -- 2) Upgrade pip FIRST (critical for old pip) --
echo [2/6] Upgrading pip...
python -m pip install --upgrade pip
echo.

REM -- 3) Create/recreate virtual environment --
echo [3/6] Setting up virtual environment...
if exist "venv" (
    echo [!] Old venv found. Deleting to avoid conflicts...
    rmdir /s /q venv
)
echo Creating fresh venv...
python -m venv venv
if errorlevel 1 (
    echo [!] Failed to create venv. Will install globally.
    set USE_VENV=0
) else (
    echo [OK] venv created
    set USE_VENV=1
)
echo.

REM -- 4) Install dependencies --
echo [4/6] Installing packages...
if "%USE_VENV%"=="1" (
    call venv\Scripts\activate.bat
    echo Installing in venv...
) else (
    echo Installing globally...
)

REM Upgrade pip inside venv too
python -m pip install --upgrade pip

REM Install packages ONE BY ONE to handle errors
echo.
echo Installing requests...
pip install requests

echo Installing numpy...
pip install numpy

echo Installing opencv-python...
pip install opencv-python

echo Installing pyyaml...
pip install pyyaml

echo Installing pandas...
pip install pandas

echo Installing streamlit...
pip install streamlit

echo Installing folium...
pip install folium

echo Installing streamlit-folium...
pip install streamlit-folium

echo Installing reportlab...
pip install reportlab

echo Installing arabic-reshaper...
pip install arabic-reshaper

REM python-bidi has broken dep (puccinialin) on old systems - use specific version
echo Installing python-bidi (compatible version)...
pip install python-bidi==0.4.2
if errorlevel 1 (
    echo [!] python-bidi failed. Trying without puccinialin...
    pip install python-bidi --no-deps
)

echo Installing matplotlib...
pip install matplotlib

echo.
echo [OK] Core packages installed
echo.

REM -- 5) Create required folders --
echo [5/6] Creating required folders...
if not exist "data" mkdir data
if not exist "data\frames" mkdir data\frames
if not exist "test_images" mkdir test_images
if not exist "models" mkdir models
echo [OK] Folders ready
echo.

REM -- 6) Verify installation --
echo [6/6] Verifying installation...
echo.

set ALL_OK=1

echo Checking streamlit...
python -c "import streamlit; print('  [OK] streamlit ' + streamlit.__version__)" 2>nul
if errorlevel 1 (
    echo  [X] streamlit FAILED
    set ALL_OK=0
)

echo Checking opencv...
python -c "import cv2; print('  [OK] opencv ' + cv2.__version__)" 2>nul
if errorlevel 1 (
    echo  [X] opencv FAILED
    set ALL_OK=0
)

echo Checking numpy...
python -c "import numpy; print('  [OK] numpy ' + numpy.__version__)" 2>nul
if errorlevel 1 (
    echo  [X] numpy FAILED
    set ALL_OK=0
)

echo Checking pandas...
python -c "import pandas; print('  [OK] pandas ' + pandas.__version__)" 2>nul
if errorlevel 1 (
    echo  [X] pandas FAILED
    set ALL_OK=0
)

echo Checking folium...
python -c "import folium; print('  [OK] folium ' + folium.__version__)" 2>nul
if errorlevel 1 (
    echo  [X] folium FAILED
    set ALL_OK=0
)

echo Checking requests...
python -c "import requests; print('  [OK] requests ' + requests.__version__)" 2>nul
if errorlevel 1 (
    echo  [X] requests FAILED
    set ALL_OK=0
)

echo Checking yaml...
python -c "import yaml; print('  [OK] pyyaml OK')" 2>nul
if errorlevel 1 (
    echo  [X] pyyaml FAILED
    set ALL_OK=0
)

echo Checking reportlab...
python -c "import reportlab; print('  [OK] reportlab OK')" 2>nul
if errorlevel 1 (
    echo  [X] reportlab FAILED
    set ALL_OK=0
)

echo.
if "%ALL_OK%"=="1" (
    echo ============================================
    echo    [OK] Setup complete! All packages working.
    echo ============================================
) else (
    echo ============================================
    echo    [!] Setup finished with some errors.
    echo    Check the log above for details.
    echo ============================================
)
echo.
echo Next steps:
echo   1. Edit robot IP in config.yaml
echo   2. Run dashboard: run_dashboard.bat
echo      or: streamlit run dashboard.py
echo.
echo To activate venv manually:
echo   venv\Scripts\activate.bat
echo.
pause
