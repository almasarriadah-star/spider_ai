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

REM -- Done --
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
