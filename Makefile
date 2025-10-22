.PHONY: docker-build docker-run ci lint format typecheck test

docker-build:
	docker build -t adobe-helper -f examples/adobe/Dockerfile .

docker-run: docker-build
	docker run --rm \
		-e ADOBE_HELPER_ENDPOINTS_FILE=/app/docs/discovery/discovered_endpoints.json \
		adobe-helper

# CI - Run all checks (linting, formatting, type checking, tests)
ci: lint format typecheck test
	@echo "✅ All CI checks passed!"

# Linting with ruff
lint:
	@echo "🔍 Running ruff linting..."
	uv run ruff check adobe/ tests/ examples/

# Formatting check with black
format:
	@echo "🎨 Checking code formatting with black..."
	uv run black --check adobe/ tests/ examples/

# Type checking with mypy
typecheck:
	@echo "🔬 Running type checking with mypy..."
	uv run mypy adobe/

# Run tests with coverage
test:
	@echo "🧪 Running tests with coverage..."
	uv run pytest --cov=adobe --cov-report=xml
