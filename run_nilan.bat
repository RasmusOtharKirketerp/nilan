@echo off
setlocal

cd /d "%~dp0"

set "PY=python"
where %PY% >nul 2>nul
if errorlevel 1 (
  set "PY=py -3"
)

set "RUN_LOG=run_output.log"
set "NABTO_OUT=nabto_output.json"

echo [%date% %time%] Starting run > "%RUN_LOG%"
echo [1/2] Running nabto probe (self-contained repo code)...
%PY% nilan_comm.py > "%NABTO_OUT%" 2>> "%RUN_LOG%"
set "NABTO_ERR=%ERRORLEVEL%"

echo [2/2] Done.
echo Nabto output: %NABTO_OUT%
echo Run log: %RUN_LOG%

echo Nabto exit code: %NABTO_ERR% >> "%RUN_LOG%"
if not "%NABTO_ERR%"=="0" echo Nabto probe failed with exit code %NABTO_ERR%

pause
exit /b %NABTO_ERR%
