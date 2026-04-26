@echo off
echo Building BORG Launcher Portable Release...
echo.

REM Build Tauri app
cd tauri-launcher
call npm run tauri build
cd ..

REM Create release directory
if exist "BORGLauncher_Release" rmdir /s /q "BORGLauncher_Release"
mkdir "BORGLauncher_Release"

REM Copy exe file (icon is embedded)
echo Copying portable version...
xcopy "tauri-launcher\src-tauri\target\release\borg-minecraft-launcher.exe" "BORGLauncher_Release\BORGLauncher.exe" /Y

REM Copy dop folder (contains mrpack, servers.dat, fancymenu)
echo Copying dop folder...
xcopy "dop" "BORGLauncher_Release\dop" /E /I /Y

echo.
echo Portable release built successfully in BORGLauncher_Release folder
echo.
echo Contents:
echo - BORGLauncher_Release\BORGLauncher.exe (single file with embedded Python)
echo.
echo Python launcher files are embedded in the exe and extracted to AppData on first run.
echo.
echo For GitHub release: zip the BORGLauncher_Release folder
echo.
pause
