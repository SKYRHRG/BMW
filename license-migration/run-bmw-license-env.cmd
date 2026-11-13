@echo off
setlocal
rem BMW LICENSE-ONLY MIGRATION — legacy executable is not modified.
rem Set URL below to your OWN deployed HTTPS license server endpoint.
rem Note: the protected bmw_gui application may ignore LICENSE_API_URL.
set "LICENSE_API_URL=https://YOUR-LICENSE-DOMAIN.example/api/app/fauth/license/check"
if not exist "%~dp0BMW.exe" (
  echo BMW.exe not found beside this launcher.
  pause
  exit /b 2
)
echo Launching original BMW.exe with the requested license endpoint configuration.
echo This launcher does not bypass validation or modify the EXE.
start "" /D "%~dp0" "%~dp0BMW.exe"
exit /b 0
