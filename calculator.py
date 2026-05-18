from models import CalculationResult


def calculate_local(unit_cost, unit_sell, qty, use_exchange, exchange_rate, fee_rate, buy_currency=None, sell_currency=None, my_currency=None):
    net_rate = 1.0 - fee_rate
    unit_net = unit_sell * net_rate

    total_cost_buy = unit_cost * qty
    
    if use_exchange:
        total_cost = total_cost_buy * exchange_rate
    else:
        total_cost = total_cost_buy

    total_net = unit_net * qty
    total_steam_sell = unit_sell * qty
    ratio = (total_cost / total_net) if total_net > 0 else 0.0
    discount = (1.0 - ratio) if total_net > 0 else 0.0

    if use_exchange:
        need_sell = (unit_cost * exchange_rate / net_rate) if net_rate > 0 else 0.0
    else:
        need_sell = (unit_cost / net_rate) if net_rate > 0 else 0.0
    
    total_cost_in_my = total_cost_buy
    total_net_in_my = total_net
    total_steam_sell_in_my = total_steam_sell
    
    if use_exchange and my_currency:
        if my_currency == buy_currency:
            total_net_in_my = total_net / exchange_rate
            total_steam_sell_in_my = total_steam_sell / exchange_rate
        elif my_currency == sell_currency:
            pass
        else:
            total_net_in_my = total_net
            total_steam_sell_in_my = total_steam_sell

    return CalculationResult(
        unit_net=unit_net,
        total_cost=total_cost,
        total_net=total_net,
        ratio=ratio,
        discount=discount,
        need_sell=need_sell
    )


def calculate_reverse_quantity(target_amount, unit_sell, fee_rate):
    net_rate = 1.0 - fee_rate
    required_qty = int(target_amount / (unit_sell * net_rate)) if unit_sell * net_rate > 0 else 0
    return required_qty


def calculate_break_even_price(unit_cost, fee_rate):
    net_rate = 1.0 - fee_rate
    break_even_price = unit_cost / net_rate if net_rate > 0 else 0.0
    return break_even_price


def calculate_required_cost(target_amount, unit_sell, fee_rate, exchange_rate=1.0, use_exchange=False):
    net_rate = 1.0 - fee_rate
    required_cost = (target_amount / net_rate) / exchange_rate if use_exchange else (target_amount / net_rate)
    return required_cost