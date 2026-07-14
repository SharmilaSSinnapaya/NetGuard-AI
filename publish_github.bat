@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo  NetGuard-AI — create GitHub repo and push
echo ============================================================
echo.
echo  Before continuing:
echo    1. Install Git: https://git-scm.com/download/win
echo    2. Install GitHub CLI: https://cli.github.com/
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo ERROR: git not found.
  pause
  exit /b 1
)

where gh >nul 2>&1
if errorlevel 1 (
  echo ERROR: gh not found. Install from https://cli.github.com/
  pause
  exit /b 1
)

echo Checking GitHub authentication...
gh auth status
if errorlevel 1 (
  echo.
  echo Logging in to GitHub...
  gh auth login
  if errorlevel 1 (
    echo ERROR: gh auth login failed.
    pause
    exit /b 1
  )
)

echo.
echo Staging all project files...
git add -A
git status --short
echo.

git diff --cached --quiet
if errorlevel 1 (
  echo Creating commit...
  git commit -m "Prepare public NetGuard-AI portfolio release"
  if errorlevel 1 (
    echo ERROR: commit failed. Set your git identity if prompted:
    echo   git config --global user.name "Your Name"
    echo   git config --global user.email "you@example.com"
    pause
    exit /b 1
  )
) else (
  echo No new changes to commit — continuing with push.
)

git branch -M main

echo.
REM Prefer one-shot create+push when remote is missing
git remote get-url origin >nul 2>&1
if errorlevel 1 (
  echo Creating public repo and pushing via GitHub CLI...
  gh repo create NetGuard-AI --public --source=. --remote=origin --push --description "AI-powered Intrusion Detection System with FastAPI + Streamlit"
  if errorlevel 1 (
    echo.
    echo Create/push failed. If the name is taken, rename on GitHub or run:
    echo   gh repo create NetGuard-AI-IDS --public --source=. --remote=origin --push
    pause
    exit /b 1
  )
) else (
  echo Remote origin already set. Pushing to origin main...
  git push -u origin main
  if errorlevel 1 (
    echo ERROR: push failed.
    pause
    exit /b 1
  )
)

echo.
echo Success. Opening repository...
gh repo view --web
echo.
pause
exit /b 0
