.PHONY: install run test lint format clean docker-build docker-run

# Run installation of dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt

# Boot local FastAPI application server
run:
	python scripts/run.py

# Execute automated tests suite
test:
	pytest

# Run formatting checks and strict static typing checks
lint:
	ruff check app
	black --check app
	isort --check-only app
	mypy app

# Format the repository codebase files
format:
	black app tests scripts
	isort app tests scripts
	ruff check app --fix

# Clean cached python compiler files
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	find . -type d -name ".ruff_cache" -exec rm -r {} +
	rm -f .coverage
	rm -f coverage.xml

# Build deployment Docker image
docker-build:
	docker build -t conversational-shl-recommender:latest .

# Launch Docker container run
docker-run:
	docker run -p 8000:8000 --env-file .env conversational-shl-recommender:latest
