.PHONY: run-server stop-server test lint

PORT=8000

run-server:
	@echo "Starting server on port $(PORT)..."
	nohup poetry run python main.py > output.log 2>&1 & echo $$! > server.pid

stop-server:
	@echo "Stopping server..."
	@if [ -f server.pid ]; then kill -9 `cat server.pid` && rm server.pid; fi || true
	@lsof -t -i:$(PORT) | xargs -r kill -9

test:
	poetry run pytest tests

lint:
	poetry run ruff format .
	poetry run ruff check . --fix