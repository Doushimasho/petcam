@echo off
cd /d "%~dp0"

rem 設定を変えるには管理者の権限が要る。無ければ自分を昇格して開き直す。
net session >nul 2>&1
if errorlevel 1 (
  echo.
  echo  管理者の権限が必要です。許可の画面が出たら「はい」を押してください。
  echo.
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

echo.
echo  高速スタートアップを無効にします。
echo.
echo  この設定が有効だと、Windowsの「シャットダウン」が完全な終了に
echo  ならないため、電源を入れ直しても自動起動が走らないことがあります。
echo.

reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power" /v HiberbootEnabled /t REG_DWORD /d 0 /f >nul 2>&1
if errorlevel 1 (
  echo  [失敗] 設定を変更できませんでした。
  echo.
  pause
  exit /b 1
)

echo  [完了] 高速スタートアップを無効にしました。
echo.
echo  次にシャットダウンするときから効きます。
echo  スマートプラグで試す前に、一度シャットダウンしてください。
echo.
echo  ----------------------------------------------------------
python precheck.py
echo.
pause
