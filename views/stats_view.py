import flet as ft
from utils import money, pct
from glassmorphism import get_glassmorphism_style


def create_stats_view(settings, t):
    is_dark = True
    
    st_total_cost = ft.Text("-")
    st_total_net = ft.Text("-")
    st_total_sell = ft.Text("-")
    st_total_qty = ft.Text("-")
    st_ratio = ft.Text("-")
    st_discount = ft.Text("-")

    def kv_row(k: str, v: ft.Control):
        return ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(k, size=14), v])

    stats_view = ft.Container(
        padding=20,
        border_radius=18,
        bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.SURFACE),
        border=ft.BorderSide(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
        shadow=ft.BoxShadow(
            blur_radius=30,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
            offset=ft.Offset(0, 10),
        ),
        content=ft.Column(
            spacing=16,
            controls=[
                ft.Text(t("stats_title"), size=20, weight=ft.FontWeight.W_700),
                ft.Container(
                    padding=18,
                    border_radius=16,
                    bgcolor=ft.Colors.with_opacity(0.25, ft.Colors.SURFACE_CONTAINER),
                    border=ft.BorderSide(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
                    shadow=ft.BoxShadow(
                        blur_radius=20,
                        spread_radius=0,
                        color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                        offset=ft.Offset(0, 5),
                    ),
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            kv_row(t("total_qty"), st_total_qty),
                            kv_row(t("total_cost"), st_total_cost),
                            kv_row(t("total_sell"), st_total_sell),
                            kv_row(t("total_net"), st_total_net),
                            ft.Container(height=1, bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.SURFACE)),
                            kv_row(t("total_ratio"), st_ratio),
                            kv_row(t("total_discount"), st_discount),
                        ],
                    ),
                ),
                ft.Text(t("stats_hint"), opacity=0.8, size=13),
            ],
        ),
    )

    def update_stats(stats):
        if stats:
            my_currency_symbol = settings.my_currency_symbol
            st_total_cost.value = f"{my_currency_symbol} {money(stats.total_cost)}"
            st_total_net.value = f"{my_currency_symbol} {money(stats.total_net)}"
            st_total_sell.value = f"{my_currency_symbol} {money(stats.total_sell)}"
            st_total_qty.value = f"{stats.total_qty}"
            st_ratio.value = pct(stats.avg_ratio) if stats.total_net > 0 else "-"
            st_discount.value = pct(stats.avg_discount) if stats.total_net > 0 else "-"
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