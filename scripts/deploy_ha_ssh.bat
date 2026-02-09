@echo off
setlocal

set "ROOT=%~dp0.."
set "SETTINGS=%ROOT%\local_settings.json"

if not exist "%SETTINGS%" (
  echo Missing %SETTINGS%
  exit /b 1
)

for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Content -Raw '%SETTINGS%' | ConvertFrom-Json).ha.host"`) do set "HOST=%%I"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Content -Raw '%SETTINGS%' | ConvertFrom-Json).ha.port"`) do set "PORT=%%I"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Content -Raw '%SETTINGS%' | ConvertFrom-Json).ha.username"`) do set "USER=%%I"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Content -Raw '%SETTINGS%' | ConvertFrom-Json).ha.config_path"`) do set "CONFIG_PATH=%%I"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Content -Raw '%SETTINGS%' | ConvertFrom-Json).ha.auth.private_key_path"`) do set "KEY_PATH=%%I"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Content -Raw '%SETTINGS%' | ConvertFrom-Json).ha.auth.method"`) do set "AUTH_METHOD=%%I"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Content -Raw '%SETTINGS%' | ConvertFrom-Json).ha.auth.password"`) do set "PASSWORD=%%I"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Content -Raw '%SETTINGS%' | ConvertFrom-Json).deploy.integration_src"`) do set "SRC_REL=%%I"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Content -Raw '%SETTINGS%' | ConvertFrom-Json).deploy.integration_name"`) do set "NAME=%%I"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Content -Raw '%SETTINGS%' | ConvertFrom-Json).deploy.restart_after_deploy"`) do set "RESTART=%%I"

if "%HOST%"=="" ( echo Missing ha.host & exit /b 1 )
if "%USER%"=="" ( echo Missing ha.username & exit /b 1 )
if "%CONFIG_PATH%"=="" ( echo Missing ha.config_path & exit /b 1 )
if "%PORT%"=="" set "PORT=22"
if "%SRC_REL%"=="" set "SRC_REL=custom_components/nilan_nabto"
if "%NAME%"=="" set "NAME=nilan_nabto"

set "SRC=%ROOT%\%SRC_REL:/=\%"
if not exist "%SRC%" (
  echo Missing source dir: %SRC%
  exit /b 1
)

set "SSH=ssh -p %PORT% -o StrictHostKeyChecking=accept-new"
set "SCP=scp -P %PORT% -o StrictHostKeyChecking=accept-new"
if not "%KEY_PATH%"=="" (
  set "SSH=%SSH% -i "%KEY_PATH%""
  set "SCP=%SCP% -i "%KEY_PATH%""
)

if /I "%AUTH_METHOD%"=="password" (
  if not "%PASSWORD%"=="" (
    where plink >nul 2>nul
    if errorlevel 1 (
      echo Password auth requested, but plink/pscp not found.
      echo Install PuTTY tools or use scripts/deploy_ha_ssh.sh with sshpass.
      exit /b 1
    )
    where pscp >nul 2>nul
    if errorlevel 1 (
      echo Password auth requested, but pscp not found.
      echo Install PuTTY tools or use scripts/deploy_ha_ssh.sh with sshpass.
      exit /b 1
    )
    set "SSH=plink -P %PORT% -batch -pw %PASSWORD%"
    set "SCP=pscp -P %PORT% -batch -pw %PASSWORD%"
    if not "%KEY_PATH%"=="" (
      set "SSH=%SSH% -i "%KEY_PATH%""
      set "SCP=%SCP% -i "%KEY_PATH%""
    )
  )
)

set "REMOTE_TMP=/tmp/%NAME%_upload"
set "REMOTE_DST=%CONFIG_PATH%/custom_components/%NAME%"

echo Deploying %NAME% to %USER%@%HOST%:%REMOTE_DST%
%SSH% %USER%@%HOST% "mkdir -p '%CONFIG_PATH%/custom_components' && rm -rf '%REMOTE_TMP%'"
if errorlevel 1 exit /b 1

%SCP% -r "%SRC%" %USER%@%HOST%:/tmp/
if errorlevel 1 exit /b 1

%SSH% %USER%@%HOST% "rm -rf '%REMOTE_TMP%' && mv '/tmp/%NAME%' '%REMOTE_TMP%' && rm -rf '%REMOTE_DST%' && mv '%REMOTE_TMP%' '%REMOTE_DST%'"
if errorlevel 1 exit /b 1

%SSH% %USER%@%HOST% "test -f '%REMOTE_DST%/manifest.json' && test -f '%REMOTE_DST%/__init__.py' && test -f '%REMOTE_DST%/config_flow.py' && test -d '%REMOTE_DST%/vendor/genvexnabto'"
if errorlevel 1 (
  echo Deploy verification failed on remote host.
  exit /b 1
)

echo Deploy complete and verified.

if /I "%RESTART%"=="True" goto restart
if /I "%RESTART%"=="true" goto restart

echo Next: Restart Home Assistant or reload integration in UI.
exit /b 0

:restart
echo restart_after_deploy=true - sending restart command...
%SSH% %USER%@%HOST% "ha core restart || supervisorctl restart home-assistant || true"
echo Restart command sent.
exit /b 0
