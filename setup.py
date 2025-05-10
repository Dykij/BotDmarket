"""
setup.py

Скрипт для установки и публикации пакета dmarket-bot.
Содержит описание зависимостей, точек входа, метаданных и структуры пакета.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dmarket-bot",
    version="0.1.0",
    description="Бот для торговли игровыми предметами на площадке DMarket",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DMarket Bot Team",
    author_email="example@example.com",
    url="https://github.com/example/dmarket-bot",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "python-telegram-bot>=20.0",
        "python-dotenv>=1.0.0",
        "requests>=2.30.0",
        "httpx>=0.27.0",
        "psutil>=7.0.0",
    ],
    extras_require={
        "dev": [
            "ruff",
            "mypy",
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
            "black",
            "sphinx",
            "sphinx-rtd-theme",
        ],
    },
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "dmarket-bot=src.__main__:main",
            "dmarket-run=src.telegram_bot.bot_v2:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 