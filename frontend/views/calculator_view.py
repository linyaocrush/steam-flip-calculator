import flet as ft
from utils import money, pct, safe_float, safe_int
from calculator import calculate_local


def create_calculator_view(settings, on_add_to_history, t):
    tf_item = ft.TextField(label=t("item_name"), value="CS2 刀/皮肤", expand=True)
    tf_note = ft.TextField(label=t("note"), expand=True)

    tf_cost = ft.TextField(
        label=t("cost"),
        value="70",
        prefix=ft.Text(settings["buy_currency_symbol"]),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )
    tf_steam_sell = ft.TextField(
        label=t("steam_sell"),
        value="100",
        prefix=ft.Text(settings["sell_currency_symbol"]),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )
    tf_qty = ft.TextField(
        label=t("quantity"),
        value="1",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=120,
    )

    out_unit_net = ft.Text(value="-")
    out_total_cost = ft.Text(value="-")
    out_total_net = ft.Text(value="-")
    out_ratio = ft.Text(value="-")
    out_discount = ft.Text(value="-")
    out_need_sell = ft.Text(value="-")

    def format_price(amount, currency_symbol, currency_code):
        my_currency = settings.get("my_currency", "CNY")
        my_symbol = settings.get("my_currency_symbol", "¥")
        
        if currency_code == my_currency:
            return f"{currency_symbol} {money(amount)}"
        
        exchange_rate = settings.get("exchange_rate", 1.0)
        if settings["buy_currency"] == my_currency:
            converted = amount / exchange_rate
        else:
            converted = amount * exchange_rate
        
        return f"{currency_symbol} {money(amount)} ({my_symbol} {money(converted)})"

    def recalc(_=None):
        unit_cost = safe_float(tf_cost.value)
        unit_sell = safe_float(tf_steam_sell.value)
        qty = safe_int(tf_qty.value)

        use_exchange = settings["buy_currency"] != settings["sell_currency"]

        data = calculate_local(
            unit_cost,
            unit_sell,
            qty,
            use_exchange,
            settings["exchange_rate"],
            settings["steam_fee_rate"],
        )

        out_unit_net.value = format_price(data['unit_net'], settings['sell_currency_symbol'], settings['sell_currency'])
        out_total_cost.value = format_price(data['total_cost'], settings['sell_currency_symbol'], settings['sell_currency'])
        out_total_net.value = format_price(data['total_net'], settings['sell_currency_symbol'], settings['sell_currency'])
        out_ratio.value = f"{pct(data['ratio'])} ({t('ratio_desc')})"
        out_discount.value = f"{pct(data['discount'])}"
        out_need_sell.value = f"{format_price(data['need_sell'], settings['sell_currency_symbol'], settings['sell_currency'])} ({t('unit')})"
        return True

    for t_field in (tf_cost, tf_steam_sell, tf_qty):
        t_field.on_change = recalc

    def kv_row(k: str, v: ft.Control):
        return ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(k), v])

    fee_percent = settings["steam_fee_rate"] * 100
    reverse_box = ft.Container(
        width=340,
        padding=14,
        border_radius=14,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Text(t("reverse_title"), size=14, weight=ft.FontWeight.W_600),
                ft.Text(t("steam_fee", fee=fee_percent), size=12, opacity=0.8),
                kv_row(t("break_even_price"), out_need_sell),
                ft.FilledButton(t("add_to_history"), icon=ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda _: on_add_to_history(tf_item, tf_note, tf_cost, tf_steam_sell, tf_qty)),
            ],
        ),
    )

    calc_result_box = ft.Container(
        expand=True,
        padding=14,
        border_radius=14,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text(t("result_title"), size=14, weight=ft.FontWeight.W_600),
                kv_row(t("unit_net"), out_unit_net),
                kv_row(t("total_cost"), out_total_cost),
                kv_row(t("total_net"), out_total_net),
                kv_row(t("flip_ratio"), out_ratio),
                kv_row(t("discount"), out_discount),
            ],
        ),
    )

    calc_card = ft.Card(
        elevation=1,
        content=ft.Container(
            padding=18,
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row([tf_item, tf_note], spacing=12),
                    ft.Row([tf_cost, tf_steam_sell, tf_qty], spacing=12),
                    ft.Divider(height=1),
                    ft.Row([calc_result_box, reverse_box], spacing=14),
                ],
            ),
        ),
    )

    return {
        "view": calc_card,
        "recalc": recalc,
        "tf_cost": tf_cost,
        "tf_steam_sell": tf_steam_sell,
        "reverse_box": reverse_box,
    }