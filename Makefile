.PHONY: lint test run-cli

lint:
	ruff check src tests
	mypy src

test:
	pytest

run-cli:
	python -m aviation_briefing.cli $(ARGS)
