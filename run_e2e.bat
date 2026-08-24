@echo off
chcp 65001 >nul
title Portal E2E (Playwright)

REM ==========================================================================
REM  Portal E2E runner -- standalone.
REM
REM  Split out of git_push_auto.bat on 2026-08-25: pushing code and running
REM  the browser tests are two different decisions, and the gate made every
REM  frontend commit wait a couple of minutes.
REM
REM  Usage:
REM    run_e2e.bat                    run every spec in frontend/e2e
REM    run_e2e.bat luqun-repair       run one spec file (.spec.ts optional)
REM    run_e2e.bat "Dashboard"        no such file -> used as --grep instead
REM    run_e2e.bat --ui               Playwright UI mode (debug)
REM    run_e2e.bat --headed           run with a visible browser
REM    run_e2e.bat --report           just open the last HTML report
REM
REM  Prerequisites:
REM    * backend running on 127.0.0.1:8000   (checked below, NOT auto-started
REM      -- venv path / NSSM service differ per machine)
REM    * frontend/e2e/.env with E2E_USER / E2E_PASS
REM    * the frontend dev server is started automatically by
REM      playwright.config.ts -> webServer (reuseExistingServer)
REM ==========================================================================

setlocal enabledelayedexpansion

cd /d C:\OneDrive\_Ragic\portal

set "MODE=run"
set "TARGET="
set "SPEC="
set "GREP="
set "PWARGS="

REM -- parse arguments ------------------------------------------------------
:parse
if "%~1"=="" goto :parsed
if /i "%~1"=="--ui"      ( set "MODE=ui"     & shift & goto :parse )
if /i "%~1"=="-u"        ( set "MODE=ui"     & shift & goto :parse )
if /i "%~1"=="--report"  ( set "MODE=report" & shift & goto :parse )
if /i "%~1"=="-r"        ( set "MODE=report" & shift & goto :parse )
if /i "%~1"=="--headed"  ( set "PWARGS=!PWARGS! --headed" & shift & goto :parse )
if /i "%~1"=="--help"    goto :usage
if /i "%~1"=="-h"        goto :usage
if /i "%~1"=="/?"        goto :usage
set "TARGET=%~1"
shift
goto :parse

:parsed

REM -- report only ----------------------------------------------------------
if "!MODE!"=="report" (
    echo Opening the last HTML report...
    pushd frontend
    call npx playwright show-report
    popd
    exit /b 0
)

REM -- a non-flag argument is a spec file if one exists, otherwise a grep ----
if defined TARGET (
    if exist "frontend\e2e\!TARGET!" (
        set "SPEC=e2e/!TARGET!"
    ) else (
        if exist "frontend\e2e\!TARGET!.spec.ts" (
            set "SPEC=e2e/!TARGET!.spec.ts"
        ) else (
            set "GREP=!TARGET!"
        )
    )
)

echo.
echo ==========================================
echo  Portal E2E
echo ==========================================
if defined SPEC echo  Spec  : !SPEC!
if defined GREP echo  Grep  : !GREP!
if not defined SPEC if not defined GREP echo  Scope : all specs
if "!MODE!"=="ui" echo  Mode  : Playwright UI
echo.

REM -- backend health check -------------------------------------------------
echo Checking backend on 127.0.0.1:8000 ...
powershell -NoProfile -Command "try { $null = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/version' -TimeoutSec 5 -UseBasicParsing; exit 0 } catch { exit 1 }"
if errorlevel 1 (
    echo.
    echo [ERROR] Backend is not responding on 127.0.0.1:8000
    echo         Start it first:  cd backend ^&^& uvicorn app.main:app --reload --port 8000
    echo.
    pause
    exit /b 1
)
echo [OK] Backend is up.
echo.

REM -- run ------------------------------------------------------------------
pushd frontend

if "!MODE!"=="ui" (
    call npm run test:e2e:ui
    set "E2E_EXIT=!errorlevel!"
) else (
    echo Running Playwright ^(this takes a couple of minutes^)...
    echo.
    if defined SPEC (
        call npx playwright test "!SPEC!" !PWARGS!
    ) else (
        if defined GREP (
            call npx playwright test --grep "!GREP!" !PWARGS!
        ) else (
            call npx playwright test !PWARGS!
        )
    )
    set "E2E_EXIT=!errorlevel!"
)

popd

REM -- result ---------------------------------------------------------------
if not "!E2E_EXIT!"=="0" (
    echo.
    echo ==========================================
    echo  [ERROR] E2E FAILED  ^(exit code !E2E_EXIT!^)
    echo ==========================================
    if not "!MODE!"=="ui" (
        echo Opening the HTML report in a new window...
        pushd frontend
        start "Playwright Report" cmd /c "npx playwright show-report"
        popd
    )
    echo.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  [OK] E2E passed.
echo ==========================================
echo.
echo Report:  run_e2e.bat --report
echo.
pause
exit /b 0

:usage
echo.
echo Usage:
echo   run_e2e.bat                    run every spec in frontend/e2e
echo   run_e2e.bat luqun-repair       run one spec file (.spec.ts optional)
echo   run_e2e.bat "Dashboard"        no such file -^> used as --grep instead
echo   run_e2e.bat --ui               Playwright UI mode (debug)
echo   run_e2e.bat --headed           run with a visible browser
echo   run_e2e.bat --report           open the last HTML report
echo.
echo Requires the backend on 127.0.0.1:8000. The frontend dev server is
echo started automatically by playwright.config.ts.
echo.
pause
exit /b 0
