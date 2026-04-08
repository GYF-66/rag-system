@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

if "%OPENAI_API_KEY%"=="" (
  if exist "%PROJECT_ROOT%\.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%PROJECT_ROOT%\.env") do (
      if /I "%%A"=="OPENAI_API_KEY" set "OPENAI_API_KEY=%%B"
    )
  )
)

if "%OPENAI_API_KEY%"=="" (
  echo Missing OPENAI_API_KEY environment variable. 1>&2
  exit /b 1
)

npx -y @openai/codex@0.57.0 ^
  -c model_provider=\"lansekafei\" ^
  -c model=\"qwen3-coder-plus\" ^
  -c model_providers.lansekafei.name=\"Lansekafei\" ^
  -c model_providers.lansekafei.base_url=\"https://www.lansekafei.asia/v1\" ^
  -c model_providers.lansekafei.env_key=\"OPENAI_API_KEY\" ^
  -c model_providers.lansekafei.wire_api=\"chat\" ^
  -c model_providers.lansekafei.requires_openai_auth=false ^
  %*

exit /b %ERRORLEVEL%
