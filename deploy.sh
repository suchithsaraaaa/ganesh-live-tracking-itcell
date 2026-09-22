#!/usr/bin/env bash
# ==============================================================================
# Hyderabad Police Ganesh Visarjan Live Tracking System - EC2 Deployment Script
# ==============================================================================
set -e

echo "=== [Preflight] Validating production environment configuration ==="
if [ ! -f .env ] && [ -z "$SECRET_KEY" ]; then
    echo "ERROR: No production .env file or environment variables detected."
    echo "Please copy .env.example to .env and configure all required variables:"
    echo "  cp .env.example .env"
    exit 1
fi

# Function to get variable from environment or .env file
get_env_val() {
    local var_name="$1"
    local val="${!var_name}"
    if [ -z "$val" ] && [ -f .env ]; then
        val=$(grep -E "^[[:space:]]*${var_name}=" .env | head -n 1 | cut -d '=' -f2- | tr -d ' "\r\n')
    fi
    echo "$val"
}

SECRET_KEY_VAL=$(get_env_val "SECRET_KEY")
ALLOWED_HOSTS_VAL=$(get_env_val "ALLOWED_HOSTS")
DB_PASSWORD_VAL=$(get_env_val "DB_PASSWORD")

# Check required variables exist and are non-empty
if [ -z "$SECRET_KEY_VAL" ] || [ -z "$ALLOWED_HOSTS_VAL" ] || [ -z "$DB_PASSWORD_VAL" ]; then
    echo "ERROR: The following required environment variables must be defined in .env or the environment:"
    [ -z "$SECRET_KEY_VAL" ] && echo "  - SECRET_KEY"
    [ -z "$ALLOWED_HOSTS_VAL" ] && echo "  - ALLOWED_HOSTS"
    [ -z "$DB_PASSWORD_VAL" ] && echo "  - DB_PASSWORD"
    exit 1
fi

# Check against wildcard and insecure placeholders
if [ "$ALLOWED_HOSTS_VAL" = "*" ]; then
    echo "ERROR: Wildcard ALLOWED_HOSTS='*' is not permitted in production."
    exit 1
fi

if [[ "$SECRET_KEY_VAL" == *"change-me"* ]] || [ "$SECRET_KEY_VAL" = "police_secret_key_change_in_production" ]; then
    echo "ERROR: Insecure placeholder detected for SECRET_KEY. Please configure a genuine secret key."
    exit 1
fi

if [[ "$DB_PASSWORD_VAL" == *"change-me"* ]] || [ "$DB_PASSWORD_VAL" = "police_secure_pass_2026" ]; then
    echo "ERROR: Insecure placeholder detected for DB_PASSWORD. Please configure a genuine database password."
    exit 1
fi

# Validate compose configuration syntax
docker compose config > /dev/null
echo "Preflight check passed: Production environment configuration verified."

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
