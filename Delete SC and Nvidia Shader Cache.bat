@echo off
echo Cleaning cache directories...

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

if exist "c:\users\%USERNAME%\Appdata\Local\Star Citizen\*.*" (
    echo Deleting Star Citizen Shader cache...
    del "c:\users\%USERNAME%\Appdata\Local\Star Citizen\*.*" /q >nul 2>&1
    echo Star Citizen Shader cache deletion completed
) else (
    echo Star Citizen Shader cache directory not found or already empty
)

echo Cache cleanup completed!
pause