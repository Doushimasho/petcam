@echo off
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo  Python が見つかりませんでした。
  echo.
  echo  https://www.python.org/downloads/ からインストールしてください。
  echo  インストール画面の最初にある
  echo  「Add python.exe to PATH」に必ずチェックを入れてください。
  echo.
  echo  インストールしたら、このファイルをもう一度ダブルクリックしてください。
  echo.
  pause
  exit /b 1
)

python -c "import flask, simple_websocket, cryptography" >nul 2>&1
if errorlevel 1 (
  echo.
  echo  必要な部品を用意しています。初回だけ1分ほどかかります...
  echo.
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo  部品の用意に失敗しました。上のメッセージを確認してください。
    echo.
    pause
    exit /b 1
  )
  echo.
)

python server.py
if errorlevel 1 (
  echo.
  echo  起動に失敗しました。上のメッセージを確認してください。
  echo.
  pause
)
