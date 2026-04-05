#!/bin/bash
# Start Shatter - creates .env from .env.example if needed, then starts Docker
cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo "Creating .env from defaults..."
    cp .env.example .env
    # Generate a random database password
    RANDOPASS=$(openssl rand -base64 24)
    sed -i.bak "s#^POSTGRES_PASSWORD=.*#POSTGRES_PASSWORD=$RANDOPASS#" .env && rm -f .env.bak
    echo ".env created with a random database password."
fi

echo "Starting Shatter..."
docker compose -f docker-compose.dev.yml up -d

if [ $? -ne 0 ]; then
    echo ""
    echo "Docker failed. Make sure Docker Desktop is running, then try again."
else
    echo ""
    echo "Shatter is starting. Open http://localhost:3000 in your browser in a minute or two."
fi

echo ""
read -n 1 -p "Press any key to close..."
