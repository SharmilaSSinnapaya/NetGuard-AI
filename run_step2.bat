@echo off
setlocal EnableDelayedExpansion
REM NetGuard-AI Step 2: create venv, install, download NSL-KDD, preprocess, test
cd /d "%~dp0"

REM ---- Locate a real Python interpreter ----
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
  echo.
  echo ============================================================
  echo  Python was NOT found on this PC.
  echo ============================================================
  echo.
  echo  1. Install from: https://www.python.org/downloads/
  echo  2. On the FIRST installer screen, CHECK:
  echo       [x] Add python.exe to PATH
  echo  3. Also leave "py launcher" enabled.
  echo  4. Close ALL Command Prompt windows, open a NEW one.
  echo  5. Run this check:
  echo       py -3 --version
  echo  6. Then run run_step2.bat again.
  echo.
  echo  Extra Windows fix if needed:
  echo    Settings -^> Apps -^> Advanced app settings
  echo    -^> App execution aliases
  echo    Turn OFF: python.exe and python3.exe
  echo ============================================================
  echo.
  pause
  exit /b 1
)

echo Using Python: %PYTHON_EXE%
"%PYTHON_EXE%" --version
if errorlevel 1 goto :fail

echo [1/5] Creating virtual environment (.venv) ...
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
echo Step 2 finished successfully.
pause
exit /b 0

:fail
echo.
echo Step 2 failed. See errors above.
pause
exit /b 1
