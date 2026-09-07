@echo off
cd /d "%~dp0"
echo.
echo  動いているサーバを止めます。
echo.
python autostart.py stop
echo.
pause
