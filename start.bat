@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "VBS_LAUNCHER=%SCRIPT_DIR%start_deepscientist_silent.vbs"

if not exist "%VBS_LAUNCHER%" (
    echo Missing silent launcher: "%VBS_LAUNCHER%"
    exit /b 1
)

wscript.exe "%VBS_LAUNCHER%"
exit /b 0
