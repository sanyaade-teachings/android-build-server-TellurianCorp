# Setting Up Codecov Token in GitHub

This guide shows you how to add your Codecov token as a GitHub secret so the CI/CD pipeline can upload coverage reports.

## Step-by-Step Instructions

### 1. Get Your Codecov Token

1. Go to [codecov.io](https://codecov.io) and sign in
2. Navigate to your repository settings
3. Find the "Repository Upload Token" section
4. Copy the token (it's a long alphanumeric string)

### 2. Add Token to GitHub Secrets

1. Go to your GitHub repository
2. Click on **Settings** (top menu)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Fill in:
   - **Name**: `CODECOV_TOKEN`
   - **Value**: Paste your Codecov token
6. Click **Add secret**

### 3. Verify the Secret

The secret should now appear in your secrets list. It will be masked (shown as `••••••••`) for security.

### 4. Test the Integration

1. Push a commit to trigger the GitHub Actions workflow
2. Check the workflow run in the **Actions** tab
3. The "Upload coverage to Codecov" step should succeed
4. Check your Codecov dashboard - you should see coverage data

## Alternative: Without Token

If you don't want to use a token, the workflow can still work if:
- Your repository is connected to Codecov via GitHub OAuth
- Codecov has access to your repository

However, using a token is recommended for:
- Better reliability
- More control over uploads
- Private repositories
- Organizations with strict access controls

## Troubleshooting

**Token not working?**
- Verify the token is correct (no extra spaces)
- Check that the secret name is exactly `CODECOV_TOKEN`
- Ensure the token hasn't expired
- Check GitHub Actions logs for specific error messages

**Workflow still failing?**
- The workflow will work without a token if Codecov is connected via GitHub
- Remove the `token:` line from the workflow if you prefer OAuth authentication
- Check Codecov repository settings to ensure it's properly connected

## Security Notes

- Never commit the token to your repository
- The token is stored securely in GitHub Secrets
- Only repository collaborators with appropriate permissions can see/edit secrets
- The token is masked in workflow logs
