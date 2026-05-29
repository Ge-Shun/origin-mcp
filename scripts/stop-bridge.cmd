@echo off
rem Double-click to stop the Origin-embedded origin-mcp bridge.
rem Prefers the project's virtualenv Python, falling back to "python" on PATH.
setlocal
set "ROOT=%~dp0.."
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0stop_bridge.py"
echo.
pause
