@echo off
cd /d "%~dp0"

rem SYSTEM で動く仕事を登録するには管理者の権限が要る。
rem 無ければ、自分自身を昇格して開き直す。
net session >nul 2>&1
if errorlevel 1 (
  echo.
  echo  管理者の権限が必要です。許可の画面が出たら「はい」を押してください。
  echo.
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

echo.
echo  パソコンの起動時に、カメラを自動で立ち上げるようにします。
echo.
python autostart.py install
echo.
pause
