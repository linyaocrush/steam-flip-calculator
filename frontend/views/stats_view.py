import flet as ft
from utils import money, pct


def create_stats_view(settings, t):
    st_total_cost = ft.Text("-")
    st_total_net = ft.Text("-")
    st_total_sell = ft.Text("-")
    st_total_qty = ft.Text("-")
    st_ratio = ft.Text("-")
    st_discount = ft.Text("-")

    def kv_row(k: str, v: ft.Control):
        return ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(k), v])

    stats_view = ft.Card(
        elevation=1,
        content=ft.Container(
            padding=18,
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Text(t("stats_title"), size=18, weight=ft.FontWeight.W_700),
                    ft.Container(
                        padding=16,
                        border_radius=14,
                        bgcolor=ft.Colors.SURFACE_CONTAINER,
                        content=ft.Column(
                            spacing=10,
                            controls=[
                                kv_row(t("total_qty"), st_total_qty),
                                kv_row(t("total_cost"), st_total_cost),
                                kv_row(t("total_sell"), st_total_sell),
                                kv_row(t("total_net"), st_total_net),
                                ft.Divider(height=1),
                                kv_row(t("total_ratio"), st_ratio),
                                kv_row(t("total_discount"), st_discount),
                            ],
                        ),
                    ),
                    ft.Text(t("stats_hint"), opacity=0.8),
                ],
            ),
        ),
    )

    def update_stats(stats):
        if stats:
            # 使用统计数据中返回的我的货币符号（数据库中已转换好）
            my_currency_symbol = stats.get('my_currency_symbol', settings.get('my_currency_symbol', '¥'))
            st_total_cost.value = f"{my_currency_symbol} {money(stats['total_cost'])}"
            st_total_net.value = f"{my_currency_symbol} {money(stats['total_net'])}"
            st_total_sell.value = f"{my_currency_symbol} {money(stats['total_steam_sell'])}"
            st_total_qty.value = f"{stats['total_qty']}"
            st_ratio.value = pct(stats["ratio"]) if stats["total_net"] > 0 else "-"
            st_discount.value = pct(stats["discount"]) if stats["total_net"] > 0 else "-"
        else:
            st_total_cost.value = "-"
            st_total_net.value = "-"
            st_total_sell.value = "-"
            st_total_qty.value = "-"
            st_ratio.value = "-"
            st_discount.value = "-"

    return {
        "view": stats_view,
        "update_stats": update_stats,
    }