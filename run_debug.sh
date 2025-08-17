#!/bin/bash
echo "Kopiere Debug-Script in Container..."
docker cp debug_check.py automaten_app:/app/debug_check.py
echo ""
echo "Führe Debug-Check aus..."
docker-compose exec app python /app/debug_check.py
echo ""
