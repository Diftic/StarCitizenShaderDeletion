@echo off
title Enhanced Cache Cleaner for Gaming
echo Testing - Script started successfully
echo.
echo ========================================
echo  Enhanced Cache Cleaner for Gaming
echo  AMD and NVIDIA GPU + Star Citizen
echo ========================================
echo.
echo RECOMMENDATIONS BEFORE CLEANING:
echo.
echo 1. CLOSE ALL GAMES AND APPLICATIONS
echo    - Ensure no games or graphics applications are running
echo    - Close Steam, Epic Games, and other game launchers
echo    - Exit any streaming or recording software
echo.
echo 2. WHEN TO USE THIS TOOL:
echo    - After AMD or NVIDIA driver updates
echo    - After Star Citizen game patches/updates
echo    - When experiencing crashes, stuttering, or visual artifacts
echo    - When loading times have dramatically increased
echo    - When free disk space is low
echo.
echo 3. WHAT THIS TOOL CLEANS:
echo    - AMD shader caches (DxCache, VkCache, etc.)
echo    - NVIDIA shader caches (DXCache, GLCache)
echo    - Star Citizen shader and USER folders
echo    - Windows temporary files and DirectX cache
echo.
echo 4. EXPECTED BEHAVIOR AFTER CLEANING:
echo    - Temporary performance dips during first gameplay
echo    - Longer initial loading times as shaders rebuild
echo    - Star Citizen may need to recompile shaders
echo    - Settings may reset if USER folder is deleted
echo.
echo 5. BACKUP RECOMMENDATION:
echo    - Back up Star Citizen keybindings if customized
echo    - Located at: StarCitizen\LIVE\USER\Controls\Mappings
echo.
echo ========================================
echo.
echo Press any key to continue with cache cleaning...
pause >nul
cls
echo.
echo Starting cache cleanup process...
echo.

REM ===== NVIDIA GPU Cache Cleaning =====
echo [NVIDIA] Cleaning NVIDIA GPU shader caches...

if exist "c:\users\%USERNAME%\Appdata\Local\NVIDIA\DXCache\*.*" (
    echo Deleting Nvidia DX cache...
    del "c:\users\%USERNAME%\Appdata\Local\NVIDIA\DXCache\*.*" /q >nul 2>&1
    echo Nvidia DX cache deletion completed
) else (
    echo Nvidia DX cache directory not found or already empty
)

if exist "c:\users\%USERNAME%\Appdata\Local\NVIDIA\GLCache\*.*" (
    echo Deleting Nvidia GL cache...
    del "c:\users\%USERNAME%\Appdata\Local\NVIDIA\GLCache\*.*" /q >nul 2>&1
    echo Nvidia GL cache deletion completed
) else (
    echo Nvidia GL cache directory not found or already empty
)

echo.

REM ===== AMD GPU Cache Cleaning =====
echo [AMD] Cleaning AMD GPU shader caches...

if exist "c:\users\%USERNAME%\Appdata\Local\AMD\DxCache\" (
    echo Deleting AMD DX cache...
    del "c:\users\%USERNAME%\Appdata\Local\AMD\DxCache\*.*" /q >nul 2>&1
    echo AMD DX cache deletion completed
) else (
    echo AMD DX cache directory not found
)

if exist "c:\users\%USERNAME%\Appdata\Local\AMD\DXCache\" (
    echo Deleting AMD DXCache alternate...
    del "c:\users\%USERNAME%\Appdata\Local\AMD\DXCache\*.*" /q >nul 2>&1
    echo AMD DXCache deletion completed
) else (
    echo AMD DXCache directory not found
)

if exist "c:\users\%USERNAME%\Appdata\Local\AMD\Dx9Cache\" (
    echo Deleting AMD DX9 cache...
    del "c:\users\%USERNAME%\Appdata\Local\AMD\Dx9Cache\*.*" /q >nul 2>&1
    echo AMD DX9 cache deletion completed
) else (
    echo AMD DX9 cache directory not found
)

