@echo off
setlocal

set "REPO_DIR=%~dp0"
set "SETTINGS_FILE=%REPO_DIR%local_settings.json"

set "HA_CONFIG_DIR=%~1"
if "%HA_CONFIG_DIR%"=="" (
  if exist "%SETTINGS_FILE%" (
    for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Content -Raw '%SETTINGS_FILE%' | ConvertFrom-Json).ha.config_path"`) do set "HA_CONFIG_DIR=%%I"
  )
)

if "%HA_CONFIG_DIR%"=="" (
  echo Usage: %~nx0 ^<ha_config_dir^>
  echo Example: %~nx0 C:\HA\config
  echo Or set ha.config_path in local_settings.json
  exit /b 1
)

if "%HA_CONFIG_DIR:~0,1%"=="/" (
  echo Detected Linux path in ha.config_path: %HA_CONFIG_DIR%
  echo This Windows script needs a Windows path, e.g. C:\HA\config
  exit /b 1
)

set "SRC_DIR=%REPO_DIR%custom_components\nilan_nabto"
set "DST_DIR=%HA_CONFIG_DIR%\custom_components\nilan_nabto"

if not exist "%SRC_DIR%" (
  echo Source integration not found: %SRC_DIR%
  exit /b 1
)

if not exist "%HA_CONFIG_DIR%" (
  echo Home Assistant config path does not exist: %HA_CONFIG_DIR%
  exit /b 1
)

echo Publishing Nilan CodeWizard to local Home Assistant config...
if not exist "%HA_CONFIG_DIR%\custom_components" mkdir "%HA_CONFIG_DIR%\custom_components"
if exist "%DST_DIR%" rmdir /s /q "%DST_DIR%"
xcopy "%SRC_DIR%" "%DST_DIR%" /e /i /y >nul

if errorlevel 1 (
  echo Publish failed.
  exit /b 1
)

echo Publish complete.
echo Destination: %DST_DIR%
echo.
echo Next steps:
echo 1. Restart Home Assistant.
echo 2. Reload Nilan CodeWizard integration in Devices ^& Services.
exit /b 0
