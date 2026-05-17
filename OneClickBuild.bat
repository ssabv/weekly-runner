@echo off
chcp 65001 >nul 2>nul
title WeeklyRunner Build Tool

echo.
echo ============================================
echo   One-click Build WeeklyRunner.exe
echo ============================================
echo.

:: ---- Step 1: Check Python ----
echo [1/4] Checking Python ...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python is installed:
    python --version
    goto :install_deps
)

echo [!] Python not found. Trying py launcher...
py --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python is installed (via py):
    py --version
    set "PYTHON=py"
    goto :install_deps
)

echo [!] Python not found. Installing...
echo.

:: Download Python 3.12 (embeddable installer is too minimal, use full installer)
echo [2/4] Downloading Python 3.12 (~25MB)...
set "PY_URL=https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
set "INSTALLER=%TEMP%\python-installer.exe"

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%INSTALLER%'"

if not exist "%INSTALLER%" (
    echo [FAIL] Download failed. Please install Python manually:
    echo        https://www.python.org/downloads/
    echo        IMPORTANT: Check "Add Python to PATH" during install!
    pause
    exit /b 1
)

echo [OK] Download complete.
echo.
echo [3/4] Installing Python (silent)...
echo       If UAC prompt appears, click YES.
echo.

start /wait "" "%INSTALLER%" /passive InstallAllUsers=1 PrependPath=1 Include_test=0

:: Refresh PATH from registry
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%ProgramFiles%\Python312"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] Python install may need a system restart.
    echo        Please restart your PC and run this script again.
    pause
    exit /b 1
)

echo [OK] Python installed.
del "%INSTALLER%" >nul 2>&1

:: ---- Step 2: Install PyInstaller ----
:install_deps
echo.
echo [4/5] Installing PyInstaller...
pip install pyinstaller --quiet 2>nul
if %errorlevel% neq 0 (
    python -m pip install pyinstaller --quiet 2>nul
)
echo [OK] PyInstaller ready.

:: ---- Step 3: Build EXE ----
echo.
echo ============================================
echo [5/5] Building WeeklyRunner.exe ...
echo ============================================
echo.

cd /d "%~dp0"

pyinstaller --onefile --windowed --name WeeklyRunner --clean main.py

echo.
if exist "dist\WeeklyRunner.exe" (
    echo ============================================
    echo [OK] BUILD SUCCESS!
    echo ============================================
    echo.
    echo Output: %~dp0dist\WeeklyRunner.exe
    echo.
    echo How to use:
    echo   1. Double-click dist\WeeklyRunner.exe
    echo   2. Browse to select your AHK script
    echo   3. Set execution day and time
    echo   4. Click Start
    echo.
    set /p RUNNOW="Run now? (Y/N): "
    if /i "%RUNNOW%"=="Y" start "" "dist\WeeklyRunner.exe"
) else (
    echo [FAIL] Build failed. Please screenshot the error above.
)

echo.
pause