if exist "c:\users\%USERNAME%\Appdata\Local\AMD\VkCache\" (
    echo Deleting AMD Vulkan cache...
    del "c:\users\%USERNAME%\Appdata\Local\AMD\VkCache\*.*" /q >nul 2>&1
    echo AMD Vulkan cache deletion completed
) else (
    echo AMD Vulkan cache directory not found
)

echo.

REM ===== Star Citizen Cache Cleaning =====
echo [STAR CITIZEN] Cleaning Star Citizen caches...

if exist "c:\users\%USERNAME%\Appdata\Local\Star Citizen\" (
    echo Deleting Star Citizen Shader cache...
    del "c:\users\%USERNAME%\Appdata\Local\Star Citizen\*.*" /q >nul 2>&1
    echo Star Citizen Shader cache deletion completed
) else (
    echo Star Citizen Shader cache directory not found
)

REM ===== Star Citizen USER Folder (Contains Settings!) =====
echo.
echo WARNING: The next step will delete Star Citizen USER folder
echo This contains your keybindings and game settings!
echo If you do not want to lose your keybindings, cancel this step,
echo and make sure to export your keybindings from the game and
echo store it in a separate folder.
echo.
set /p choice="Delete Star Citizen USER folder? (y/N): "
if /i "%choice%"=="y" (
    if exist "C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\USER\" (
        echo Deleting Star Citizen USER folder...
        del "C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\USER\*.*" /q >nul 2>&1
        echo Star Citizen USER folder deletion completed
    ) else (
        echo Star Citizen USER folder not found
    )
) else (
    echo Skipping Star Citizen USER folder deletion
)

REM ===== RSI Launcher Cache =====
if exist "%appdata%\rsilauncher\" (
    echo Deleting RSI Launcher cache...
    del "%appdata%\rsilauncher\*.*" /q >nul 2>&1
    echo RSI Launcher cache deletion completed
) else (
    echo RSI Launcher cache directory not found
)

echo.

REM ===== Windows System Cache Cleaning =====
echo [WINDOWS] Cleaning Windows temporary files...

if exist "%temp%\*.*" (
    echo Deleting user temp files...
    del "%temp%\*.*" /q >nul 2>&1
    echo User temp files deletion completed
) else (
    echo User temp directory not found or empty
)
echo.
echo ========================================
echo  Cache cleanup completed successfully!
echo ========================================
echo.
pause
cls
echo.
echo.
echo IMPORTANT POST-CLEANUP INFORMATION:
echo.
echo EXPECTED PERFORMANCE CHANGES:
echo - Shader caches will rebuild automatically on next game launch
echo - First 5-10 minutes of gameplay may have reduced performance
echo - Loading times may be longer initially as shaders recompile
echo - Performance should return to normal or improve after rebuild
echo.
echo NEXT STEPS RECOMMENDED:
echo 1. Restart your computer for optimal results
echo 2. Launch games one at a time to rebuild shader caches
echo 3. Be patient during first gameplay sessions
echo 4. Monitor for improvements in crashes/stuttering
echo.
echo STAR CITIZEN SPECIFIC:
echo - If USER folder was deleted, reconfigure your settings
echo - Restore any backed-up keybindings if needed
echo - First launch may take significantly longer than usual
echo.
echo If problems persist after cache clearing:
echo - Update your GPU drivers (AMD/NVIDIA)
echo - Verify game file integrity through launchers
echo - Check for Windows updates
echo ========================================
echo.
echo.
set /p restart="Do you want to restart your computer now? (Y/N): "
if /i "%restart%"=="y" (
    echo.
    echo Restarting computer in 5 seconds...
    echo Press Ctrl+C to cancel if you changed your mind!
    timeout /t 5
    shutdown /r /t 0
) else (
    echo.
    echo Remember to restart your computer manually when convenient.
    echo.
    echo Press any key to exit...
    pause >nul
)