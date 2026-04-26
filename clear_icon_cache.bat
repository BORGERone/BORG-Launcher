@echo off
echo Clearing Windows icon cache...
echo.

REM Kill explorer.exe
taskkill /f /im explorer.exe

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Delete icon cache files
del /f /q "%LOCALAPPDATA%\IconCache.db"
del /f /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\IconCache*.db"

REM Restart explorer.exe
start explorer.exe

echo.
echo Icon cache cleared successfully.
pause
