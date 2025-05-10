import traceback
from os import getenv

from dotenv import load_dotenv
from telegram import ChatAction, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from src.telegram_bot.profiles import get_user_profile
from src.telegram_bot.settings_handlers import get_localized_text
from src.utils.api_error_handling import APIError

# Загружаем переменные окружения
load_dotenv()


async def dmarket_status_impl(
    update: Update, context: CallbackContext, status_message=None
) -> None:
    """Реализация проверки статуса DMarket API.

    Args:
        update (Update): Объект обновления Telegram
        context (CallbackContext): Контекст обработчика
        status_message: Сообщение для обновления статуса (опционально)

    """
    # Получаем пользователя и его профиль
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)

    # Отправляем индикатор печатания, если сообщение статуса не предоставлено
    if not status_message:
        await update.effective_chat.send_action(ChatAction.TYPING)
        checking_msg = get_localized_text(user_id, "checking_api")
        status_message = await update.message.reply_text(checking_msg)

    try:
        # Отображаем индикатор загрузки данных
        await update.effective_chat.send_action(ChatAction.UPLOAD_DOCUMENT)

        import httpx

        from src.dmarket.dmarket_api import DMarketAPI
        from src.telegram_bot.auto_arbitrage_scanner import check_user_balance

        # Получаем API ключи из профиля пользователя или из переменных окружения
        public_key = profile.get("api_key", "")
        secret_key = profile.get("api_secret", "")
        auth_source = ""
        if not public_key or not secret_key:
            # При отсутствии ключей в профиле, пробуем переменные окружения
            public_key = getenv("DMARKET_PUBLIC_KEY", "")
            secret_key = getenv("DMARKET_SECRET_KEY", "")
            auth_source = " <i>(из переменных окружения)</i>"

        auth_status = "❌ <b>Авторизация</b>: ключи API не настроены"
        if public_key and secret_key:
            auth_status = f"✅ <b>Авторизация</b>: настроена{auth_source}"

        api_client = DMarketAPI(
            public_key=public_key,
            secret_key=secret_key,
            pool_limits=httpx.Limits(max_connections=5),
        )

        api_status = "Неизвестно"
        balance_info = ""

        try:
            # Показываем, что мы работаем с API
            await update.effective_chat.send_action(ChatAction.TYPING)

            # Получаем баланс через улучшенную функцию
            balance_data = await check_user_balance(api_client)

            # Проверка на наличие ошибки
            if balance_data.get("error", False):
                api_status = "⚠️ <b>API</b>: проблема с доступом"
                error_message = balance_data.get("error_message", "Неизвестная ошибка")

                if "unauthorized" in error_message.lower() or "token" in error_message.lower():
                    auth_status = "❌ <b>Авторизация</b>: ошибка авторизации"
                    balance_info = "<i>Не удалось получить баланс: проверьте ключи API.</i>"
                else:
                    balance_info = f"<i>Ошибка при запросе баланса:</i> {error_message}"
            else:
                has_funds = balance_data.get("has_funds", False)
                balance = balance_data.get("balance", 0.0)

                api_status = "✅ <b>API доступно</b>"

                if public_key and secret_key:
                    # Форматируем баланс для отображения пользователю
                    if balance > 0:
                        balance_status = "✅"
                    else:
                        balance_status = "⚠️"
                    balance_info = (
                        f"{balance_status} <b>Баланс</b>: <code>${balance:.2f} USD</code>"
                    )
                else:
                    balance_info = "<i>Баланс недоступен без API ключей.</i>"

        except APIError as e:
            api_status = f"⚠️ <b>Ошибка API</b>: {e.message}"
            if e.status_code == 401:
                auth_status = "❌ <b>Ошибка авторизации</b>: неверные ключи API"
            balance_info = "<i>Не удалось проверить баланс.</i>"

        except Exception as e:
            api_status = f"❌ <b>Ошибка соединения</b>: {e!s}"
            balance_info = "<i>Не удалось проверить баланс.</i>"

        finally:
            # Закрываем клиент после использования
            await api_client._close_client()

        # Добавляем информацию для устранения проблем
        troubleshooting = ""
        if "ошибка авторизации" in auth_status.lower() or "❌" in auth_status:
            troubleshooting = (
                "\n\n🔧 <b>Для устранения проблемы:</b>\n"
                "1. Проверьте корректность API ключей\n"
                "2. Убедитесь, что ключи не истекли\n"
                "3. Создайте новые ключи API на DMarket, если необходимо"
            )

        status_message = (
            f"{api_status}\n"
            f"{auth_status}\n"
            f"{balance_info}{troubleshooting}\n\n"
            f"🕒 <i>Последнее обновление: только что</i>"
        )

        # Показываем финальное сообщение с форматированием HTML
        await status_message.edit_text(
            status_message,
            parse_mode=ParseMode.HTML,
        )

    except Exception as e:
        error_traceback = traceback.format_exc()
        await status_message.edit_text(
            "❌ <b>Произошла критическая ошибка при проверке статуса DMarket API.</b>\n\n"
            f"<i>Ошибка:</i> <code>{e!s}</code>\n\n"
            "🕒 <i>Последнее обновление: только что</i>",
            parse_mode=ParseMode.HTML,
        )
