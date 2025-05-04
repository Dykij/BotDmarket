import traceback
import os
from telegram import Update
from telegram.ext import CallbackContext
from src.telegram_bot.profiles import get_user_profile
from src.telegram_bot.settings_handlers import get_localized_text
from src.utils.api_error_handling import APIError

async def dmarket_status_impl(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    checking_msg = get_localized_text(user_id, "checking_api")
    message = await update.message.reply_text(checking_msg)
    try:
        import httpx
        from src.dmarket.dmarket_api import DMarketAPI
        from src.utils.rate_limiter import RateLimiter
        from src.telegram_bot.auto_arbitrage_scanner import check_user_balance
        public_key = profile.get("api_key", "")
        secret_key = profile.get("api_secret", "")
        auth_source = ""
        if not public_key or not secret_key:
            public_key = os.environ.get("DMARKET_PUBLIC_KEY", "")
            secret_key = os.environ.get("DMARKET_SECRET_KEY", "")
            if public_key and secret_key:
                auth_source = " (из окружения)"
        else:
            auth_source = " (из профиля)"
        auth_status = "❌ Авторизация: ключи API не настроены"
        if public_key and secret_key:
            auth_status = f"✅ Авторизация: настроена{auth_source}"
        api_client = DMarketAPI(
            public_key=public_key,
            secret_key=secret_key,
            pool_limits=httpx.Limits(max_connections=5)
        )
        api_status = "Неизвестно"
        balance_info = ""
        try:
            has_funds, balance = await check_user_balance(api_client)
            api_status = "✅ API доступно"
            if public_key and secret_key:
                if has_funds is not None:
                    balance_info = get_localized_text(user_id, "balance", balance=balance)
                else:
                    auth_status = "⚠️ Ошибка авторизации: проверьте ключи API"
                    balance_info = "Не удалось получить баланс."
            else:
                balance_info = "Баланс недоступен без API ключей."
        except APIError as e:
            api_status = f"⚠️ Ошибка API: {e.message}"
            if e.status_code == 401:
                auth_status = "❌ Ошибка авторизации: неверные ключи API"
            balance_info = "Не удалось проверить баланс."
        except Exception as e:
            api_status = f"❌ Ошибка соединения: {str(e)}"
            balance_info = "Не удалось проверить баланс."
        finally:
            await api_client._close_client()
        status_message = (
            f"{api_status}\n"
            f"{auth_status}\n"
            f"{balance_info}\n\n"
            f"🕒 Последнее обновление: только что"
        )
        await message.edit_text(status_message)
    except Exception as e:
        error_traceback = traceback.format_exc()
        await message.edit_text(
            "❌ Произошла критическая ошибка при проверке статуса DMarket API.\n\n"
            f"Ошибка: {str(e)}\n\n"
            "🕒 Последнее обновление: только что"
        )
