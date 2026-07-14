@echo off
REM Launch Streamlit dashboard (API must already be running)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv — run setup.bat first.
  pause
  exit /b 1
)

echo Checking API at http://127.0.0.1:8000/health ...
set "API_OK=0"
".venv\Scripts\python.exe" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read(); print('API OK')"
if not errorlevel 1 set "API_OK=1"

if "%API_OK%"=="0" goto :no_api

echo Starting dashboard at http://localhost:8501
echo Keep this window open while using the dashboard.
echo.
".venv\Scripts\python.exe" -m streamlit run dashboard\app.py --server.headless true
exit /b %ERRORLEVEL%

:no_api
echo.
echo API is not reachable on http://127.0.0.1:8000
echo Start it first with start_api.bat in another Command Prompt window.
echo.
pause
exit /b 1
