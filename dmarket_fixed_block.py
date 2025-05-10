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