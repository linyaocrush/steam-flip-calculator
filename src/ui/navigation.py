import flet as ft
from enum import Enum


class AppView(Enum):
    CALCULATOR = "calculator"
    HISTORY = "history"
    STATS = "stats"
    SETTINGS = "settings"


def create_navigation(t, page):
    views = {}
    current_view = AppView.CALCULATOR
    buttons = []

    def register_view(name, view):
        views[name] = view

    def switch_view(view_name):
        nonlocal current_view
        current_view = view_name
        for name, view in views.items():
            view.visible = (name == view_name)
        _update_styles()
        page.update()

    def _update_styles():
        for btn, name in buttons:
            if name == current_view:
                btn.style.bgcolor = ft.Colors.with_opacity(0.8, ft.Colors.INDIGO)
                btn.style.color = ft.Colors.WHITE
                btn.style.overlay_color = ft.Colors.with_opacity(0.2, ft.Colors.WHITE)
            else:
                btn.style.bgcolor = ft.Colors.with_opacity(0.3, ft.Colors.SURFACE)
                btn.style.color = ft.Colors.WHITE
                btn.style.overlay_color = ft.Colors.with_opacity(0.1, ft.Colors.WHITE)
        page.update()

    _btn_labels = {}

    def _btn(label_key, icon, view_name):
        btn = ft.Button(
            t(label_key),
            icon=icon,
            on_click=lambda _: switch_view(view_name),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.with_opacity(0.8 if view_name == AppView.CALCULATOR else 0.3, ft.Colors.INDIGO),
                color=ft.Colors.WHITE,
                padding=10,
                shape=ft.RoundedRectangleBorder(radius=10),
                overlay_color=ft.Colors.with_opacity(0.2 if view_name == AppView.CALCULATOR else 0.1, ft.Colors.WHITE),
            ),
        )
        buttons.append((btn, view_name))
        _btn_labels[view_name] = label_key
        return btn

    def refresh_language(t_new):
        for btn, name in buttons:
            btn.text = t_new(_btn_labels[name])

    tab_buttons = ft.Row([
        _btn("calculator", ft.Icons.CALCULATE_OUTLINED, AppView.CALCULATOR),
        _btn("history", ft.Icons.HISTORY, AppView.HISTORY),
        _btn("stats", ft.Icons.INSIGHTS_OUTLINED, AppView.STATS),
        _btn("settings", ft.Icons.SETTINGS_OUTLINED, AppView.SETTINGS),
    ], spacing=8)

    return tab_buttons, switch_view, register_view, refresh_language
