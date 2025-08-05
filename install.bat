@echo off
setlocal

REM === Set variables ===
set "MINICONDA_INSTALLER=Miniconda3-latest-Windows-x86_64.exe"
set "MINICONDA_URL=https://repo.anaconda.com/miniconda/%MINICONDA_INSTALLER%"
set "MINICONDA_PATH=%USERPROFILE%\Miniconda3"

REM === Check if Miniconda is already installed ===
if exist "%MINICONDA_PATH%\conda.bat" (
    echo Miniconda already installed at %MINICONDA_PATH%
) else (
    echo Downloading Miniconda installer...
    curl -L -o %MINICONDA_INSTALLER% %MINICONDA_URL%
    
    echo Installing Miniconda silently...
    start /wait "" "%MINICONDA_INSTALLER%" /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%MINICONDA_PATH%

    echo Removing installer...
    del %MINICONDA_INSTALLER%
)

REM === Initialize conda ===
call "%MINICONDA_PATH%\conda.bat" init cmd.exe

REM === Reload shell to apply conda init ===
call "%USERPROFILE%\Documents\WindowsPowerShell\conda_hook.ps1" > nul 2>&1

REM === Extract environment name from environment.yml ===
for /f "tokens=2 delims=: " %%A in ('findstr /B "name:" environment.yml') do (
    set "ENV_NAME=%%A"
)

REM === Check if the environment already exists ===
call "%MINICONDA_PATH%\conda.bat" activate base
call conda env list | findstr /C:"%ENV_NAME%" > nul

if %errorlevel%==0 (
    echo Environment "%ENV_NAME%" already exists. Activating it...
) else (
    echo Creating environment from environment.yml...
    call conda env create -f environment.yml
)

REM === Activate the environment ===
call conda activate %ENV_NAME%

endlocal
pause
