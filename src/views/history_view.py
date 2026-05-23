import flet as ft
from decimal import Decimal
from typing import NamedTuple, Callable
from utils import money_decimal, pct_decimal, pct_raw
from config import CURRENCY_SYMBOLS


class HistoryView(NamedTuple):
    dt: ft.DataTable
    row_for_record: Callable
    add_row: Callable
    remove_row: Callable
    delete_record: Callable
    refresh_language: Callable


def create_history_view(settings, snack, t, page):
    col_time = ft.Text(t("time"), size=12)
    col_item = ft.Text(t("item"), size=12)
    col_qty = ft.Text(t("qty"), size=12)
    col_cost_unit = ft.Text(t("cost_unit"), size=12)
    col_sell_unit = ft.Text(t("sell_unit"), size=12)
    col_net_unit = ft.Text(t("net_unit"), size=12)
    col_cost_total = ft.Text(t("cost_total"), size=12)
    col_net_total = ft.Text(t("net_total"), size=12)
    col_flip_ratio = ft.Text(t("flip_ratio"), size=12)
    col_discount_pct = ft.Text(t("discount_pct"), size=12)
    col_action = ft.Text(t("action"), size=12)

    dt = ft.DataTable(
        columns=[
            ft.DataColumn(col_time),
            ft.DataColumn(col_item),
            ft.DataColumn(col_qty),
            ft.DataColumn(col_cost_unit),
            ft.DataColumn(col_sell_unit),
            ft.DataColumn(col_net_unit),
            ft.DataColumn(col_cost_total),
            ft.DataColumn(col_net_total),
            ft.DataColumn(col_flip_ratio),
            ft.DataColumn(col_discount_pct),
            ft.DataColumn(col_action),
        ],
        rows=[],
        border_radius=8,
        show_checkbox_column=False,
        expand=True,
        width=float("inf"),
    )

    def remove_row(record_id):
        """Remove a single DataRow by record id (stored in row.data)."""
        for i, row in enumerate(dt.rows):
            if row.data == record_id:
                dt.rows.pop(i)
                return True
        return False

    def delete_record(record_id, refresh_stats_callback):
        from services.database import delete_record as db_delete_record
        success = db_delete_record(record_id)
        if success:
            remove_row(record_id)
            snack.content = ft.Text(t("delete_success"))
        else:
            snack.content = ft.Text(t("delete_failed"))
        snack.open = True
        refresh_stats_callback()
        page.update()

    def row_for_record(record, delete_callback):
        buy_symbol = CURRENCY_SYMBOLS.get(record.buy_currency, "¥")
        sell_symbol = CURRENCY_SYMBOLS.get(record.sell_currency, "¥")

        row = ft.DataRow(
            data=record.id,
            cells=[
                ft.DataCell(ft.Text(record.ts, size=11)),
                ft.DataCell(
                    ft.Column(
                        spacing=2,
                        tight=True,
                        controls=[
                            ft.Text(record.item_name, size=12, weight=ft.FontWeight.W_500),
                            ft.Text(record.note, size=10, color=ft.Colors.GREY) if record.note else ft.Container(),
                        ],
                    )
                ),
                ft.DataCell(ft.Text(str(record.qty), size=11)),
                ft.DataCell(ft.Text(f"{buy_symbol} {money_decimal(record.unit_cost)}", size=11)),
                ft.DataCell(ft.Text(f"{sell_symbol} {money_decimal(record.unit_steam_sell)}", size=11)),
                ft.DataCell(ft.Text(f"{sell_symbol} {money_decimal(record.unit_net)}", size=11)),
                ft.DataCell(ft.Text(f"{buy_symbol} {money_decimal(record.total_cost)}", size=11)),
                ft.DataCell(ft.Text(f"{sell_symbol} {money_decimal(record.total_net)}", size=11)),
                ft.DataCell(ft.Text(pct_decimal(record.ratio), size=11)),
                ft.DataCell(ft.Text(pct_raw(record.discount), size=11)),
                ft.DataCell(
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.RED,
                        tooltip=t("delete"),
                        on_click=lambda _, rid=record.id: delete_record(rid, delete_callback),
                    )
                ),
            ],
        )
        return row

    def add_row(record, delete_callback):
        """Prepend a single DataRow (for incremental add)."""
        row = row_for_record(record, delete_callback)
        dt.rows.insert(0, row)
        page.update()

    def refresh_language(t):
        col_time.value = t("time")
        col_item.value = t("item")
        col_qty.value = t("qty")
        col_cost_unit.value = t("cost_unit")
        col_sell_unit.value = t("sell_unit")
        col_net_unit.value = t("net_unit")
        col_cost_total.value = t("cost_total")
        col_net_total.value = t("net_total")
        col_flip_ratio.value = t("flip_ratio")
        col_discount_pct.value = t("discount_pct")
        col_action.value = t("action")

    return HistoryView(
        dt=dt,
        row_for_record=row_for_record,
        add_row=add_row,
        remove_row=remove_row,
        delete_record=delete_record,
        refresh_language=refresh_language,
    )