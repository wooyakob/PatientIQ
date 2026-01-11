.PHONY: help dev backend frontend stop

help:
	@echo "Targets:"
	@echo "  make dev       - run backend + frontend in one command"
	@echo "  make backend   - run FastAPI backend on :8000"
	@echo "  make frontend  - run Vite frontend on :8080"
	@echo "  make stop      - best-effort stop anything listening on :8000 and :8080"

backend:
	uv run uvicorn backend.api:app --reload --host 127.0.0.1 --port 8000

frontend:
	npm --prefix frontend run dev

dev:
	@echo "Starting backend + frontend..."
	@echo "Backend:  http://127.0.0.1:8000"
	@echo "Frontend: http://localhost:8080"
	@echo ""
	@echo "Press Ctrl+C to stop both."
	@echo ""
	@set -e; \
	trap 'kill 0' INT TERM; \
	(uv run uvicorn backend.api:app --reload --host 127.0.0.1 --port 8000) & \
	(npm --prefix frontend run dev) & \
	wait

stop:
	@-lsof -ti tcp:8000 | xargs -r kill >/dev/null 2>&1 || true
	@-lsof -ti tcp:8080 | xargs -r kill >/dev/null 2>&1 || true
