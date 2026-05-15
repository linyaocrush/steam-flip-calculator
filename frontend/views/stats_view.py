import flet as ft
from utils import money, pct


def create_stats_view(settings):
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
                    ft.Text("统计汇总（基于历史记录）", size=18, weight=ft.FontWeight.W_700),
                    ft.Container(
                        padding=16,
                        border_radius=14,
                        bgcolor=ft.Colors.SURFACE_CONTAINER,
                        content=ft.Column(
                            spacing=10,
                            controls=[
                                kv_row("总数量:", st_total_qty),
                                kv_row("总花费:", st_total_cost),
                                kv_row("Steam 售出总额(未扣费):", st_total_sell),
                                kv_row("总到手余额(已扣手续费):", st_total_net),
                                ft.Divider(height=1),
                                kv_row("整体倒余额比例(花费/到手):", st_ratio),
                                kv_row("整体折扣:", st_discount),
                            ],
                        ),
                    ),
                    ft.Text("提示：整体折扣=1-（总花费/总到手余额）。例如花 70 得 85，折扣≈17.65%。", opacity=0.8),
                ],
            ),
        ),
    )

    def update_stats(stats):
        if stats:
            st_total_cost.value = f"{settings['sell_currency_symbol']} {money(stats['total_cost'])}"
            st_total_net.value = f"{settings['sell_currency_symbol']} {money(stats['total_net'])}"
            st_total_sell.value = f"{settings['sell_currency_symbol']} {money(stats['total_steam_sell'])}"
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