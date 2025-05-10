"""
Конфигурация Sphinx для документации DMarket Bot.
"""

import os
import sys
from datetime import datetime

# Добавляем путь к модулю src
sys.path.insert(0, os.path.abspath('../../src'))

# Основные настройки проекта
project = 'DMarket Bot'
copyright = f'2023-{datetime.now().year}, DMarket Bot Team'
author = 'DMarket Bot Team'
version = '0.1.0'
release = '0.1.0'

# Расширения Sphinx
extensions = [
    'sphinx.ext.autodoc',        # Автоматическая документация из docstrings
    'sphinx.ext.napoleon',       # Поддержка NumPy и Google стилей docstrings
    'sphinx.ext.viewcode',       # Добавляет ссылки на исходный код
    'sphinx.ext.intersphinx',    # Ссылки на другую документацию
    'sphinx.ext.coverage',       # Покрытие документацией
    'sphinx.ext.mathjax',        # Поддержка математических формул
    'sphinx_rtd_theme',          # Тема Read the Docs
]

# Настройки автодокументации
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'special-members': '__init__',
}

# Настройки интерсфинкса для ссылок на документацию Python
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'telegram': ('https://python-telegram-bot.readthedocs.io/en/stable/', None),
}

# Настройки шаблонов
templates_path = ['_templates']
exclude_patterns = []

# Настройки HTML
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_title = 'DMarket Bot Documentation'
html_favicon = '_static/favicon.ico'
html_logo = '_static/logo.png'

# Дополнительные настройки HTML
html_theme_options = {
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': True,
    'style_nav_header_background': '#2980B9',
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# Настройки для сборки документации
source_suffix = '.rst'
master_doc = 'index'
language = 'ru'
pygments_style = 'sphinx'
todo_include_todos = False
