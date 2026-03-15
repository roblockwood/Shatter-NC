@echo off
REM Pull latest from GitHub, stop Shatter dev stack, rebuild images, then start again.
setlocal

cd /d "%~dp0"
set "COMPOSE_FILE=%~dp0docker-compose.dev.yml"

echo Pulling latest from GitHub...
git pull
if errorlevel 1 goto :error

echo Stopping Shatter (docker-compose.dev.yml)...
docker compose -f "%COMPOSE_FILE%" down
if errorlevel 1 goto :error

echo Building images...
docker compose -f "%COMPOSE_FILE%" build
if errorlevel 1 goto :error

echo Starting Shatter...
docker compose -f "%COMPOSE_FILE%" up -d
if errorlevel 1 goto :error

echo Done. Backend: 8000, Frontend: 3000, Postgres: 5432
goto :end

:error
echo Failed. Check errors above.
exit /b 1

:end
endlocal
pause
