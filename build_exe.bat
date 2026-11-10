@echo off
chcp 65001 > nul
echo ====================================================
echo   Minipet Desktop Pet - Standalone Single EXE Build
echo ====================================================

set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo [INFO] Terminating any running Minipet process to prevent file locks...
taskkill /f /im Minipet.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo [INFO] Using Python: %PYTHON_EXE%
echo [INFO] Packaging Minipet into a single-file executable...

"%PYTHON_EXE%" -m PyInstaller ^
    --noconsole ^
    --onefile ^
    --name "Minipet" ^
    --clean ^
    --add-data "index.html;." ^
    --add-data "solo_play.js;." ^
    --add-data "alarm_3d.html;." ^
    --add-data "vendor;vendor" ^
    --add-data "assets;assets" ^
    main.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================================
    echo   [SUCCESS] Minipet.exe built successfully!
    echo   Location: dist\Minipet.exe
    echo ====================================================
) else (
    echo.
    echo [ERROR] Build failed with error code %ERRORLEVEL%.
)
pause

