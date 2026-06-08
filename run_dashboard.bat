@echo off
cd /d "%~dp0"

REM Activate venv if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

streamlit run dashboard.py
pause
