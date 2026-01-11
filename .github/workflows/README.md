# GitHub Actions Workflows

This directory contains CI/CD workflows for the Android Build Server project.

## Workflows

### test.yml
Runs the test suite across multiple Python versions and generates coverage reports.

**Triggers:**
- Push to `main` or `master` branches
- Pull requests to `main` or `master` branches

**Actions:**
- Tests on Python 3.9, 3.10, 3.11, and 3.12
- Generates coverage reports
- Uploads coverage to Codecov
- Creates HTML coverage artifacts

### lint.yml
Performs code quality checks using flake8 and pylint.

**Triggers:**
- Push to `main` or `master` branches
- Pull requests to `main` or `master` branches

**Actions:**
- Runs flake8 for style checking
- Runs pylint for code analysis

## Setup

1. Ensure your repository is on GitHub
2. Update badge URLs in README.md with your username/organization
3. (Optional) Set up Codecov for coverage tracking
4. Push to trigger workflows

## Viewing Results

- Go to the **Actions** tab in your GitHub repository
- Click on a workflow run to see detailed logs
- Download coverage HTML reports from artifacts
