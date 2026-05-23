import threading
import flet as ft
from utils import safe_float
from config import CURRENCY_SYMBOLS
from services.exchange_rate import fetch_exchange_rate
from state.app_state import app_state


def setup_settings_controller(settings_ui, page, snack, t):
    """Wire up the fetch-rate and save buttons in the settings view."""
    tf_buy_currency = settings_ui.tf_buy_currency
    tf_sell_currency = settings_ui.tf_sell_currency
    tf_exchange_rate = settings_ui.tf_exchange_rate
    tf_fee_rate = settings_ui.tf_fee_rate
    dd_my_currency = settings_ui.dd_my_currency
    dd_language = settings_ui.dd_language
    btn_fetch_rate = settings_ui.btn_fetch_rate
    update_save_status = settings_ui.update_save_status
    update_exchange_label = settings_ui.update_exchange_label
    mark_unsaved = settings_ui.mark_unsaved
    save_button = settings_ui.save_button

    def fetch_rate_handler(_):
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

        def _fetch_task():
            rate, updated_at, message = fetch_exchange_rate(buy_code, sell_code, force_refresh=True)
            if rate is not None:
                tf_exchange_rate.value = str(rate)
                snack.content = ft.Text(t("rate_success", base=buy_code, target=sell_code, rate=rate))
                mark_unsaved()
            else:
                snack.content = ft.Text(t("rate_failed"))
            snack.open = True
            page.update()

        threading.Thread(target=_fetch_task, daemon=True).start()

    btn_fetch_rate.on_click = fetch_rate_handler

    def save_handler(_):
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

        settings = app_state.update_settings(new_settings)

        page.theme_mode = ft.ThemeMode.DARK
        tf_exchange_rate.label = t("exchange_rate", from_curr=buy_currency, to_curr=sell_currency)
        snack.content = ft.Text(t("saved"))
        update_save_status(True)
        page.update()

    save_button.on_click = save_handler
