@echo off
chcp 65001 >nul
echo ================================
echo Mod 管理器 - 自动打包脚本
echo ================================

echo.
echo [1/4] 检查依赖...
py -3 -m pip install pyinstaller flask requests waitress -q

echo.
echo [2/4] 切换到生产模式...
powershell -Command "(Get-Content app.py) -replace 'DEBUG = True', 'DEBUG = False' | Set-Content app.py"

echo.
echo [3/4] 清理并打包...
py -3 -m PyInstaller mod_manager.spec --clean
if %ERRORLEVEL% neq 0 (
    echo 打包失败
    pause
    exit /b 1
)

echo.
echo [4/4] 恢复开发模式...
powershell -Command "(Get-Content app.py) -replace 'DEBUG = False', 'DEBUG = True' | Set-Content app.py"

echo.
echo ================================
echo 打包完成！
echo ================================
echo.
echo 可执行文件: dist\ModManager.exe
echo 文件信息:
dir "dist\ModManager.exe" | findstr ModManager.exe
echo.
echo 使用说明:
echo 1. 将整个 dist 文件夹复制到任意位置
echo 2. 运行 ModManager.exe 即可
echo 3. 首次运行会自动打开独立窗口
echo.
echo 注意事项:
echo - 确保 Edge 浏览器已安装
echo - 会自动创建 mods 和 static 文件夹
echo ================================
pause
