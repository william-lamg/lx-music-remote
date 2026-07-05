@echo off
title LX Music 遙控器
cd /d "%~dp0"
echo ====================================================
echo   🎵 LX Music 一體化遙控器
echo ====================================================
echo.
echo 正在啟動...
echo.
python lx-remote-app.py
if %errorlevel% neq 0 (
    echo.
    echo 發生錯誤，請確認已安裝 Python。
    pause
)
