# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automating various tasks in the DMarket Telegram Bot project.

## Available Workflows

| Workflow | File | Description |
|----------|------|-------------|
| CI | `ci.yml` | Main CI pipeline that runs linting, type checking, and full test suite with coverage reporting |
| Quick Tests | `quick-tests.yml` | Fast test suite that only runs simplified tests with mocks |
| Python Tests | `python-tests.yml` | Comprehensive Python test suite with coverage reporting |
| Code Quality | `code-quality.yml` | Code style, formatting, and type checking |
| Pre-commit Hooks | `pre-commit.yml` | Runs pre-commit hooks on all files |
| Security Analysis | `security-scan.yml` | Analyzes dependencies for security vulnerabilities |

## Composite Actions

We have created a reusable composite action to standardize environment setup across workflows:

| Action | Path | Description |
|--------|------|-------------|
| Setup Python Environment | `.github/actions/setup-python-env` | Sets up Python, installs dependencies, and configures environment |

### Using the Setup Python Environment Action

```yaml
- name: Setup Python and dependencies
  uses: ./.github/actions/setup-python-env
  with:
    python-version: '3.11'
    install-poetry: 'true'
    install-dev-deps: 'true'
    create-env-file: 'true'
```

## How to Use

### For Developers

1. **Push Changes**: GitHub Actions will automatically run when you push to `main`, `master`, or `develop` branches.

2. **Pull Requests**: When you create a PR to these branches, workflows will run to validate your changes.

3. **Manual Execution**: You can manually trigger most workflows from the GitHub Actions tab.

4. **New Features**: When working on a feature branch, the `quick-tests.yml` workflow will run on pushes to validate your changes quickly.

### Setting Up Secrets

For workflows to access DMarket and Telegram APIs during tests, you need to set up secrets in your GitHub repository:

1. Go to your repository settings
2. Navigate to "Secrets and variables" > "Actions"
3. Add the following repository secrets:
   - `DMARKET_PUBLIC_KEY`: Your DMarket public API key
   - `DMARKET_SECRET_KEY`: Your DMarket secret API key
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `CODECOV_TOKEN`: Token for uploading coverage reports to Codecov (optional)

### Local Testing

Before pushing your changes, you can run the same checks locally:

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run linting
python -m ruff check .

# Run type checking
mypy .

# Run simplified test suite
pytest tests/dmarket/test_dmarket_api_simplified.py tests/telegram_bot/test_arbitrage_scanner_simplified.py -v

# Run full test suite with coverage
pytest --cov=src --cov-report=term
```

## Troubleshooting Common Issues

### Dependency Installation Failures

If you encounter issues with dependency installation:

1. Check if you're using Poetry or requirements.txt in your local development
2. Make sure all dependencies are properly specified
3. Consider updating the Python version in the workflows

### Test Failures

If tests fail in CI but pass locally:

1. Check if there are differences in environment variables
2. Verify if CI is running with proper PYTHONPATH settings
3. Look for platform-specific issues (Windows vs. Linux)

## Workflow Customization

If you need to customize a workflow:

1. Edit the appropriate YAML file in this directory
2. Commit and push your changes
3. The updated workflow will be available immediately for manual runs and will be used for future automated runs 