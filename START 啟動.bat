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

REM 改為啟動 WebView 正式入口
start "" powershell -WindowStyle Hidden -Command "uv run python -m pywebview_tailwind_shell.app"
exit
