.. _utils_modules:

======================
Утилиты (utils)
======================

Модули утилит предоставляют вспомогательные функции и классы, используемые в других частях проекта.

.. toctree::
   :maxdepth: 2

   performance
   rate_limiter

Модуль performance
-----------------

Модуль :mod:`performance` предоставляет инструменты для оптимизации производительности,
включая систему кеширования и профилирование выполнения функций.

.. automodule:: src.utils.performance
   :members:
   :undoc-members:
   :show-inheritance:

Модуль rate_limiter
------------------

Модуль :mod:`rate_limiter` предоставляет механизм ограничения скорости запросов к API
для предотвращения превышения лимитов.

.. automodule:: src.utils.rate_limiter
   :members:
   :undoc-members:
   :show-inheritance: 