@echo off
setlocal
REM NetGuard-AI Step 5: launch Streamlit dashboard (API must already be running)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [.venv missing] Run run_step2.bat first.
  pause
  exit /b 1
)

echo Checking API at http://127.0.0.1:8000/health ...
set "API_OK=0"
".venv\Scripts\python.exe" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read(); print('API OK')"
if not errorlevel 1 set "API_OK=1"

if "%API_OK%"=="0" goto :no_api

echo Starting Streamlit dashboard ...
echo Open the URL Streamlit prints - usually http://localhost:8501
echo Keep this window open while using the dashboard.
echo.
".venv\Scripts\python.exe" -m streamlit run dashboard\app.py --server.headless true
exit /b %ERRORLEVEL%

:no_api
echo.
echo ============================================================
echo  API is not reachable on http://127.0.0.1:8000
echo ============================================================
echo.
echo  Use TWO Command Prompt windows:
echo.
echo    Window 1:  start_api.bat
echo               Wait for: Uvicorn running on http://127.0.0.1:8000
echo.
echo    Window 2:  run_step5.bat
echo.
echo  If you closed the API window, start it again with start_api.bat
echo ============================================================
echo.
pause
exit /b 1
