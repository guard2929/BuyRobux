from decimal import Decimal

def calculate_gamepass_robux(robux_amount, has_promo=False):
    """
    Рассчитывает количество Robux, которое нужно установить в GamePass.
    Учитывает 30% комиссию Roblox (создатели получают 70%).
    Если используется промокод, возвращает увеличенное значение.
    """
    if has_promo:
        return int(Decimal(str(robux_amount)) / Decimal('0.7'))
    return robux_amount