.PHONY: up down db api web install seed

up:
	docker compose up -d db
	@echo "Waiting for Postgres…"
	@sleep 3

down:
	docker compose down

db:
	docker compose up -d db

api:
	cd backend && uvicorn app.main:app --reload --port 8000

web:
	cd frontend && npm run dev

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

seed:
	cd backend && python -m scripts.seed_demo
