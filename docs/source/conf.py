"""Конфигурация Sphinx для документации проекта DMarket Bot."""

import os
import sys
from datetime import datetime

# Добавляем путь к исходному коду проекта
sys.path.insert(0, os.path.abspath("../.."))

# Информация о проекте
project = "DMarket Bot"
copyright = f"{datetime.now().year}, DMarket Team"
author = "DMarket Team"
release = "1.0.0"

# Расширения
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
]

# Шаблоны
templates_path = ["_templates"]
exclude_patterns = []

# Язык документации
language = "ru"

# HTML настройки
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Настройки автодокументации
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autoclass_content = "both"

# Настройки форматирования документации
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = True
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_keyword = True
napoleon_custom_sections = None

# Ссылки на другие документации
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
