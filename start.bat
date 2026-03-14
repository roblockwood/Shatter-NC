@echo off
setlocal enabledelayedexpansion
REM Start Shatter - creates .env from .env.example if needed, then starts Docker
cd /d "%~dp0"

if not exist .env (
    echo Creating .env from defaults...
    copy .env.example .env >nul
    REM Generate a random database password and update .env
    for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "[Convert]::ToBase64String((1..24 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])"`) do set RANDOPASS=%%i
    powershell -NoProfile -Command "(Get-Content .env) -replace 'POSTGRES_PASSWORD=.*', 'POSTGRES_PASSWORD=!RANDOPASS!' | Set-Content .env"
    echo .env created with a random database password.
)

echo Starting Shatter...
docker compose -f docker-compose.dev.yml up -d

if %ERRORLEVEL% neq 0 (
    echo.
    echo Docker failed. Make sure Docker Desktop is running, then try again.
) else (
    echo.
    echo Shatter is starting. Open http://localhost:3000 in your browser in a minute or two.
)

echo.
pause
