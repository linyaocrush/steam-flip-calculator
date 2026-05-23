import flet as ft
from decimal import Decimal, ROUND_HALF_UP
from typing import NamedTuple, Callable
from utils import money_decimal, pct_decimal, safe_float, safe_decimal, safe_int, Debouncer
from services.calculator import calculate_local
from ui.glassmorphism import create_glass_card, get_glassmorphism_style
from state.app_state import app_state


class CalculatorView(NamedTuple):
    view: ft.Container
    recalc: Callable
    tf_cost: ft.TextField
    tf_steam_sell: ft.TextField
    refresh_language: Callable


def _get_my_currency_amounts(total_cost_buy: Decimal, total_net: Decimal, total_steam_sell: Decimal,
                              buy_currency: str, sell_currency: str, my_currency: str,
                              exchange_rate: float):
    """Convert amounts to 'my currency'. Returns (cost_in_my, net_in_my, sell_in_my).

    Pure math — no I/O. For cases where my_currency differs from both buy and sell,
    returns unconverted sell-currency values (caller should pre-convert if needed).
    """
    if not my_currency or buy_currency == sell_currency:
        return total_cost_buy, total_net, total_steam_sell

    if my_currency == buy_currency:
        rate = Decimal(str(exchange_rate))
        net_in_my = (total_net / rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        sell_in_my = (total_steam_sell / rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return total_cost_buy, net_in_my, sell_in_my

    if my_currency == sell_currency:
        rate = Decimal(str(exchange_rate))
        cost_in_my = (total_cost_buy * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return cost_in_my, total_net, total_steam_sell

    # my_currency differs from both — can't convert without extra rates
    return total_cost_buy, total_net, total_steam_sell


def create_calculator_view(settings, on_add_to_history, t, page):
    is_dark = True

    _recalc_debouncer = Debouncer(200)

    def _debounced_recalc():
        recalc()
        page.update()

    def _debounced_calc_target():
        calc_target_qty()
        page.update()

    tf_item = ft.TextField(
        label=t("item_name"), 
        value=settings.last_item_name or "CS2 刀/皮肤", 
        expand=True,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    tf_note = ft.TextField(
        label=t("note"), 
        expand=True,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )

    tf_cost = ft.TextField(
        label=t("cost"),
        value=str(settings.last_unit_cost) if settings.last_unit_cost else "70",
        prefix=ft.Text(settings.buy_currency_symbol),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    tf_steam_sell = ft.TextField(
        label=t("steam_sell"),
        value=str(settings.last_unit_sell) if settings.last_unit_sell else "100",
        prefix=ft.Text(settings.sell_currency_symbol),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    tf_qty = ft.TextField(
        label=t("quantity"),
        value="1",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=120,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )

    out_unit_net = ft.Text(value="-")
    out_total_cost = ft.Text(value="-")
    out_total_net = ft.Text(value="-")
    out_ratio = ft.Text(value="-")
    out_discount = ft.Text(value="-")
    out_need_sell = ft.Text(value="-")

    tf_target_amount = ft.TextField(
        label=t("target_amount"),
        value="",
        prefix=ft.Text(settings.sell_currency_symbol),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        hint_text=t("target_amount_desc"),
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    
    out_required_qty = ft.Text(value="-")
    out_required_cost = ft.Text(value="-")

    # Cache for last calculation result to avoid redundant calculate_local() in on_add
    _last_calc_result = None
    _last_calc_inputs = None

    # Translatable label controls
    txt_result_title = ft.Text(t("result_title"), size=16, weight=ft.FontWeight.W_600)
    txt_target_title = ft.Text(t("target_title"), size=16, weight=ft.FontWeight.W_600)
    txt_reverse_title = ft.Text(t("reverse_title"), size=16, weight=ft.FontWeight.W_600)

    txt_unit_net_label = ft.Text(t("unit_net"), size=12, width=100)
    txt_total_cost_label = ft.Text(t("total_cost"), size=12, width=100)
    txt_total_net_label = ft.Text(t("total_net"), size=12, width=100)
    txt_ratio_label = ft.Text(t("flip_ratio"), size=12, width=100)
    txt_discount_label = ft.Text(t("discount"), size=12, width=100)

    txt_required_qty_label = ft.Text(t("required_qty"), size=12, width=100)
    txt_required_cost_label = ft.Text(t("required_cost"), size=12, width=100)

    txt_fee_label = ft.Text(t("steam_fee", fee=app_state.get_settings().steam_fee_rate * 100), size=12)
    txt_break_even_label = ft.Text(t("break_even_price"), size=12, width=100)

    def format_price(amount: Decimal, currency_symbol, currency_code):
        current_settings = app_state.get_settings()
        my_currency = current_settings.my_currency
        my_symbol = current_settings.my_currency_symbol

        if currency_code == my_currency:
            return f"{currency_symbol} {money_decimal(amount)}"

        exchange_rate = Decimal(str(current_settings.exchange_rate))
        if current_settings.buy_currency == my_currency:
            converted = amount / exchange_rate
        else:
            converted = amount * exchange_rate

        return f"{currency_symbol} {money_decimal(amount)} ({my_symbol} {money_decimal(converted)})"

    def format_cost(amount_in_sell_currency: Decimal):
        """
        成本类金额（总花费/需要花费）优先按"我的货币"显示：
        - 若 buy_currency == my_currency：直接显示 my_currency（不再显示 sell_currency + 括号）
        - 否则：沿用原来的 format_price 逻辑（卖出币种为主，括号里我的币种）
        """
        current_settings = app_state.get_settings()
        my_currency = current_settings.my_currency
        my_symbol = current_settings.my_currency_symbol

        if current_settings.buy_currency == my_currency:
            if current_settings.buy_currency != current_settings.sell_currency:
                exchange_rate = Decimal(str(current_settings.exchange_rate))
                amount_in_my = amount_in_sell_currency / exchange_rate
            else:
                amount_in_my = amount_in_sell_currency
            return f"{current_settings.buy_currency_symbol} {money_decimal(amount_in_my)}"

        return format_price(amount_in_sell_currency, current_settings.buy_currency_symbol, current_settings.buy_currency)

    def recalc(_=None):
        nonlocal _last_calc_result, _last_calc_inputs
        current_settings = app_state.get_settings()
        unit_cost = safe_float(tf_cost.value)
        unit_sell = safe_float(tf_steam_sell.value)
        qty = safe_int(tf_qty.value)

        use_exchange = current_settings.buy_currency != current_settings.sell_currency

        data = calculate_local(
            unit_cost,
            unit_sell,
            qty,
            use_exchange,
            current_settings.exchange_rate,
            current_settings.steam_fee_rate,
        )
        _last_calc_result = data
        _last_calc_inputs = (safe_decimal(tf_cost.value), safe_decimal(tf_steam_sell.value), safe_int(tf_qty.value))

        out_unit_net.value = format_price(data.unit_net, current_settings.sell_currency_symbol, current_settings.sell_currency)
        out_total_cost.value = format_cost(data.total_cost)
        out_total_net.value = format_price(data.total_net, current_settings.sell_currency_symbol, current_settings.sell_currency)
        out_ratio.value = f"{pct_decimal(data.ratio)} ({t('ratio_desc')})"
        out_discount.value = f"{data.discount:,.2f}%"
        out_need_sell.value = f"{format_price(data.need_sell, current_settings.sell_currency_symbol, current_settings.sell_currency)} ({t('unit')})"

        calc_target_qty()
        return True

    def calc_target_qty(_=None):
        current_settings = app_state.get_settings()
        target_amount = safe_float(tf_target_amount.value)
        unit_cost = safe_float(tf_cost.value)
        unit_sell = safe_float(tf_steam_sell.value)

        if target_amount <= 0 or unit_sell <= 0:
            out_required_qty.value = "-"
            out_required_cost.value = "-"
            return

        net_rate = 1.0 - current_settings.steam_fee_rate
        unit_net = unit_sell * net_rate
        required_qty = int((target_amount / unit_net) + 0.999)
        required_cost = unit_cost * required_qty

        use_exchange = current_settings.buy_currency != current_settings.sell_currency
        if use_exchange:
            required_cost_display = required_cost * current_settings.exchange_rate
        else:
            required_cost_display = required_cost

        out_required_qty.value = str(required_qty)
        out_required_cost.value = format_cost(Decimal(str(required_cost_display)))

    def on_add(_):
        current_settings = app_state.get_settings()
        item_name = (tf_item.value or "").strip()
        if not item_name:
            return

        unit_cost = safe_decimal(tf_cost.value)
        unit_steam_sell = safe_decimal(tf_steam_sell.value)
        qty = safe_int(tf_qty.value)
        note = (tf_note.value or "").strip()

        if unit_cost <= 0 or unit_steam_sell <= 0:
            return

        current_inputs = (unit_cost, unit_steam_sell, qty)
        if _last_calc_inputs == current_inputs and _last_calc_result is not None:
            data = _last_calc_result
        else:
            use_exchange = current_settings.buy_currency != current_settings.sell_currency
            data = calculate_local(
                unit_cost,
                unit_steam_sell,
                qty,
                use_exchange,
                current_settings.exchange_rate,
                current_settings.steam_fee_rate,
            )

        cost_in_my, net_in_my, sell_in_my = _get_my_currency_amounts(
            data.total_cost_buy, data.total_net, data.total_cost + data.total_net,
            current_settings.buy_currency, current_settings.sell_currency,
            current_settings.my_currency, current_settings.exchange_rate,
        )

        record_data = {
            "item_name": item_name,
            "note": note,
            "unit_cost": unit_cost,
            "unit_steam_sell": unit_steam_sell,
            "qty": qty,
            "discount": data.discount,
            "unit_net": data.unit_net,
            "total_cost": data.total_cost_buy,
            "total_net": data.total_net,
            "total_steam_sell": data.total_cost + data.total_net,
            "total_cost_in_my_currency": cost_in_my,
            "total_net_in_my_currency": net_in_my,
            "total_steam_sell_in_my_currency": sell_in_my,
            "ratio": data.ratio,
        }

        current_settings.last_item_name = item_name
        current_settings.last_unit_cost = safe_float(tf_cost.value)
        current_settings.last_unit_sell = safe_float(tf_steam_sell.value)
        from services.database import save_settings
        save_settings(current_settings)

        on_add_to_history(tf_item, tf_note, tf_cost, tf_steam_sell, tf_qty, record_data)

    tf_cost.on_change = lambda _: _recalc_debouncer(_debounced_recalc)
    tf_steam_sell.on_change = lambda _: _recalc_debouncer(_debounced_recalc)
    tf_qty.on_change = lambda _: _recalc_debouncer(_debounced_recalc)
    tf_target_amount.on_change = lambda _: _recalc_debouncer(_debounced_calc_target)

    def on_settings_changed(new_settings):
        tf_cost.prefix = ft.Text(new_settings.buy_currency_symbol)
        tf_steam_sell.prefix = ft.Text(new_settings.sell_currency_symbol)
        tf_target_amount.prefix = ft.Text(new_settings.sell_currency_symbol)
        recalc()

    app_state.subscribe(on_settings_changed)

    btn_add_to_history = ft.FilledButton(
        t("add_to_history"),
        icon=ft.Icons.ADD_OUTLINED,
        on_click=on_add,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.INDIGO),
            color=ft.Colors.WHITE,
            padding=14,
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )

    calc_card = ft.Container(
        padding=20,
        border_radius=18,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border=ft.BorderSide(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
        shadow=ft.BoxShadow(
            blur_radius=30,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
            offset=ft.Offset(0, 10),
        ),
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Row(
                    spacing=14,
                    controls=[
                        tf_item,
                        tf_note,
                    ],
                ),
                ft.Row(
                    spacing=14,
                    controls=[
                        tf_cost,
                        tf_steam_sell,
                        tf_qty,
                    ],
                ),
                ft.Container(height=1, bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.SURFACE)),
                ft.Row(
                    spacing=16,
                    expand=True,
                    controls=[
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    txt_result_title,
                                    ft.Column(
                                        spacing=6,
                                        controls=[
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    txt_unit_net_label,
                                                    out_unit_net,
                                                ],
                                            ),
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    txt_total_cost_label,
                                                    out_total_cost,
                                                ],
                                            ),
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    txt_total_net_label,
                                                    out_total_net,
                                                ],
                                            ),
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    txt_ratio_label,
                                                    out_ratio,
                                                ],
                                            ),
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    txt_discount_label,
                                                    out_discount,
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    txt_target_title,
                                    tf_target_amount,
                                    ft.Column(
                                        spacing=6,
                                        controls=[
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    txt_required_qty_label,
                                                    out_required_qty,
                                                ],
                                            ),
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    txt_required_cost_label,
                                                    out_required_cost,
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    txt_reverse_title,
                                    ft.Column(
                                        spacing=6,
                                        controls=[
                                            txt_fee_label,
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    txt_break_even_label,
                                                    out_need_sell,
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    controls=[
                        btn_add_to_history,
                    ],
                ),
            ],
        ),
    )

    def refresh_language(t):
        tf_item.label = t("item_name")
        tf_note.label = t("note")
        tf_cost.label = t("cost")
        tf_steam_sell.label = t("steam_sell")
        tf_qty.label = t("quantity")
        tf_target_amount.label = t("target_amount")
        tf_target_amount.hint_text = t("target_amount_desc")

        txt_result_title.value = t("result_title")
        txt_target_title.value = t("target_title")
        txt_reverse_title.value = t("reverse_title")

        txt_unit_net_label.value = t("unit_net")
        txt_total_cost_label.value = t("total_cost")
        txt_total_net_label.value = t("total_net")
        txt_ratio_label.value = t("flip_ratio")
        txt_discount_label.value = t("discount")

        txt_required_qty_label.value = t("required_qty")
        txt_required_cost_label.value = t("required_cost")

        current_settings = app_state.get_settings()
        txt_fee_label.value = t("steam_fee", fee=current_settings.steam_fee_rate * 100)
        txt_break_even_label.value = t("break_even_price")

        btn_add_to_history.text = t("add_to_history")
        recalc()

    return CalculatorView(
        view=calc_card,
        recalc=recalc,
        tf_cost=tf_cost,
        tf_steam_sell=tf_steam_sell,
        refresh_language=refresh_language,
    )