@echo off
cd /d "%~dp0"
echo.
echo  パソコンの起動時に、カメラを自動で立ち上げるようにします。
echo.
python autostart.py install
echo.
pause
