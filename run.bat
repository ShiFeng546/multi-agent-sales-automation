@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "BUNDLED_PYTHON=C:\Users\13428\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%BUNDLED_PYTHON%" (
  set "PYTHON_EXE=%BUNDLED_PYTHON%"
) else (
  set "PYTHON_EXE=python"
)

start "" http://127.0.0.1:8000
"%PYTHON_EXE%" "%SCRIPT_DIR%app.py"
