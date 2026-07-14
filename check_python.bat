@echo off
REM Quick check: is Python installed and callable?
echo === Python discovery ===
echo.

echo [py launcher]
where py 2>nul
py -3 --version 2>nul
if errorlevel 1 echo   py launcher NOT available
echo.

echo [python on PATH]
where python 2>nul
python --version 2>nul
if errorlevel 1 echo   python NOT on PATH
echo.

echo [common install folders]
dir /b "%LocalAppData%\Programs\Python" 2>nul
if errorlevel 1 echo   No folder: %%LocalAppData%%\Programs\Python
echo.

echo If nothing above shows a version like "Python 3.12.x",
echo install from https://www.python.org/downloads/
echo and CHECK "Add python.exe to PATH", then reopen CMD.
echo.
pause
