@echo off
setlocal

cd /d "%~dp0"

set "PY=python"
where %PY% >nul 2>nul
if errorlevel 1 (
  set "PY=py -3"
)

set "RUN_LOG=run_output.log"
set "LOCAL_OUT=local_output.json"
set "NABTO_OUT=nabto_output.json"

echo [%date% %time%] Starting run > "%RUN_LOG%"
echo [1/4] Installing/updating required Python packages...
%PY% -m pip install --user -r requirements.txt >> "%RUN_LOG%" 2>&1
if errorlevel 1 (
  echo Failed to install requirements. See %RUN_LOG%
  pause
  exit /b 1
)
%PY% -m pip check >> "%RUN_LOG%" 2>&1
if errorlevel 1 (
  echo Dependency integrity check failed. See %RUN_LOG%
  pause
  exit /b 1
)

echo [2/4] Running local probe...
%PY% nilan_comm.py local > "%LOCAL_OUT%" 2>> "%RUN_LOG%"
set "LOCAL_ERR=%ERRORLEVEL%"

echo [3/4] Running nabto probe...
%PY% nilan_comm.py nabto > "%NABTO_OUT%" 2>> "%RUN_LOG%"
set "NABTO_ERR=%ERRORLEVEL%"

echo [4/4] Done.
echo Local output: %LOCAL_OUT%
echo Nabto output: %NABTO_OUT%
echo Run log: %RUN_LOG%

echo Local exit code: %LOCAL_ERR% >> "%RUN_LOG%"
echo Nabto exit code: %NABTO_ERR% >> "%RUN_LOG%"

if not "%LOCAL_ERR%"=="0" echo Local probe failed with exit code %LOCAL_ERR%
if not "%NABTO_ERR%"=="0" echo Nabto probe failed with exit code %NABTO_ERR%

pause
exit /b 0
