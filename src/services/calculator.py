from decimal import Decimal, ROUND_HALF_UP, getcontext
from models import CalculationResult
from services.exchange_rate import fetch_exchange_rate

getcontext().prec = 28

def calculate_local(unit_cost, unit_sell, qty, use_exchange, exchange_rate, fee_rate, buy_currency=None, sell_currency=None, my_currency=None):
    unit_cost = Decimal(str(unit_cost))
    unit_sell = Decimal(str(unit_sell))
    qty = Decimal(str(qty))
    exchange_rate = Decimal(str(exchange_rate))
    fee_rate = Decimal(str(fee_rate))
    
    net_rate = (Decimal('1') - fee_rate).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    unit_net = (unit_sell * net_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    total_cost_buy = (unit_cost * qty).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    if use_exchange:
        total_cost = (total_cost_buy * exchange_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        total_cost = total_cost_buy

    total_net = (unit_net * qty).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_steam_sell = (unit_sell * qty).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    if total_net > 0:
        ratio = (total_cost / total_net).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        discount = ((Decimal('1') - ratio) * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        ratio = Decimal('0')
        discount = Decimal('0')

    if use_exchange:
        if net_rate > 0:
            need_sell = ((unit_cost * exchange_rate) / net_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            need_sell = Decimal('0')
    else:
        if net_rate > 0:
            need_sell = (unit_cost / net_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            need_sell = Decimal('0')
    
    total_cost_in_my = total_cost_buy
    total_net_in_my = total_net
    total_steam_sell_in_my = total_steam_sell
    
    if my_currency and use_exchange:
        if my_currency == buy_currency:
            total_net_in_my = (total_net / exchange_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_steam_sell_in_my = (total_steam_sell / exchange_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif my_currency == sell_currency:
            total_cost_in_my = (total_cost_buy * exchange_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            buy_to_my_rate, _, _ = fetch_exchange_rate(buy_currency, my_currency)
            sell_to_my_rate, _, _ = fetch_exchange_rate(sell_currency, my_currency)
            
            buy_to_my_rate = Decimal(str(buy_to_my_rate))
            sell_to_my_rate = Decimal(str(sell_to_my_rate))
            
            total_cost_in_my = (total_cost_buy * buy_to_my_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_net_in_my = (total_net * sell_to_my_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_steam_sell_in_my = (total_steam_sell * sell_to_my_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return CalculationResult(
        unit_net=float(unit_net),
        total_cost=float(total_cost),
        total_cost_buy=float(total_cost_buy),
        total_net=float(total_net),
        ratio=float(ratio),
        discount=float(discount),
        need_sell=float(need_sell),
        total_cost_in_my_currency=float(total_cost_in_my),
        total_net_in_my_currency=float(total_net_in_my),
        total_steam_sell_in_my_currency=float(total_steam_sell_in_my)
    )


def calculate_reverse_quantity(target_amount, unit_sell, fee_rate):
    target_amount = Decimal(str(target_amount))
    unit_sell = Decimal(str(unit_sell))
    fee_rate = Decimal(str(fee_rate))
    
    net_rate = (Decimal('1') - fee_rate).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    denominator = (unit_sell * net_rate).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    if denominator > 0:
        required_qty = int((target_amount / denominator).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    else:
        required_qty = 0
    return required_qty


def calculate_break_even_price(unit_cost, fee_rate):
    unit_cost = Decimal(str(unit_cost))
    fee_rate = Decimal(str(fee_rate))
    
    net_rate = (Decimal('1') - fee_rate).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    if net_rate > 0:
        break_even_price = (unit_cost / net_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        break_even_price = Decimal('0')
    return float(break_even_price)


def calculate_required_cost(target_amount, unit_sell, fee_rate, exchange_rate=1.0, use_exchange=False):
    target_amount = Decimal(str(target_amount))
    unit_sell = Decimal(str(unit_sell))
    fee_rate = Decimal(str(fee_rate))
    exchange_rate = Decimal(str(exchange_rate))
    
    net_rate = (Decimal('1') - fee_rate).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    if net_rate > 0:
        if use_exchange:
            required_cost = ((target_amount / net_rate) / exchange_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            required_cost = (target_amount / net_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        required_cost = Decimal('0')
    return float(required_cost)