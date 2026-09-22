#!/usr/bin/env bash
# ==============================================================================
# Hyderabad Police Ganesh Visarjan Live Tracking System - EC2 Deployment Script
# ==============================================================================
set -e

echo "=== [1/5] Pulling latest repository code ==="
git pull origin main

echo "=== [2/5] Building frontend static bundle ==="
cd frontend
npm ci
npm run build
cd ..

echo "=== [3/5] Building Docker containers (PostGIS, Django, Nginx) ==="
docker compose build --pull

echo "=== [4/5] Launching containers and running migrations ==="
docker compose up -d

echo "=== [5/5] Checking container status ==="
docker compose ps

echo "=============================================================================="
echo "Deployment completed successfully. Live command dashboard available on Port 80."
echo "To run idol dataset import on the production database, execute:"
echo "  docker compose exec backend python manage.py import_idols /app/data/HYDERABAD_Data\ \(15\).xls"
echo "=============================================================================="
