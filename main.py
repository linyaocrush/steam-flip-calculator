import flet as ft
from config import DEFAULT_SETTINGS, CURRENCY_SYMBOLS
from utils import safe_float, safe_int
from i18n import get_text
from database import init_db, get_settings, save_settings, get_records, get_stats, add_record, clear_records
from exchange_rate import fetch_exchange_rate
from views import (
    create_calculator_view,
    create_history_view,
    create_stats_view,
    create_settings_view,
)
from glassmorphism import (
    create_gradient_background,
    create_floating_orbs,
    create_glass_card,
    create_glass_button,
    get_glassmorphism_style,
)


def main(page: ft.Page):
    page.title = "Steam 倒余额工具箱"
    page.window_width = 1040
    page.window_height = 760
    page.theme_mode = ft.ThemeMode.DARK

    page.theme = ft.Theme(
        use_material3=True,
        color_scheme_seed=ft.Colors.INDIGO,
        visual_density=ft.VisualDensity.COMFORTABLE,
    )

    init_db()
    
    settings = get_settings()
    page.theme_mode = ft.ThemeMode.DARK
    page.title = get_text("app_title", settings.language)

    page.bgcolor = ft.Colors.TRANSPARENT

    def get_t():
        lang = settings.language
        return lambda key, **kwargs: get_text(key, lang, **kwargs)

    t = get_t()

    snack = ft.SnackBar(content=ft.Text(""))
    page.snack_bar = snack

    def on_add_to_history(tf_item, tf_note, tf_cost, tf_steam_sell, tf_qty, record_data=None):
        item_name = (tf_item.value or "").strip()
        if not item_name:
            snack.content = ft.Text(t("error_empty_item"))
            snack.open = True
            page.update()
            return

        unit_cost = safe_float(tf_cost.value)
        unit_sell = safe_float(tf_steam_sell.value)
        qty = safe_int(tf_qty.value)
        note = (tf_note.value or "").strip()

        if unit_cost <= 0 or unit_sell <= 0:
            snack.content = ft.Text(t("error_invalid_price"))
            snack.open = True
            page.update()
            return

        payload = {
            "item_name": item_name,
            "note": note,
            "unit_cost": unit_cost,
            "unit_steam_sell": unit_sell,
            "qty": qty,
        }
        
        if record_data:
            payload.update({
                "discount": record_data.get("discount", 0.0),
                "unit_net": record_data.get("unit_net", 0.0),
                "total_cost": record_data.get("total_cost", 0.0),
                "total_net": record_data.get("total_net", 0.0),
                "total_steam_sell": record_data.get("total_steam_sell", 0.0),
                "total_cost_in_my_currency": record_data.get("total_cost_in_my_currency", 0.0),
                "total_net_in_my_currency": record_data.get("total_net_in_my_currency", 0.0),
                "total_steam_sell_in_my_currency": record_data.get("total_steam_sell_in_my_currency", 0.0),
            })

        success = add_record(payload)

        if success:
            snack.content = ft.Text(t("save_success"))
        else:
            snack.content = ft.Text(t("save_failed"))
        snack.open = True
        refresh_history()
        refresh_stats()
        page.update()

    calculator = create_calculator_view(settings, on_add_to_history, t)
    calc_card = calculator["view"]
    recalc = calculator["recalc"]
    tf_cost = calculator["tf_cost"]
    tf_steam_sell = calculator["tf_steam_sell"]

    history = create_history_view(settings, snack, t)
    dt = history["dt"]
    row_for_record = history["row_for_record"]

    def refresh_history():
        records = get_records()
        dt.rows = [row_for_record(r, refresh_history) for r in records]
        page.update()

    stats = create_stats_view(settings, t)
    stats_view = stats["view"]
    update_stats = stats["update_stats"]

    def refresh_stats():
        stats_data = get_stats()
        update_stats(stats_data)
        page.update()

    def refresh_history_and_stats():
        records = get_records()
        stats_data = get_stats()

        dt.rows = [row_for_record(r, refresh_history) for r in records]
        update_stats(stats_data)

        page.update()

    def clear_all(_):
        def yes(_):
            success = clear_records()
            if success:
                snack.content = ft.Text(t("clear_success"))
            else:
                snack.content = ft.Text(t("clear_failed"))
            snack.open = True
            refresh_history()
            refresh_stats()
            page.update()

        def no(_):
            page.dialog = None
            page.update()

        page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(t("confirm_clear")),
            content=ft.Text(t("confirm_clear_msg")),
            actions=[
                ft.TextButton(t("cancel"), on_click=no),
                ft.FilledButton(t("confirm"), on_click=yes)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        page.dialog.open = True
        page.update()

    is_dark = page.theme_mode == ft.ThemeMode.DARK
    
    history_view = ft.Column(
        expand=True,
        spacing=14,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(t("history_title"), size=20, weight=ft.FontWeight.W_700),
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.OutlinedButton(
                                t("refresh"), 
                                icon=ft.Icons.REFRESH, 
                                on_click=lambda _: refresh_history_and_stats(),
                                style=ft.ButtonStyle(
                                    padding=10,
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                ),
                            ),
                            ft.OutlinedButton(
                                t("clear_all"), 
                                icon=ft.Icons.DELETE_SWEEP_OUTLINED, 
                                on_click=clear_all,
                                style=ft.ButtonStyle(
                                    padding=10,
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                ),
                            ),
                        ],
                    ),
                ],
            ),
            ft.Container(
                expand=True, 
                border_radius=16, 
                padding=14, 
                bgcolor=ft.Colors.with_opacity(0.2 if is_dark else 0.4, ft.Colors.SURFACE),
                border=ft.BorderSide(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE if is_dark else ft.Colors.BLACK)),
                shadow=ft.BoxShadow(
                    blur_radius=25,
                    spread_radius=0,
                    color=ft.Colors.with_opacity(0.25 if is_dark else 0.12, ft.Colors.BLACK),
                    offset=ft.Offset(0, 8),
                ),
                content=ft.Column([dt], expand=True),
            ),
        ],
    )

    settings_ui = create_settings_view(settings, snack, t, page)
    settings_view = settings_ui["view"]
    tf_buy_currency = settings_ui["tf_buy_currency"]
    tf_sell_currency = settings_ui["tf_sell_currency"]
    tf_exchange_rate = settings_ui["tf_exchange_rate"]
    tf_fee_rate = settings_ui["tf_fee_rate"]
    dd_my_currency = settings_ui["dd_my_currency"]
    dd_language = settings_ui["dd_language"]
    btn_fetch_rate = settings_ui["btn_fetch_rate"]
    update_save_status = settings_ui["update_save_status"]
    update_exchange_label = settings_ui["update_exchange_label"]
    mark_unsaved = settings_ui["mark_unsaved"]
    check_unsaved = settings_ui["check_unsaved"]
    save_button = settings_ui["save_button"]

    check_unsaved()

    def fetch_exchange_rate_handler(_):
        buy_code = tf_buy_currency.value or "CNY"
        sell_code = tf_sell_currency.value or "CNY"

        if buy_code == sell_code:
            snack.content = ft.Text(t("error_same_currency"))
            snack.open = True
            page.update()
            return

        snack.content = ft.Text(t("fetching_rate"))
        snack.open = True
        page.update()

        rate, updated_at, message = fetch_exchange_rate(buy_code, sell_code)
        
        if "成功" in message:
            tf_exchange_rate.value = str(rate)
            snack.content = ft.Text(t("rate_success", base=buy_code, target=sell_code, rate=rate))
            mark_unsaved()
        else:
            snack.content = ft.Text(t("rate_failed"))
        snack.open = True
        page.update()

    btn_fetch_rate.on_click = fetch_exchange_rate_handler

    def save_settings_click(_):
        current_settings = get_settings()
        old_language = current_settings.language
        
        buy_currency = tf_buy_currency.value or "CNY"
        sell_currency = tf_sell_currency.value or "CNY"
        exchange_rate = safe_float(tf_exchange_rate.value)
        fee_rate = safe_float(tf_fee_rate.value) / 100.0
        my_currency = dd_my_currency.value or "CNY"
        language = dd_language.value or "zh"

        if fee_rate <= 0 or fee_rate >= 1:
            snack.content = ft.Text(t("error_invalid_fee"))
            snack.open = True
            page.update()
            return

        new_settings = {
            "buy_currency": buy_currency,
            "buy_currency_symbol": CURRENCY_SYMBOLS[buy_currency],
            "sell_currency": sell_currency,
            "sell_currency_symbol": CURRENCY_SYMBOLS[sell_currency],
            "exchange_rate": exchange_rate,
            "steam_fee_rate": fee_rate,
            "my_currency": my_currency,
            "my_currency_symbol": CURRENCY_SYMBOLS[my_currency],
            "language": language,
        }

        from models import Settings
        settings_obj = Settings(**new_settings)
        saved_settings = save_settings(settings_obj)
        settings = saved_settings
        
        page.theme_mode = ft.ThemeMode.DARK
        tf_exchange_rate.label = t("exchange_rate", from_curr=buy_currency, to_curr=sell_currency)
        snack.content = ft.Text(t("saved"))
        tf_cost.prefix = ft.Text(settings.buy_currency_symbol)
        tf_steam_sell.prefix = ft.Text(settings.sell_currency_symbol)
        recalc()
        update_save_status(True)
        page.update()
        
        if language != old_language:
            page.snack_bar.open = False
            rebuild_ui()

    save_button.on_click = save_settings_click

    current_view = "calculator"

    def switch_view(view_name):
        nonlocal current_view
        current_view = view_name
        calc_card.visible = (view_name == "calculator")
        history_view.visible = (view_name == "history")
        stats_view.visible = (view_name == "stats")
        settings_view.visible = (view_name == "settings")
        update_button_styles()
        page.update()
    
    def update_button_styles():
        for btn, view_name in buttons:
            if view_name == current_view:
                btn.style.bgcolor = ft.Colors.with_opacity(0.8, ft.Colors.INDIGO)
                btn.style.color = ft.Colors.WHITE
                btn.style.overlay_color = ft.Colors.with_opacity(0.2, ft.Colors.WHITE)
            else:
                btn.style.bgcolor = ft.Colors.with_opacity(0.3, ft.Colors.SURFACE)
                btn.style.color = ft.Colors.WHITE
                btn.style.overlay_color = ft.Colors.with_opacity(0.1, ft.Colors.WHITE)
        page.update()
    
    btn_calculator = ft.Button(
        t("calculator"),
        icon=ft.Icons.CALCULATE_OUTLINED,
        on_click=lambda _: switch_view("calculator"),
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.INDIGO),
            color=ft.Colors.WHITE,
            padding=10,
            shape=ft.RoundedRectangleBorder(radius=10),
            overlay_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        ),
    )
    
    btn_history = ft.Button(
        t("history"),
        icon=ft.Icons.HISTORY,
        on_click=lambda _: switch_view("history"),
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.SURFACE),
            color=ft.Colors.WHITE,
            padding=10,
            shape=ft.RoundedRectangleBorder(radius=10),
            overlay_color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
        ),
    )
    
    btn_stats = ft.Button(
        t("stats"),
        icon=ft.Icons.INSIGHTS_OUTLINED,
        on_click=lambda _: switch_view("stats"),
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.SURFACE),
            color=ft.Colors.WHITE,
            padding=10,
            shape=ft.RoundedRectangleBorder(radius=10),
            overlay_color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
        ),
    )
    
    btn_settings = ft.Button(
        t("settings"),
        icon=ft.Icons.SETTINGS_OUTLINED,
        on_click=lambda _: switch_view("settings"),
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.SURFACE),
            color=ft.Colors.WHITE,
            padding=10,
            shape=ft.RoundedRectangleBorder(radius=10),
            overlay_color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
        ),
    )
    
    buttons = [
        (btn_calculator, "calculator"),
        (btn_history, "history"),
        (btn_stats, "stats"),
        (btn_settings, "settings"),
    ]
    
    tab_buttons = ft.Row([btn for btn, _ in buttons], spacing=8)

    main_content = ft.Container(
        padding=16,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(
                                    content=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, size=28, color=ft.Colors.WHITE),
                                    padding=8,
                                    border_radius=12,
                                    bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.INDIGO),
                                ),
                                ft.Text(t("app_title"), size=22, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE if is_dark else ft.Colors.BLACK),
                            ],
                        ),
                    ],
                ),
                ft.Container(
                    padding=12,
                    border_radius=14,
                    bgcolor=ft.Colors.with_opacity(0.2 if is_dark else 0.4, ft.Colors.SURFACE),
                    content=tab_buttons,
                ),
                calc_card,
                history_view,
                stats_view,
                settings_view,
            ],
        ),
    )

    background_stack = ft.Stack(
        [
            create_gradient_background(is_dark),
            create_floating_orbs(is_dark),
            ft.Container(
                content=main_content,
                padding=20,
                expand=True,
            ),
        ],
        expand=True,
        width=float("inf"),
        height=float("inf"),
    )

    page.add(background_stack)

    history_view.visible = False
    stats_view.visible = False
    settings_view.visible = False
    refresh_history()
    refresh_stats()
    recalc()
    page.update()

    def rebuild_ui():
        page.controls.clear()
        main(page)

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP, port=0)