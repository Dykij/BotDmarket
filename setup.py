from setuptools import setup, find_packages

setup(
    name="dmarket-tools",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "python-telegram-bot>=20.0",
        "python-dotenv",
        "httpx",
    ],
    extras_require={
        "dev": [
            "ruff",
            "mypy",
            "pytest",
            "pytest-asyncio",
        ],
    },
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "dmarket-bot=src.__main__:main",
        ],
    },
    description="Tools for working with DMarket API",
    author="DM Trading Tools Team",
    author_email="example@example.com",
    url="https://github.com/yourusername/dm-trading-tools",
)
