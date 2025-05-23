# Руководство по использованию GitHub Copilot в этом репозитории

## 1. Структурируйте код и документацию
- Используйте понятные имена файлов, папок, функций и переменных.
- Добавляйте комментарии и docstring’и к функциям, классам и модулям.
- Описывайте назначение и структуру проекта в README.md.

## 2. Используйте англоязычные комментарии
- Copilot лучше понимает и генерирует код на основе англоязычных комментариев и описаний.
- Для сложных участков кода пишите подробные комментарии, описывающие ожидаемое поведение.

## 3. Пишите инструкции и TODO
- Используйте TODO, FIXME, NOTE и другие маркеры для обозначения мест, требующих доработки или внимания.
- Copilot может предлагать решения для таких мест.

## 4. Следите за стилем кода
- Соблюдайте единый стиль кодирования (например, PEP8 для Python, PSR для PHP, стандарт Go и т.д.).
- Используйте линтеры и форматтеры — Copilot подстраивается под стиль проекта.

## 5. Используйте типизацию
- Добавляйте аннотации типов, если язык поддерживает (TypeScript, Python, PHP 7+ и т.д.).
- Это помогает Copilot предлагать более точные и безопасные решения.

## 6. Покрывайте код тестами
- Наличие тестов помогает Copilot предлагать тестовые сценарии и примеры использования функций.

## 7. Обновляйте зависимости
- Следите за актуальностью зависимостей в package.json, requirements.txt и других менеджерах пакетов.

## 8. Используйте Copilot Chat для уточнения
- Задавайте Copilot вопросы по коду, просите объяснить или сгенерировать примеры.

## 9. Проверяйте и редактируйте предложения Copilot
- Всегда просматривайте и тестируйте сгенерированный код перед коммитом.

## 10. Ограничьте доступ к приватным данным
- Не храните секреты, пароли и приватные ключи в открытом виде — Copilot может использовать их в предложениях.

---

### Пример комментария для генерации функции

```python
# Calculate the moving average for a list of prices with a given window size.
def moving_average(prices: list[float], window: int) -> list[float]:
    # ...
```

---

### Дополнительные ресурсы

- [Официальная документация GitHub Copilot (RU)](https://docs.github.com/ru/copilot)
- [Рекомендации по безопасности Copilot](https://docs.github.com/ru/copilot/getting-started-with-github-copilot/about-github-copilot-safety)
