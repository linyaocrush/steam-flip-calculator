import flet as ft


def create_navigation(t, page):
    views = {}
    current_view = "calculator"
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

    def _btn(label_key, icon, view_name):
        btn = ft.Button(
            t(label_key),
            icon=icon,
            on_click=lambda _: switch_view(view_name),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.with_opacity(0.8 if view_name == "calculator" else 0.3, ft.Colors.INDIGO),
                color=ft.Colors.WHITE,
                padding=10,
                shape=ft.RoundedRectangleBorder(radius=10),
                overlay_color=ft.Colors.with_opacity(0.2 if view_name == "calculator" else 0.1, ft.Colors.WHITE),
            ),
        )
        buttons.append((btn, view_name))
        return btn

    tab_buttons = ft.Row([
        _btn("calculator", ft.Icons.CALCULATE_OUTLINED, "calculator"),
        _btn("history", ft.Icons.HISTORY, "history"),
        _btn("stats", ft.Icons.INSIGHTS_OUTLINED, "stats"),
        _btn("settings", ft.Icons.SETTINGS_OUTLINED, "settings"),
    ], spacing=8)

    return tab_buttons, switch_view, register_view
