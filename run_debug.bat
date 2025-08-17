@echo off
echo Fuehre Debug-Check aus...
docker-compose exec app python /app/scripts/debug_check.py
echo.
pause
