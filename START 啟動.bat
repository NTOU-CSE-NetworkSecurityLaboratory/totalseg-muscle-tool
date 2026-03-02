@echo off
setlocal EnableExtensions
chcp 65001 > nul

cd /d "%~dp0python"

REM Check if uv is installed
where uv >nul 2>&1
if errorlevel 1 (
    echo [INFO] uv not installed, installing...
    powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if errorlevel 1 (
        echo [ERROR] Failed to install uv
        pause
        exit /b 1
    )

    REM 讓「同一次執行」就能找到 uv（預設安裝位置通常在 ~/.local/bin）[web:75]
    if exist "%USERPROFILE%\.local\bin\uv.exe" set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    REM 舊版本可能在 ~/.cargo/bin（保險起見也加）[page:0]
    if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
)

REM 建議把入口檔改成 gui_pyside.pyw，uv 會用 pythonw 跑（不綁 console）[page:2]
start "" powershell -WindowStyle Hidden -Command "uv run gui_pyside.py"
exit