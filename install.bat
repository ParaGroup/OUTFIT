@echo off
setlocal enabledelayedexpansion

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
    curl -L -o "%MINICONDA_INSTALLER%" "%MINICONDA_URL%"

    echo Installing Miniconda silently...
    start /wait "" "%MINICONDA_INSTALLER%" /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D="%MINICONDA_PATH%"

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

REM === Launch a new shell with the environment activated ===
start cmd.exe /k "%MINICONDA_PATH%\Scripts\activate.bat %ENV_NAME%"
exit /b
