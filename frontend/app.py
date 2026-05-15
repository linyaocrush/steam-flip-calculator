import flet as ft
from config import CURRENCY_SYMBOLS
from utils import safe_float, safe_int
from api import api_get, api_post, api_delete, check_api_connection
from i18n import get_text
from views import (
    create_loading_view,
    create_calculator_view,
    create_history_view,
    create_stats_view,
    create_settings_view,
)


def main(page: ft.Page):
    page.title = "Steam 倒余额工具箱"
    page.window_width = 1040
    page.window_height = 760
    page.theme_mode = ft.ThemeMode.LIGHT

    page.theme = ft.Theme(
        use_material3=True,
        color_scheme_seed=ft.Colors.INDIGO,
        visual_density=ft.VisualDensity.COMFORTABLE,
    )

    settings = {
        "buy_currency": "CNY",
        "buy_currency_symbol": "¥",
        "sell_currency": "CNY",
        "sell_currency_symbol": "¥",
        "exchange_rate": 1.0,
        "steam_fee_rate": 0.15,
        "theme_mode": "LIGHT",
        "my_currency": "CNY",
        "my_currency_symbol": "¥",
        "exchange_rate_updated_at": None,
        "language": "zh",
    }

    def get_t():
        lang = settings.get("language", "zh")
        return lambda key, **kwargs: get_text(key, lang, **kwargs)

    def load_settings():
        data, status = api_get("/settings")
        if status == 200:
            settings.update(data)
            theme_mode = settings.get("theme_mode", "LIGHT")
            page.theme_mode = ft.ThemeMode.DARK if theme_mode == "DARK" else ft.ThemeMode.LIGHT
            page.title = get_text("app_title", settings.get("language", "zh"))

    def on_retry(_):
        connect_to_backend()

    loading_components = create_loading_view(on_retry)
    loading_view = loading_components["view"]
    loading_text = loading_components["loading_text"]
    loading_progress = loading_components["loading_progress"]
    loading_error = loading_components["loading_error"]
    retry_button = loading_components["retry_button"]

    page.add(loading_view)
    page.update()

    def init_app():
        load_settings()
        t = get_t()

        snack = ft.SnackBar(content=ft.Text(""))
        page.snack_bar = snack

        def on_add_to_history(tf_item, tf_note, tf_cost, tf_steam_sell, tf_qty):
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

            data, status = api_post("/records", {
                "item_name": item_name,
                "note": note,
                "unit_cost": unit_cost,
                "unit_steam_sell": unit_sell,
                "qty": qty
            })

            if status == 201:
                snack.content = ft.Text(t("save_success"))
            else:
                snack.content = ft.Text(data.get("error", t("save_failed")))
            snack.open = True
            refresh_history()
            refresh_stats()
            page.update()

        calculator = create_calculator_view(settings, on_add_to_history, t)
        calc_card = calculator["view"]
        recalc = calculator["recalc"]
        tf_cost = calculator["tf_cost"]
        tf_steam_sell = calculator["tf_steam_sell"]
        reverse_box = calculator["reverse_box"]

        history = create_history_view(settings, snack, t)
        dt = history["dt"]
        row_for_record = history["row_for_record"]

        def refresh_history():
            records, status = api_get("/records")
            if status == 200:
                dt.rows = [row_for_record(r, refresh_history) for r in records]
            else:
                dt.rows = []
            page.update()

        stats = create_stats_view(settings, t)
        stats_view = stats["view"]
        update_stats = stats["update_stats"]

        def refresh_stats():
            stats_data, status = api_get("/stats")
            if status == 200:
                update_stats(stats_data)
            else:
                update_stats(None)
            page.update()

        dlg = ft.AlertDialog(modal=True, title=ft.Text(t("confirm_clear")), content=ft.Text(t("confirm_clear_msg")), actions=[])
        page.dialog = dlg

        def clear_all(_):
            def yes(_):
                _, status = api_delete("/records")
                if status == 200:
                    snack.content = ft.Text(t("clear_success"))
                else:
                    snack.content = ft.Text(t("clear_failed"))
                snack.open = True
                refresh_history()
                refresh_stats()
                dlg.open = False
                page.update()

            def no(_):
                dlg.open = False
                page.update()

            dlg.actions = [ft.TextButton(t("cancel"), on_click=no), ft.FilledButton(t("confirm"), on_click=yes)]
            dlg.open = True
            page.update()

        history_view = ft.Column(
            expand=True,
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(t("history_title"), size=18, weight=ft.FontWeight.W_700),
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.OutlinedButton(t("refresh"), icon=ft.Icons.REFRESH, on_click=lambda _: (refresh_history(), refresh_stats())),
                                ft.OutlinedButton(t("clear_all"), icon=ft.Icons.DELETE_SWEEP_OUTLINED, on_click=clear_all),
                            ],
                        ),
                    ],
                ),
                ft.Container(expand=True, border_radius=14, padding=10, bgcolor=ft.Colors.SURFACE, content=ft.Column([dt], expand=True)),
            ],
        )

        settings_ui = create_settings_view(settings, snack, t)
        settings_view = settings_ui["view"]
        tf_buy_currency = settings_ui["tf_buy_currency"]
        tf_sell_currency = settings_ui["tf_sell_currency"]
        tf_exchange_rate = settings_ui["tf_exchange_rate"]
        tf_fee_rate = settings_ui["tf_fee_rate"]
        dd_theme_mode = settings_ui["dd_theme_mode"]
        dd_my_currency = settings_ui["dd_my_currency"]
        dd_language = settings_ui["dd_language"]
        btn_fetch_rate = settings_ui["btn_fetch_rate"]
        update_save_status = settings_ui["update_save_status"]
        update_exchange_label = settings_ui["update_exchange_label"]
        mark_unsaved = settings_ui["mark_unsaved"]
        save_button = settings_ui["save_button"]

        def fetch_exchange_rate(_):
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

            data, status = api_get(f"/exchange-rate?base={buy_code}&target={sell_code}")
            if status == 200 and "rate" in data:
                tf_exchange_rate.value = str(data["rate"])
                snack.content = ft.Text(t("rate_success", base=buy_code, target=sell_code, rate=data["rate"]))
                mark_unsaved()
            else:
                snack.content = ft.Text(data.get("error", t("rate_failed")))
            snack.open = True
            page.update()

        btn_fetch_rate.on_click = fetch_exchange_rate

        def save_settings_click(_):
            buy_currency = tf_buy_currency.value or "CNY"
            sell_currency = tf_sell_currency.value or "CNY"
            exchange_rate = safe_float(tf_exchange_rate.value)
            fee_rate = safe_float(tf_fee_rate.value) / 100.0
            theme_mode = dd_theme_mode.value or "LIGHT"
            my_currency = dd_my_currency.value or "CNY"
            language = dd_language.value or "zh"

            if fee_rate <= 0 or fee_rate >= 1:
                snack.content = ft.Text(t("error_invalid_fee"))
                snack.open = True
                page.update()
                return

            snack.content = ft.Text(t("fetching_rate"))
            snack.open = True
            page.update()

            data, status = api_post("/settings", {
                "buy_currency": buy_currency,
                "buy_currency_symbol": CURRENCY_SYMBOLS[buy_currency],
                "sell_currency": sell_currency,
                "sell_currency_symbol": CURRENCY_SYMBOLS[sell_currency],
                "exchange_rate": exchange_rate,
                "steam_fee_rate": fee_rate,
                "theme_mode": theme_mode,
                "my_currency": my_currency,
                "my_currency_symbol": CURRENCY_SYMBOLS[my_currency],
                "language": language,
            })

            if status == 200:
                settings.update({
                    "buy_currency": buy_currency,
                    "buy_currency_symbol": CURRENCY_SYMBOLS[buy_currency],
                    "sell_currency": sell_currency,
                    "sell_currency_symbol": CURRENCY_SYMBOLS[sell_currency],
                    "exchange_rate": data.get("exchange_rate", exchange_rate),
                    "steam_fee_rate": fee_rate,
                    "theme_mode": theme_mode,
                    "my_currency": my_currency,
                    "my_currency_symbol": CURRENCY_SYMBOLS[my_currency],
                    "exchange_rate_updated_at": data.get("exchange_rate_updated_at"),
                    "language": language,
                })
                tf_exchange_rate.value = str(settings["exchange_rate"])
                page.theme_mode = ft.ThemeMode.DARK if theme_mode == "DARK" else ft.ThemeMode.LIGHT
                tf_exchange_rate.label = t("exchange_rate", from_curr=buy_currency, to_curr=sell_currency)
                snack.content = ft.Text(t("save_success"))
                tf_cost.prefix = ft.Text(settings["buy_currency_symbol"])
                tf_steam_sell.prefix = ft.Text(settings["sell_currency_symbol"])
                reverse_box.content.controls[1].value = t("steam_fee", fee=fee_rate * 100)
                recalc()
                update_save_status(True)
            else:
                snack.content = ft.Text(data.get("error", t("save_failed")))
            snack.open = True
            page.update()

        save_button.on_click = save_settings_click

        def toggle_theme(_):
            page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
            page.update()

        def switch_view(view_name):
            calc_card.visible = (view_name == "calculator")
            history_view.visible = (view_name == "history")
            stats_view.visible = (view_name == "stats")
            settings_view.visible = (view_name == "settings")
            page.update()

        tab_buttons = ft.Row([
            ft.Button(
                t("calculator"),
                icon=ft.Icons.CALCULATE_OUTLINED,
                on_click=lambda _: switch_view("calculator"),
            ),
            ft.Button(
                t("history"),
                icon=ft.Icons.HISTORY,
                on_click=lambda _: switch_view("history"),
            ),
            ft.Button(
                t("stats"),
                icon=ft.Icons.INSIGHTS_OUTLINED,
                on_click=lambda _: switch_view("stats"),
            ),
            ft.Button(
                t("settings"),
                icon=ft.Icons.SETTINGS_OUTLINED,
                on_click=lambda _: switch_view("settings"),
            ),
        ])

        main_content = ft.Container(
            padding=12,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=10,
                                controls=[ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED),
                                          ft.Text(t("app_title"), size=20, weight=ft.FontWeight.W_700)],
                            ),
                            ft.OutlinedButton(t("toggle_theme"), icon=ft.Icons.DARK_MODE_OUTLINED, on_click=toggle_theme),
                        ],
                    ),
                    tab_buttons,
                    calc_card,
                    history_view,
                    stats_view,
                    settings_view,
                ],
            ),
        )

        page.controls.clear()
        page.add(main_content)

        history_view.visible = False
        stats_view.visible = False
        settings_view.visible = False
        refresh_history()
        refresh_stats()
        recalc()
        page.update()

    def connect_to_backend():
        loading_error.value = ""
        retry_button.visible = False
        loading_text.value = get_text("loading", settings.get("language", "zh"))
        page.update()

        for attempt in range(5):
            loading_text.value = get_text("loading", settings.get("language", "zh")) + f" ({attempt + 1}/5)"
            loading_progress.value = (attempt + 1) / 5
            page.update()

            if check_api_connection():
                loading_text.value = get_text("loading_success", settings.get("language", "zh"))
                loading_progress.value = 1.0
                page.update()
                init_app()
                return

        loading_text.value = get_text("loading_failed", settings.get("language", "zh"))
        loading_error.value = get_text("connection_error", settings.get("language", "zh"))
        loading_progress.value = 0
        retry_button.visible = True
        page.update()

    connect_to_backend()


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP, port=0)