@echo off
cd /d "%~dp0"

echo ============================================
echo    Spider-AI - Setup Script
echo ============================================
echo.

REM -- 1) Check Python --
echo [1/5] Checking Python...
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

REM -- 2) Create virtual environment --
echo [2/5] Setting up virtual environment...
if not exist "venv" (
    echo Creating venv...
    python -m venv venv
    if errorlevel 1 (
        echo [!] Failed to create venv. Will install globally.
        set USE_VENV=0
    ) else (
        echo [OK] venv created
        set USE_VENV=1
    )
) else (
    echo [OK] venv already exists
    set USE_VENV=1
)
echo.

REM -- 3) Install dependencies --
echo [3/5] Installing packages from requirements.txt...
if "%USE_VENV%"=="1" (
    call venv\Scripts\activate.bat
    echo Installing in venv...
) else (
    echo Installing globally...
)
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [!] Error during install. Retrying...
    pip install -r requirements.txt
)
echo [OK] Packages installed
echo.

REM -- 4) Create required folders --
echo [4/5] Creating required folders...
if not exist "data" mkdir data
if not exist "data\frames" mkdir data\frames
if not exist "test_images" mkdir test_images
if not exist "models" mkdir models
echo [OK] Folders ready: data\, test_images\, models\
echo.

REM -- 5) Download test images --
echo [5/5] Downloading test images...
if exist "download_test_images.py" (
    echo Running download_test_images.py...
    python download_test_images.py
    if errorlevel 1 (
        echo [!] Failed. Run manually: python download_test_images.py
    ) else (
        echo [OK] Test images downloaded
    )
) else (
    echo [SKIP] download_test_images.py not found
)
echo.

REM -- 6) Verify installation --
echo [6/6] Verifying installation...
echo.

echo Checking streamlit...
python -c "import streamlit; print('  [OK] streamlit ' + streamlit.__version__)" 2>nul
if errorlevel 1 (
    echo  [X] streamlit NOT found! Installing...
    pip install streamlit --quiet
)

echo Checking opencv...
python -c "import cv2; print('  [OK] opencv ' + cv2.__version__)" 2>nul
if errorlevel 1 (
    echo  [X] opencv NOT found! Installing...
    pip install opencv-python --quiet
)

echo Checking numpy...
python -c "import numpy; print('  [OK] numpy ' + numpy.__version__)" 2>nul
if errorlevel 1 (
    echo  [X] numpy NOT found! Installing...
    pip install numpy --quiet
)

echo Checking pandas...
python -c "import pandas; print('  [OK] pandas ' + pandas.__version__)" 2>nul
if errorlevel 1 (
    echo  [X] pandas NOT found! Installing...
    pip install pandas --quiet
)

echo Checking folium...
python -c "import folium; print('  [OK] folium ' + folium.__version__)" 2>nul
if errorlevel 1 (
    echo  [X] folium NOT found! Installing...
    pip install folium --quiet
)

echo Checking requests...
python -c "import requests; print('  [OK] requests ' + requests.__version__)" 2>nul
if errorlevel 1 (
    echo  [X] requests NOT found! Installing...
    pip install requests --quiet
)

echo Checking yaml...
python -c "import yaml; print('  [OK] pyyaml OK')" 2>nul
if errorlevel 1 (
    echo  [X] pyyaml NOT found! Installing...
    pip install pyyaml --quiet
)

echo.
echo ============================================
echo    [OK] Setup complete!
echo ============================================
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
