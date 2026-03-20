.PHONY: dev dev-down prod prod-down logs shell seed test build

dev:
	docker-compose up --build

dev-down:
	docker-compose down

prod:
	docker-compose -f docker-compose.prod.yml up -d --build

prod-down:
	docker-compose -f docker-compose.prod.yml down

logs:
	docker-compose logs -f api

shell:
	docker-compose exec api bash

seed:
	docker-compose exec api python -c "import asyncio; from app.services.route_service import seed_default_routes; from app.core.database import get_database; async def run(): db = await get_database(); await seed_default_routes(db); asyncio.run(run())"

test:
	docker-compose exec api python -m pytest tests/ -v

mongo-shell:
	docker-compose exec mongodb mongosh -u laaride -p laaride_dev_password

build:
	docker build -t laaride-api:latest .
