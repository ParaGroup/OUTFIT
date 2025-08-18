@echo off
setlocal

REM Author: Alberto Ottimo
REM Project: OUTFIT
REM Date: 2025-08-06

REM === CONFIGURATION ===
set "SCRIPT_NAME=src\outfit.py"
set "EXENAME=OUTFIT"
set "ICON=icons\outfit_rounded.ico"

REM === Set project-local Miniconda installation path ===
set "PROJECT_DIR=%~dp0"
set "MINICONDA_PATH=%PROJECT_DIR%Miniconda3"
set "CONDA_BAT=%MINICONDA_PATH%\condabin\conda.bat"

REM === Set Miniconda installer details ===
set "MINICONDA_INSTALLER=Miniconda3-latest-Windows-x86_64.exe"
set "MINICONDA_URL=https://repo.anaconda.com/miniconda/%MINICONDA_INSTALLER%"

REM === Check if Miniconda is already installed ===
if exist "%CONDA_BAT%" (
    echo Miniconda already installed at %MINICONDA_PATH%
) else (
    echo Downloading Miniconda installer...
    curl -# -L -o "%MINICONDA_INSTALLER%" "%MINICONDA_URL%"

    echo Installing Miniconda silently into %MINICONDA_PATH%...
    start /wait "" Miniconda3-latest-Windows-x86_64.exe /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%MINICONDA_PATH%

    echo Removing installer...
    del "%MINICONDA_INSTALLER%"
)

REM === Auto-accept licenses ===
set "CONDA_ACCEPT_LICENSES=yes"

REM === Extract environment name from environment.yml ===
set "ENV_NAME="
for /f "tokens=2 delims=: " %%A in ('findstr /B "name:" environment.yml') do (
    set "ENV_NAME=%%A"
)

if "%ENV_NAME%"=="" (
    echo Failed to extract environment name from environment.yml
    exit /b 1
)

REM === Activate base and check if environment exists ===
call "%CONDA_BAT%" activate base

REM Check if the environment exists
call "%CONDA_BAT%" env list | findstr /C:"%ENV_NAME%" > nul
if %errorlevel%==0 (
    echo Environment "%ENV_NAME%" already exists.
) else (
    echo Creating environment "%ENV_NAME%" from environment.yml...
    call "%CONDA_BAT%" env create -f environment.yml
)

REM === Activate ENV_NAME env  ===
call "%CONDA_BAT%" activate "%ENV_NAME%"

REM === Build executable with pyinstaller ===
pyinstaller --onefile --name %EXENAME% --icon=%ICON% --noconsole %SCRIPT_NAME%
if errorlevel 1 (
    echo [ERROR] PyInstaller failed to build executable.
    exit /b 1
)

REM === Move the .exe to the current directory ===
move /Y "dist\%EXENAME%.exe" . >nul

REM === Clean up unnecessary build files ===
echo [*] Cleaning up intermediate files...
del /Q /F "%EXENAME%.spec" 2>nul
rmdir /S /Q build 2>nul
rmdir /S /Q dist 2>nul
rmdir /S /Q __pycache__ 2>nul

endlocal
pause
