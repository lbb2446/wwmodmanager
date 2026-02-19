@echo off
echo ================================
echo Mod Manager - Build Script
echo ================================

echo.
echo [1/3] Checking dependencies...
py -3 -m pip install pyinstaller flask requests waitress -q

echo.
echo [2/3] Cleaning and building...
py -3 -m PyInstaller mod_manager.spec --clean
if %ERRORLEVEL% neq 0 (
    echo Build failed
    pause
    exit /b 1
)

echo.
echo [3/3] Build complete!
echo.
echo ================================
echo Build successful!
echo ================================
echo.
echo Executable: dist\ModManager.exe
echo File info:
dir "dist\ModManager.exe" | findstr ModManager.exe
echo.
echo Usage:
echo 1. Copy the entire dist folder to any location
echo 2. Run ModManager.exe
echo 3. It will auto-open a browser window
echo.
echo Notes:
echo - Make sure Edge browser is installed
echo - mods and static folders will be created automatically
echo ================================
pause
