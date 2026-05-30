@echo off
rem Double-click to stop the Origin-embedded origin-mcp bridge.
rem Uses the active system Python on PATH.
setlocal
python "%~dp0stop_bridge.py"
echo.
pause
