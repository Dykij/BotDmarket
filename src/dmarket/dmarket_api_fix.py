"""
Фрагменты класса DMarketAPI для исправления синтаксических ошибок.
"""

# Фрагмент 1: Правильный отступ для блока try с await self._request
                try:
                    logger.info(f"Пробуем получить баланс через эндпоинт {endpoint}")
                    response = await self._request(
                        "GET",
                        endpoint,
                    )
                    
                    if response and isinstance(response, dict) and not ("error" in response or "code" in response):
                        logger.info(f"Успешно получили баланс через {endpoint}")
                        successful_endpoint = endpoint
                        break
                        
                except Exception as e:
                    last_error = e
                    logger.warning(f"Ошибка при запросе {endpoint}: {str(e)}")
                    continue

# Фрагмент 2: Правильный отступ для проверки "usd" в response
                # Формат 1: DMarket API 2023+ с usdAvailableToWithdraw и usd
                elif "usdAvailableToWithdraw" in response:
                    try:
                        usd_value = response["usdAvailableToWithdraw"]
                        if isinstance(usd_value, str):
                            # Строка может быть в формате "5.00" или "$5.00"
                            usd_available = float(usd_value.replace('$', '').strip()) * 100
                        else:
                            usd_available = float(usd_value) * 100
                        
                        # Также проверяем общий баланс (если есть)
                        if "usd" in response:
                            usd_value = response["usd"]
                            if isinstance(usd_value, str):
                                usd_total = float(usd_value.replace('$', '').strip()) * 100
                            else:
                                usd_total = float(usd_value) * 100
                        else:
                            usd_total = usd_available
                            
                        # Используем доступный баланс как основной
                        usd_amount = usd_available
                        logger.info(f"Баланс из usdAvailableToWithdraw: {usd_amount/100:.2f} USD")
                        
                    except (ValueError, TypeError) as e:
                        logger.error(f"Ошибка при обработке поля usdAvailableToWithdraw: {e}")
                        # Продолжаем проверку других форматов 