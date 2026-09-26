.PHONY: install run lint test quality docker-build

install:
	python -m pip install -r requirements-dev.txt

run:
	uvicorn app.main:app --reload

lint:
	ruff check app tests

test:
	pytest

quality: lint test

docker-build:
	docker build -t webhook-inspector .
