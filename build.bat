@echo off
setlocal enabledelayedexpansion
echo ================================
echo Mod Manager - Build Script
echo ================================

echo.
echo [1/5] Reading config...
for /f "tokens=1,* delims=:" %%a in ('findstr "app_name" config.json') do (
    set "line=%%b"
    for /f "tokens=1" %%i in ("!line!") do set "APP_NAME=%%i"
)
for /f "tokens=1,* delims=:" %%a in ('findstr "icon_path" config.json') do (
    set "line=%%b"
    for /f "tokens=1" %%i in ("!line!") do set "ICON_PATH=%%i"
)
set "APP_NAME=!APP_NAME: =!"
set "APP_NAME=!APP_NAME:"=!"
set "ICON_PATH=!ICON_PATH: =!"
set "ICON_PATH=!ICON_PATH:"=!"

echo App Name: !APP_NAME!
echo Icon: !ICON_PATH!

echo.
echo [2/5] Checking dependencies...
py -3 -m pip install pyinstaller flask requests waitress -q

echo.
echo [3/5] Updating spec file...
powershell -Command "(Get-Content mod_manager.spec) -replace 'name=.*ModManager.*', 'name=''!APP_NAME!''' | Set-Content mod_manager.spec"

echo.
echo [4/5] Adding icon to spec...
powershell -Command "$content = Get-Content mod_manager.spec -Raw; $content = $content -replace 'name=''!APP_NAME!''', 'name=''!APP_NAME!''', 'icon=''!ICON_PATH!'''; Set-Content -Path mod_manager.spec -Value $content -NoNewline"

echo.
echo [5/5] Building...
py -3 -m PyInstaller mod_manager.spec --clean
if %ERRORLEVEL% neq 0 (
    echo Build failed
    pause
    exit /b 1
)

echo.
echo ================================
echo Build complete!
echo ================================
echo.
echo Executable: dist\!APP_NAME!.exe
echo File info:
dir "dist\!APP_NAME!.exe" | findstr !APP_NAME!
echo.
echo Usage:
echo 1. Copy the entire dist folder to any location
echo 2. Run !APP_NAME!.exe
echo 3. It will auto-open a browser window
echo.
echo Notes:
echo - Make sure Edge browser is installed
echo - mods and static folders will be created automatically
echo ================================
pause
