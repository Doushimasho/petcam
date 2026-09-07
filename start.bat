@echo off
cd /d "%~dp0"
python server.py
if errorlevel 1 (
  echo.
  echo 起動に失敗しました。上のメッセージを確認してください。
  pause
)
