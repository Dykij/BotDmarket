"""Модуль локализации для Telegram-бота DMarket.
Содержит строки интерфейса на различных языках.

Поддерживаемые языки:
- ru: Русский
- en: English
- es: Español
- de: Deutsch
"""

# Список поддерживаемых языков
LANGUAGES = {
    "ru": "Русский",
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
}

# Локализованные строки
LOCALIZATIONS = {
    # Русский язык (базовый)
    "ru": {
        # Общие строки
        "welcome": "Привет, {user}! 👋\n\nЯ бот для арбитража DMarket. Помогу найти выгодные сделки.\n\nИспользуйте меню для выбора желаемой операции:",
        "help": "Доступные команды:\n\n/start - Начать работу с ботом\n/arbitrage - Открыть меню арбитража\n/dmarket - Проверить статус DMarket API\n/settings - Настройки профиля\n/help - Показать эту справку",
        "select_mode": "📊 Выберите режим арбитража:",
        "checking_api": "🔍 Проверяю статус DMarket API...",
        "api_ok": "✅ API работает нормально.\n\n🕒 Последнее обновление: только что",
        "api_error": "❌ Ошибка API DMarket: {error}",
        "back_button": "⬅️ Назад",
        "back_to_menu": "⬅️ Назад в меню",
        # Настройки
        "settings": "⚙️ Настройки профиля",
        "language": "🌐 Текущий язык: {lang}\n\nВыберите язык интерфейса:",
        "language_set": "✅ Язык установлен: {lang}",
        "api_settings": "🔑 Настройки API DMarket",
        "api_key_prompt": "Введите публичный ключ API DMarket:",
        "api_secret_prompt": "Введите секретный ключ API DMarket:",
        "api_keys_set": "✅ API ключи установлены. Теперь вы можете использовать все функции бота.",
        "trade_settings": "💼 Настройки торговли",
        "auto_trading_on": "✅ Автоматическая торговля ВКЛЮЧЕНА",
        "auto_trading_off": "❌ Автоматическая торговля ВЫКЛЮЧЕНА",
        # Арбитраж
        "arbitrage_boost": "🚀 Разгон баланса",
        "arbitrage_mid": "💼 Средний трейдер",
        "arbitrage_pro": "💰 Trade Pro",
        "best_opportunities": "🌟 Лучшие возможности",
        "auto_arbitrage": "🤖 Авто-арбитраж",
        "select_game": "🎮 Выбрать игру",
        "game_selected": "🎮 Выбрана игра: {game}",
        # Автоматический арбитраж
        "auto_low": "💰 Минимальная прибыль",
        "auto_medium": "💰💰 Средняя прибыль",
        "auto_high": "💰💰💰 Высокая прибыль",
        "auto_stats": "📊 Статистика",
        "auto_stop": "🛑 Остановить",
        "auto_searching": "🔍 Ищу возможности автоматического арбитража...",
        "auto_found": "✅ Найдено {count} предметов для арбитража.",
        "auto_no_results": "ℹ️ Не найдено предметов для арбитража.",
        "auto_processing": "⏳ Обрабатываем и готовим к автоматической торговле...",
        "auto_insufficient_balance": "⚠️ Недостаточно средств для торговли.\n\nТекущий баланс: ${balance:.2f}\nДля торговли необходимо минимум $1.00",
        "auto_completed": "✅ Арбитраж завершен!\n\nНайдено предметов: {found}\nКупленные предметы: {purchases}\nПроданные предметы: {sales}\nОбщая прибыль: ${profit:.2f}",
        # Ошибки
        "error_general": "❌ Произошла ошибка: {error}",
        "error_api_keys": "❌ Ошибка: API ключи DMarket не настроены.\n\nДля использования автоматического арбитража необходимо указать API ключи DMarket с помощью команды /setup.",
        "try_again": "🔄 Попробовать снова",
        # Риск и ликвидность
        "risk_low": "низкий",
        "risk_medium": "средний",
        "risk_high": "высокий",
        "liquidity_low": "низкая",
        "liquidity_medium": "средняя",
        "liquidity_high": "высокая",
        # Финансы
        "balance": "💰 Баланс: ${balance:.2f}",
        "insufficient_balance": "⚠️ Недостаточно средств: ${balance:.2f}",
        "profit": "📈 Прибыль: ${profit:.2f} ({percent:.1f}%)",
        # Пагинация
        "pagination_status": "📄 Страница {current} из {total}",
        "next_page": "➡️ Вперед",
        "previous_page": "⬅️ Назад",
    },
    # English
    "en": {
        # General strings
        "welcome": "Hello, {user}! 👋\n\nI'm a DMarket arbitrage bot. I'll help you find profitable deals.\n\nUse the menu to select your desired operation:",
        "help": "Available commands:\n\n/start - Start working with the bot\n/arbitrage - Open arbitrage menu\n/dmarket - Check DMarket API status\n/settings - Profile settings\n/help - Show this help",
        "select_mode": "📊 Select arbitrage mode:",
        "checking_api": "🔍 Checking DMarket API status...",
        "api_ok": "✅ API is working normally.\n\n🕒 Last update: just now",
        "api_error": "❌ DMarket API error: {error}",
        "back_button": "⬅️ Back",
        "back_to_menu": "⬅️ Back to menu",
        # Settings
        "settings": "⚙️ Profile settings",
        "language": "🌐 Current language: {lang}\n\nSelect interface language:",
        "language_set": "✅ Language set to: {lang}",
        "api_settings": "🔑 DMarket API settings",
        "api_key_prompt": "Enter your DMarket API public key:",
        "api_secret_prompt": "Enter your DMarket API secret key:",
        "api_keys_set": "✅ API keys have been set. You can now use all bot features.",
        "trade_settings": "💼 Trade settings",
        "auto_trading_on": "✅ Automatic trading is ENABLED",
        "auto_trading_off": "❌ Automatic trading is DISABLED",
        # Arbitrage
        "arbitrage_boost": "🚀 Balance Booster",
        "arbitrage_mid": "💼 Mid Trader",
        "arbitrage_pro": "💰 Trade Pro",
        "best_opportunities": "🌟 Best Opportunities",
        "auto_arbitrage": "🤖 Auto Arbitrage",
        "select_game": "🎮 Select game",
        "game_selected": "🎮 Selected game: {game}",
        # Auto arbitrage
        "auto_low": "💰 Minimum profit",
        "auto_medium": "💰💰 Medium profit",
        "auto_high": "💰💰💰 High profit",
        "auto_stats": "📊 Statistics",
        "auto_stop": "🛑 Stop",
        "auto_searching": "🔍 Searching for automatic arbitrage opportunities...",
        "auto_found": "✅ Found {count} items for arbitrage.",
        "auto_no_results": "ℹ️ No arbitrage items found.",
        "auto_processing": "⏳ Processing and preparing for automatic trading...",
        "auto_insufficient_balance": "⚠️ Insufficient balance for trading.\n\nCurrent balance: ${balance:.2f}\nMinimum required: $1.00",
        "auto_completed": "✅ Arbitrage completed!\n\nItems found: {found}\nItems purchased: {purchases}\nItems sold: {sales}\nTotal profit: ${profit:.2f}",
        # Errors
        "error_general": "❌ An error occurred: {error}",
        "error_api_keys": "❌ Error: DMarket API keys are not configured.\n\nTo use automatic arbitrage, you need to set DMarket API keys using the /setup command.",
        "try_again": "🔄 Try again",
        # Risk and liquidity
        "risk_low": "low",
        "risk_medium": "medium",
        "risk_high": "high",
        "liquidity_low": "low",
        "liquidity_medium": "medium",
        "liquidity_high": "high",
        # Finances
        "balance": "💰 Balance: ${balance:.2f}",
        "insufficient_balance": "⚠️ Insufficient balance: ${balance:.2f}",
        "profit": "📈 Profit: ${profit:.2f} ({percent:.1f}%)",
        # Pagination
        "pagination_status": "📄 Page {current} of {total}",
        "next_page": "➡️ Next",
        "previous_page": "⬅️ Previous",
    },
    # Español
    "es": {
        # Cadenas generales
        "welcome": "¡Hola, {user}! 👋\n\nSoy un bot de arbitraje de DMarket. Te ayudaré a encontrar ofertas rentables.\n\nUtiliza el menú para seleccionar la operación deseada:",
        "help": "Comandos disponibles:\n\n/start - Comenzar a trabajar con el bot\n/arbitrage - Abrir menú de arbitraje\n/dmarket - Verificar estado de API de DMarket\n/settings - Configuración de perfil\n/help - Mostrar esta ayuda",
        "select_mode": "📊 Selecciona el modo de arbitraje:",
        "checking_api": "🔍 Verificando el estado de la API de DMarket...",
        "api_ok": "✅ La API está funcionando normalmente.\n\n🕒 Última actualización: ahora mismo",
        "api_error": "❌ Error de API de DMarket: {error}",
        "back_button": "⬅️ Atrás",
        "back_to_menu": "⬅️ Volver al menú",
        # Configuración
        "settings": "⚙️ Configuración de perfil",
        "language": "🌐 Idioma actual: {lang}\n\nSelecciona el idioma de la interfaz:",
        "language_set": "✅ Idioma establecido: {lang}",
        "api_settings": "🔑 Configuración de API de DMarket",
        "api_key_prompt": "Introduce tu clave pública de API de DMarket:",
        "api_secret_prompt": "Introduce tu clave secreta de API de DMarket:",
        "api_keys_set": "✅ Las claves API han sido configuradas. Ahora puedes usar todas las funciones del bot.",
        "trade_settings": "💼 Configuración de comercio",
        "auto_trading_on": "✅ El comercio automático está ACTIVADO",
        "auto_trading_off": "❌ El comercio automático está DESACTIVADO",
        # Arbitraje
        "arbitrage_boost": "🚀 Impulsor de Balance",
        "arbitrage_mid": "💼 Comerciante Medio",
        "arbitrage_pro": "💰 Comerciante Pro",
        "best_opportunities": "🌟 Mejores Oportunidades",
        "auto_arbitrage": "🤖 Auto Arbitraje",
        "select_game": "🎮 Seleccionar juego",
        "game_selected": "🎮 Juego seleccionado: {game}",
        # Auto arbitraje
        "auto_low": "💰 Beneficio mínimo",
        "auto_medium": "💰💰 Beneficio medio",
        "auto_high": "💰💰💰 Beneficio alto",
        "auto_stats": "📊 Estadísticas",
        "auto_stop": "🛑 Detener",
        "auto_searching": "🔍 Buscando oportunidades de arbitraje automático...",
        "auto_found": "✅ Se encontraron {count} artículos para arbitraje.",
        "auto_no_results": "ℹ️ No se encontraron artículos para arbitraje.",
        "auto_processing": "⏳ Procesando y preparando para comercio automático...",
        "auto_insufficient_balance": "⚠️ Saldo insuficiente para comerciar.\n\nSaldo actual: ${balance:.2f}\nMínimo requerido: $1.00",
        "auto_completed": "✅ ¡Arbitraje completado!\n\nArtículos encontrados: {found}\nArtículos comprados: {purchases}\nArtículos vendidos: {sales}\nBeneficio total: ${profit:.2f}",
        # Errores
        "error_general": "❌ Ocurrió un error: {error}",
        "error_api_keys": "❌ Error: Las claves API de DMarket no están configuradas.\n\nPara usar el arbitraje automático, debes configurar las claves API de DMarket usando el comando /setup.",
        "try_again": "🔄 Intentar de nuevo",
        # Riesgo y liquidez
        "risk_low": "bajo",
        "risk_medium": "medio",
        "risk_high": "alto",
        "liquidity_low": "baja",
        "liquidity_medium": "media",
        "liquidity_high": "alta",
        # Finanzas
        "balance": "💰 Saldo: ${balance:.2f}",
        "insufficient_balance": "⚠️ Saldo insuficiente: ${balance:.2f}",
        "profit": "📈 Beneficio: ${profit:.2f} ({percent:.1f}%)",
        # Paginación
        "pagination_status": "📄 Página {current} de {total}",
        "next_page": "➡️ Siguiente",
        "previous_page": "⬅️ Anterior",
    },
    # Deutsch
    "de": {
        # Allgemeine Strings
        "welcome": "Hallo, {user}! 👋\n\nIch bin ein DMarket-Arbitrage-Bot. Ich helfe dir, profitable Deals zu finden.\n\nVerwende das Menü, um die gewünschte Operation auszuwählen:",
        "help": "Verfügbare Befehle:\n\n/start - Bot starten\n/arbitrage - Arbitrage-Menü öffnen\n/dmarket - DMarket API-Status prüfen\n/settings - Profileinstellungen\n/help - Diese Hilfe anzeigen",
        "select_mode": "📊 Wähle den Arbitrage-Modus:",
        "checking_api": "🔍 Prüfe DMarket API-Status...",
        "api_ok": "✅ API funktioniert normal.\n\n🕒 Letzte Aktualisierung: gerade eben",
        "api_error": "❌ DMarket API-Fehler: {error}",
        "back_button": "⬅️ Zurück",
        "back_to_menu": "⬅️ Zurück zum Menü",
        # Einstellungen
        "settings": "⚙️ Profileinstellungen",
        "language": "🌐 Aktuelle Sprache: {lang}\n\nWähle die Oberflächensprache:",
        "language_set": "✅ Sprache eingestellt auf: {lang}",
        "api_settings": "🔑 DMarket API-Einstellungen",
        "api_key_prompt": "Gib deinen öffentlichen DMarket API-Schlüssel ein:",
        "api_secret_prompt": "Gib deinen geheimen DMarket API-Schlüssel ein:",
        "api_keys_set": "✅ API-Schlüssel wurden eingestellt. Du kannst jetzt alle Bot-Funktionen nutzen.",
        "trade_settings": "💼 Handelseinstellungen",
        "auto_trading_on": "✅ Automatischer Handel ist AKTIVIERT",
        "auto_trading_off": "❌ Automatischer Handel ist DEAKTIVIERT",
        # Arbitrage
        "arbitrage_boost": "🚀 Guthaben-Booster",
        "arbitrage_mid": "💼 Mittlerer Händler",
        "arbitrage_pro": "💰 Handels-Profi",
        "best_opportunities": "🌟 Beste Gelegenheiten",
        "auto_arbitrage": "🤖 Auto-Arbitrage",
        "select_game": "🎮 Spiel auswählen",
        "game_selected": "🎮 Ausgewähltes Spiel: {game}",
        # Auto-Arbitrage
        "auto_low": "💰 Minimaler Gewinn",
        "auto_medium": "💰💰 Mittlerer Gewinn",
        "auto_high": "💰💰💰 Hoher Gewinn",
        "auto_stats": "📊 Statistiken",
        "auto_stop": "🛑 Stoppen",
        "auto_searching": "🔍 Suche nach automatischen Arbitrage-Möglichkeiten...",
        "auto_found": "✅ {count} Artikel für Arbitrage gefunden.",
        "auto_no_results": "ℹ️ Keine Arbitrage-Artikel gefunden.",
        "auto_processing": "⏳ Verarbeite und bereite für automatischen Handel vor...",
        "auto_insufficient_balance": "⚠️ Unzureichendes Guthaben für Handel.\n\nAktuelles Guthaben: ${balance:.2f}\nMinimum erforderlich: $1.00",
        "auto_completed": "✅ Arbitrage abgeschlossen!\n\nArtikel gefunden: {found}\nArtikel gekauft: {purchases}\nArtikel verkauft: {sales}\nGesamtgewinn: ${profit:.2f}",
        # Fehler
        "error_general": "❌ Ein Fehler ist aufgetreten: {error}",
        "error_api_keys": "❌ Fehler: DMarket API-Schlüssel sind nicht konfiguriert.\n\nUm automatische Arbitrage zu nutzen, musst du DMarket API-Schlüssel mit dem Befehl /setup einrichten.",
        "try_again": "🔄 Erneut versuchen",
        # Risiko und Liquidität
        "risk_low": "niedrig",
        "risk_medium": "mittel",
        "risk_high": "hoch",
        "liquidity_low": "niedrig",
        "liquidity_medium": "mittel",
        "liquidity_high": "hoch",
        # Finanzen
        "balance": "💰 Guthaben: ${balance:.2f}",
        "insufficient_balance": "⚠️ Unzureichendes Guthaben: ${balance:.2f}",
        "profit": "📈 Gewinn: ${profit:.2f} ({percent:.1f}%)",
        # Paginierung
        "pagination_status": "📄 Seite {current} von {total}",
        "next_page": "➡️ Weiter",
        "previous_page": "⬅️ Zurück",
    },
}
