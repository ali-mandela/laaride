#!/bin/bash
set -e

echo "Starting LaaRide API..."

# Wait for MongoDB to be ready
echo "Waiting for MongoDB..."
until python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import sys

async def check():
    try:
        client = AsyncIOMotorClient(os.environ['MONGODB_URL'], serverSelectionTimeoutMS=2000)
        await client.admin.command('ping')
        client.close()
    except Exception as e:
        print(f'Error connecting to MongoDB: {e}')
        sys.exit(1)

asyncio.run(check())
" 2>/dev/null; do
  echo "MongoDB not ready, retrying in 2s..."
  sleep 2
done
echo "MongoDB ready."

# Seed default routes if needed
echo "Seeding default routes..."
python -c "
import asyncio
from app.services.route_service import seed_default_routes
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import os

async def seed():
    try:
        client = AsyncIOMotorClient(os.environ['MONGODB_URL'])
        db = client[settings.DATABASE_NAME]
        result = await seed_default_routes(db)
        print(f'Routes seeded: {result}')
        client.close()
    except Exception as e:
        print(f'Seeding failed: {e}')

asyncio.run(seed())
"

# Start the API
echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-4}
