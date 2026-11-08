@echo off
cd /d "%~dp0"
REM Close any previously running Ppong-ppong-i instance so the upgraded 3D character loads cleanly
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^pythonw?\.exe$' -and $_.CommandLine -match '11\.Minipet.*main\.py|main\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
if not exist ".venv\Scripts\pythonw.exe" (
    echo [Ppong] .venv not found. Creating and installing requirements...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
start "" ".venv\Scripts\pythonw.exe" main.py
