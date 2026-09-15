@echo off
setlocal

rem Resolve the project directory from this launcher, so it works from any folder.
set "PROJECT_DIR=%~dp0..\.."
cd /d "%PROJECT_DIR%"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON=py"
    ) else (
        set "PYTHON=python"
    )
)

echo Starting DictFlow...
"%PYTHON%" wsgi.py

if errorlevel 1 (
    echo.
    echo DictFlow could not be started. Check that Python and the project dependencies are installed.
    pause
)
endlocal
