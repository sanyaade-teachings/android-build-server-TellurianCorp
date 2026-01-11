.PHONY: test test-cov test-html install clean

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	pytest

# Run tests with coverage
test-cov:
	pytest --cov=. --cov-report=term-missing

# Run tests and generate HTML coverage report
test-html:
	pytest --cov=. --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

# Clean test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Run tests in verbose mode
test-verbose:
	pytest -v

# Run specific test file
test-file:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make test-file FILE=tests/test_device.py"; \
	else \
		pytest $(FILE) -v; \
	fi
