.PHONY: lint format type test init-db run-bot run-worker

lint:
	ruff check .

format:
	black .
	ruff format .

type:
	mypy app tests

test:
	pytest

init-db:
	python3 -c "from app.config.loader import load_settings; from app.db.sqlite import connect_sqlite, initialize_schema; s=load_settings(); c=connect_sqlite(s.sqlite); initialize_schema(c); c.close()"

run-bot:
	python3 -m app.bot

run-worker:
	python3 -m app.worker
