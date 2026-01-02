@echo off
setlocal EnableDelayedExpansion

:: Shader Cache Nuking Script
:: Clears shader caches for Star Citizen, NVIDIA, and AMD
:: Run as Administrator for best results

echo ============================================
echo        SHADER CACHE NUKING SCRIPT
echo ============================================
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Not running as Administrator.
    echo           Some caches may not be fully cleared.
    echo.
)

:: Initialize counters
set "cleared=0"
set "failed=0"
set "skipped=0"

:: ==========================================
:: STAR CITIZEN SHADERS
:: ==========================================
echo [STAR CITIZEN]
echo --------------

set "SC_SHADER_PATH=%LOCALAPPDATA%\Star Citizen"

if exist "%SC_SHADER_PATH%" (
    echo   Found: %SC_SHADER_PATH%
    
    :: Clear shaders folder
    if exist "%SC_SHADER_PATH%\shaders" (
        echo   Clearing shaders folder...
        rd /s /q "%SC_SHADER_PATH%\shaders" 2>nul
        if !errorlevel! equ 0 (
            echo   [OK] shaders cleared
            set /a cleared+=1
        ) else (
            echo   [FAIL] Could not clear shaders
            set /a failed+=1
        )
    ) else (
        echo   [SKIP] shaders folder not found
        set /a skipped+=1
    )
    
    :: Clear sc_shader_cache (alternative location in some versions)
    for /d %%D in ("%SC_SHADER_PATH%\*") do (
        if exist "%%D\shaders" (
            echo   Clearing %%~nxD\shaders...
            rd /s /q "%%D\shaders" 2>nul
            if !errorlevel! equ 0 (
                echo   [OK] %%~nxD\shaders cleared
                set /a cleared+=1
            )
        )
    )
) else (
    echo   [SKIP] Star Citizen folder not found
    set /a skipped+=1
)

echo.

:: ==========================================
:: NVIDIA SHADERS
:: ==========================================
echo [NVIDIA]
echo --------

:: NVIDIA DX Cache
set "NV_DXCACHE=%LOCALAPPDATA%\NVIDIA\DXCache"
if exist "%NV_DXCACHE%" (
    echo   Clearing DXCache...
    rd /s /q "%NV_DXCACHE%" 2>nul
    mkdir "%NV_DXCACHE%" 2>nul
    echo   [OK] DXCache cleared
    set /a cleared+=1
) else (
    echo   [SKIP] DXCache not found
    set /a skipped+=1
)

:: NVIDIA GL Cache
set "NV_GLCACHE=%LOCALAPPDATA%\NVIDIA\GLCache"
if exist "%NV_GLCACHE%" (
    echo   Clearing GLCache...
    rd /s /q "%NV_GLCACHE%" 2>nul
    mkdir "%NV_GLCACHE%" 2>nul
    echo   [OK] GLCache cleared
    set /a cleared+=1
) else (
    echo   [SKIP] GLCache not found
    set /a skipped+=1
)

:: NVIDIA Compute Cache
set "NV_COMPUTE=%APPDATA%\NVIDIA\ComputeCache"
if exist "%NV_COMPUTE%" (
    echo   Clearing ComputeCache...
    rd /s /q "%NV_COMPUTE%" 2>nul
    mkdir "%NV_COMPUTE%" 2>nul
    echo   [OK] ComputeCache cleared
    set /a cleared+=1
) else (
    echo   [SKIP] ComputeCache not found
    set /a skipped+=1
)

:: NVIDIA Temp Cache
set "NV_TEMP=%TEMP%\NVIDIA Corporation\NV_Cache"
if exist "%NV_TEMP%" (
    echo   Clearing NV_Cache (temp)...
    rd /s /q "%NV_TEMP%" 2>nul
    echo   [OK] NV_Cache cleared
    set /a cleared+=1
) else (
    echo   [SKIP] NV_Cache not found
    set /a skipped+=1
)

echo.

:: ==========================================
:: AMD SHADERS
:: ==========================================
echo [AMD]
echo -----

:: AMD DX Cache
set "AMD_DXCACHE=%LOCALAPPDATA%\AMD\DxCache"
if exist "%AMD_DXCACHE%" (
    echo   Clearing DxCache...
    rd /s /q "%AMD_DXCACHE%" 2>nul
    mkdir "%AMD_DXCACHE%" 2>nul
    echo   [OK] DxCache cleared
    set /a cleared+=1
) else (
    echo   [SKIP] DxCache not found
    set /a skipped+=1
)

:: AMD GL Cache
set "AMD_GLCACHE=%LOCALAPPDATA%\AMD\GLCache"
if exist "%AMD_GLCACHE%" (
    echo   Clearing GLCache...
    rd /s /q "%AMD_GLCACHE%" 2>nul
    mkdir "%AMD_GLCACHE%" 2>nul
    echo   [OK] GLCache cleared
    set /a cleared+=1
) else (
    echo   [SKIP] GLCache not found
    set /a skipped+=1
)

:: AMD Vulkan Cache
set "AMD_VKCACHE=%LOCALAPPDATA%\AMD\VkCache"
if exist "%AMD_VKCACHE%" (
    echo   Clearing VkCache...
    rd /s /q "%AMD_VKCACHE%" 2>nul
    mkdir "%AMD_VKCACHE%" 2>nul
    echo   [OK] VkCache cleared
    set /a cleared+=1
) else (
    echo   [SKIP] VkCache not found
    set /a skipped+=1
)

:: AMD Shader Cache (alternative location)
set "AMD_SHADER=%LOCALAPPDATA%\AMD\Dx9Cache"
if exist "%AMD_SHADER%" (
    echo   Clearing Dx9Cache...
    rd /s /q "%AMD_SHADER%" 2>nul
    mkdir "%AMD_SHADER%" 2>nul
    echo   [OK] Dx9Cache cleared
    set /a cleared+=1
) else (
    echo   [SKIP] Dx9Cache not found
    set /a skipped+=1
)

echo.

:: ==========================================
:: DIRECTX SHADER CACHE (SYSTEM)
:: ==========================================
echo [DIRECTX SYSTEM CACHE]
echo ----------------------

set "DX_CACHE=%LOCALAPPDATA%\D3DSCache"
if exist "%DX_CACHE%" (
    echo   Clearing D3DSCache...
    rd /s /q "%DX_CACHE%" 2>nul
    mkdir "%DX_CACHE%" 2>nul
    echo   [OK] D3DSCache cleared
    set /a cleared+=1
) else (
    echo   [SKIP] D3DSCache not found
    set /a skipped+=1
)

echo.

:: ==========================================
:: SUMMARY
:: ==========================================
echo ============================================
echo                  SUMMARY
echo ============================================
echo   Cleared: %cleared%
echo   Skipped: %skipped%
echo   Failed:  %failed%
echo ============================================
echo.
echo NOTE: First game launch after clearing will
echo       have longer load times and potential
echo       stutter as shaders recompile.
echo.

pause
