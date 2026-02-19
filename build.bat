@echo off
setlocal enabledelayedexpansion
echo ================================
echo Mod Manager - Build Script
echo ================================

echo.
echo [1/4] Reading config and preparing build...

echo.
echo [2/4] Checking dependencies...
py -3 -m pip install pyinstaller flask requests waitress -q

echo.
echo [3/4] Building...
py -3 build.py
if %ERRORLEVEL% neq 0 (
    echo Build failed
    pause
    exit /b 1
)

echo.
echo ================================
echo Build complete!
echo ================================
pause
