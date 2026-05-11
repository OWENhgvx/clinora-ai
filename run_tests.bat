@echo off
REM Clinora — one-shot test runner (Windows CMD / PowerShell)
REM Usage (from clinora\): run_tests.bat

setlocal enabledelayedexpansion
set FAILED=0
set ROOT=%~dp0
set BACKEND=%ROOT%clinora-backend
set FRONTEND=%ROOT%clinora-frontend

echo.
echo ==========================================
echo    Clinora Test Suite
echo ==========================================

REM ── Backend ────────────────────────────────
echo.
echo -- Backend (pytest) ----------------------
cd /d "%BACKEND%"

if not exist "venv" (
    echo   Creating Python venv...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo   Installing dependencies...
pip install -r requirements.txt -q

echo.
echo   Running pytest...
python -m pytest tests/ -q --tb=short --no-header
if errorlevel 1 ( set FAILED=1 & echo   FAIL  pytest ) else ( echo   PASS  pytest )

echo.
echo   Coverage summary:
python -m pytest tests/ --cov=. --cov-report=term-missing -q --no-header 2>nul | findstr /R "TOTAL\|%"

call venv\Scripts\deactivate.bat 2>nul

REM ── Frontend ───────────────────────────────
echo.
echo -- Frontend (Vitest + ESLint) ------------
cd /d "%FRONTEND%"

echo   Installing dependencies...
npm install --silent

echo.
echo   Running ESLint...
npm run lint --silent
if errorlevel 1 ( set FAILED=1 & echo   FAIL  ESLint ) else ( echo   PASS  ESLint )

echo.
echo   Running Vitest unit tests...
npm run test:run
if errorlevel 1 ( set FAILED=1 & echo   FAIL  Vitest ) else ( echo   PASS  Vitest )

REM ── Summary ────────────────────────────────
echo.
echo ==========================================
if !FAILED!==0 (
    echo   All test suites passed.
) else (
    echo   One or more test suites FAILED.
)
echo ==========================================
echo.

endlocal
exit /b %FAILED%
