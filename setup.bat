@echo off
setlocal EnableDelayedExpansion
REM Create venv, install deps, download NSL-KDD, preprocess, run tests
cd /d "%~dp0"

set "PYTHON_EXE="

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%I"
)

if not defined PYTHON_EXE (
  where python >nul 2>&1
  if !ERRORLEVEL!==0 (
    for /f "delims=" %%I in ('where python') do (
      echo %%I | findstr /i "WindowsApps" >nul
      if errorlevel 1 (
        set "PYTHON_EXE=%%I"
        goto :found_python
      )
    )
  )
)

:found_python
if not defined PYTHON_EXE (
  for %%V in (314 313 312 311 310) do (
    if exist "%LocalAppData%\Programs\Python\Python%%V\python.exe" (
      set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python%%V\python.exe"
      goto :have_python
    )
    if exist "%ProgramFiles%\Python%%V\python.exe" (
      set "PYTHON_EXE=%ProgramFiles%\Python%%V\python.exe"
      goto :have_python
    )
    if exist "C:\Python%%V\python.exe" (
      set "PYTHON_EXE=C:\Python%%V\python.exe"
      goto :have_python
    )
  )
)

:have_python
if not defined PYTHON_EXE (
  echo Python was not found. Install from https://www.python.org/downloads/
  echo Enable "Add python.exe to PATH", then open a new Command Prompt.
  pause
  exit /b 1
)

echo Using Python: %PYTHON_EXE%
"%PYTHON_EXE%" --version
if errorlevel 1 goto :fail

echo [1/5] Creating virtual environment ...
"%PYTHON_EXE%" -m venv .venv
if errorlevel 1 goto :fail

echo [2/5] Installing dependencies ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto :fail

echo [3/5] Downloading NSL-KDD ...
".venv\Scripts\python.exe" scripts\download_data.py
if errorlevel 1 goto :fail

echo [4/5] Preprocessing ...
".venv\Scripts\python.exe" scripts\preprocess.py
if errorlevel 1 goto :fail

echo [5/5] Running tests ...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto :fail

echo.
echo Setup complete. Next: train_models.bat
pause
exit /b 0

:fail
echo.
echo Setup failed. See errors above.
pause
exit /b 1
