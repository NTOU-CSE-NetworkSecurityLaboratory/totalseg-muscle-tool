@echo off
setlocal EnableExtensions
chcp 65001 > nul

cd /d "%~dp0python"

REM Check if uv is installed
where uv >nul 2>&1
if errorlevel 1 (
    echo [INFO] 正在安裝 uv，請稍候...
    powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if errorlevel 1 (
        echo [ERROR] uv 安裝失敗，請確認網路連線後重試。
        pause
        exit /b 1
    )
    if exist "%USERPROFILE%\.local\bin\uv.exe" set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
)

echo [INFO] 正在確認執行環境，請稍候...
uv sync
if errorlevel 1 (
    echo [ERROR] 環境初始化失敗，請確認網路連線後重試。
    pause
    exit /b 1
)

echo [INFO] 啟動中...
start "" powershell -WindowStyle Hidden -Command "uv run --no-sync python -m pywebview_tailwind_shell.app"
exit
