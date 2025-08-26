.PHONY: install run-api run-graphics run-middleware run-all test clean

install:
	@echo "Installing all dependencies..."
	uv pip install -e ./packages/middleware -e ./packages/api

run-api:
	python ./packages/api/src/api/main.py

run-graphics:
	cd packages/middleware/src && set PYTHONPATH=. && python -m graphics.window

run-middleware:
	cd packages/middleware/src && set PYTHONPATH=. && python -m middleware.engine

run-all:
	$(MAKE) run-graphics & \
	$(MAKE) run-middleware & \
	wait

test:
	@echo "Running tests..."
	@$(MAKE) -C ./packages/middleware test || true
	@$(MAKE) -C ./packages/api test || true

clean:
	@echo "Cleaning..."
	find ./packages -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache