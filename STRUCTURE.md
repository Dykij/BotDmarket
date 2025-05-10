# Repository Structure

This document outlines the organization of the BotDmarket repository.

## Directory Structure

```
BotDmarket/
├── config/                  # Configuration files and templates
├── data/                    # Data storage (sales history, etc.)
│   └── sales_history/       # Historical sales data
├── docs/                    # Documentation
│   ├── build/               # Built documentation
│   └── source/              # Documentation source files
├── logs/                    # Application logs
├── scripts/                 # Utility scripts
│   ├── data_processing/     # Data processing utilities
│   ├── deployment/          # Deployment and service scripts
│   └── maintenance/         # Maintenance scripts
├── src/                     # Source code
│   ├── dmarket/             # DMarket API client
│   │   ├── api/             # API client
│   │   ├── filters/         # Market filters
│   │   └── models/          # Data models
│   ├── telegram_bot/        # Telegram bot implementation
│   │   ├── commands/        # Bot commands
│   │   ├── handlers/        # Message handlers
│   │   └── utils/           # Bot utilities
│   └── utils/               # Shared utilities
└── tests/                   # Tests
    ├── dmarket/             # DMarket API tests
    ├── fixtures/            # Test fixtures
    ├── telegram_bot/        # Telegram bot tests
    │   └── handlers/        # Handler tests
    └── utils/               # Utility tests
```

## Key Files

- `src/__main__.py` - Main entry point for the application
- `setup.py` - Package configuration
- `pyproject.toml` - Project metadata and tool configuration
- `requirements.txt` - Dependencies
- `Dockerfile` - Container definition
- `docker-compose.yml` - Container orchestration
- `Makefile` - Common development commands
- `.env.example` - Environment variable template

## Development Workflow

1. **Setup**: 
   - Create a virtual environment with `python -m venv .venv`
   - Install dependencies with `pip install -r requirements.txt`
   - Configure environment variables in `.env`

2. **Development**:
   - Run the application with `python -m src`
   - Run tests with `pytest`
   - Format code with `ruff format`
   - Lint code with `ruff check` and `mypy`

3. **Deployment**:
   - Build Docker image with `docker-compose build`
   - Run container with `docker-compose up -d`

## Testing

Tests are organized to mirror the source code structure:
- Each module has a corresponding test module
- Fixtures are stored in `tests/fixtures/`
- Run tests with `pytest tests/`

## Documentation

Documentation is built with Sphinx:
- Source files in `docs/source/`
- Build with `cd docs && make html`
- Access at `docs/build/html/index.html` 