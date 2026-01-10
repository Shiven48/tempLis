.PHONY: run run-dev run-prod test clean help

# Development server (default)
run: run-dev

# Development with auto-reload
run-dev:
	uvicorn api.main:app --reload --app-dir ./src --host 127.0.0.1 --port 8000

# Production-like server
run-prod:
	uvicorn api.main:app --app-dir ./src --host 0.0.0.0 --port 8000 --workers 4

# Run tests
test:
	@echo "No tests configured for api yet."
	# Future: python -m pytest tests/

# Clean up generated files
clean:
	@echo "Cleaning up..."
	@rm -rf __pycache__ .pytest_cache .coverage htmlcov/ .tox/
	@find . -type d -name "__pycache__" -delete
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@rm -f lab_results.db  # Remove SQLite DB if needed

# Show help
help:
	@echo "Available targets:"
	@echo "  run-dev   - Start development server with auto-reload"
	@echo "  run-prod  - Start production server"
	@echo "  test      - Run tests"
	@echo "  clean     - Clean up generated files"
	@echo "  help      - Show this help message"
