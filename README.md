# DMarket Telegram Bot

A Telegram bot for DMarket platform operations and market analytics.

## Project Structure

```
BotDmarket/
├── config/              # Configuration files
├── data/                # Data storage
├── docs/                # Documentation
├── logs/                # Log files
├── scripts/             # Utility scripts
├── src/                 # Source code
│   ├── dmarket/         # DMarket API client
│   ├── telegram_bot/    # Telegram bot implementation
│   └── utils/           # Utility functions
└── tests/               # Tests
```

## Installation

### Using pip

```bash
pip install -e .
```

### Development Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For development dependencies
pip install -e ".[dev]"
```

### Using Docker

```bash
# Build the image
docker-compose build

# Run the container
docker-compose up -d
```

## Environment Variables

Create a `.env` file based on the provided `.env.example`:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
DMARKET_PUBLIC_KEY=your_dmarket_public_key
DMARKET_SECRET_KEY=your_dmarket_secret_key
```

## Usage

### Running the Bot

```bash
# Run directly with Python
python -m src

# Or using the Makefile
make run

# Or using Docker
make docker-run
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov
```

### Development Tools

```bash
# Lint code
make lint

# Format code
make format

# Generate documentation
make docs
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please check the CONTRIBUTING.md file for guidelines.
