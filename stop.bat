@echo off
:: Default port
set PORT=8000

:: Check for port argument
if not "%1"=="" set PORT=%1

echo Stopping WCInspector on port %PORT%...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
    echo Stopping process (PID: %%a)...
    taskkill /F /PID %%a
)

echo Done.
