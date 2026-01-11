# Codecov Setup Guide

This guide explains how to set up Codecov for coverage reporting in your GitHub repository.

## Quick Setup

1. **Sign up for Codecov**
   - Go to [codecov.io](https://codecov.io)
   - Sign in with your GitHub account
   - Authorize Codecov to access your repositories

2. **Add Your Repository**
   - Click "Add new repository" in Codecov dashboard
   - Select your `android-build` repository
   - Codecov will automatically detect the repository

3. **Add Codecov Token to GitHub Secrets** (Recommended)
   - In Codecov, go to your repository settings
   - Copy your repository upload token (starts with a long alphanumeric string)
   - Go to your GitHub repository → Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `CODECOV_TOKEN`
   - Value: Paste your Codecov token
   - Click "Add secret"
   
   **Note:** The workflow will work without a token if your repository is connected via GitHub OAuth, but using a token is more reliable.

4. **Update Badge URLs**
   - In `README.md`, replace `USERNAME` with your GitHub username or organization
   - Replace `android-build` with your repository name if different
   - The badges will automatically update once Codecov receives coverage data

## Badge URLs

The badges in README.md use these formats:

```markdown
[![Coverage](https://codecov.io/gh/USERNAME/android-build/branch/main/graph/badge.svg)](https://codecov.io/gh/USERNAME/android-build)
```

Replace:
- `USERNAME` → Your GitHub username or organization
- `android-build` → Your repository name (if different)
- `main` → Your default branch name (if different)

## GitHub Actions Integration

The workflow in `.github/workflows/test.yml` automatically:
- Generates coverage reports using pytest-cov
- Uploads coverage to Codecov using the `codecov-action`
- Works without any additional configuration once Codecov is set up

## Testing the Integration

1. Push a commit to trigger the GitHub Actions workflow
2. Wait for the workflow to complete
3. Check the Codecov dashboard - you should see coverage data
4. The badge in README.md should update automatically

## Troubleshooting

**Badge not updating?**
- Ensure the repository is added in Codecov
- Check that the workflow is uploading coverage successfully
- Verify the badge URL matches your repository

**Coverage not showing?**
- Check GitHub Actions logs for errors
- Ensure `coverage.xml` is being generated
- Verify the Codecov token is set (usually automatic with GitHub integration)

## Manual Upload (Alternative)

If you prefer to upload coverage manually:

```bash
# Install codecov
pip install codecov

# Upload coverage
codecov -f coverage.xml -t YOUR_CODECOV_TOKEN
```

However, the GitHub Actions workflow handles this automatically.
