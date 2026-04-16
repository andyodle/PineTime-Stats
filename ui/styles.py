"""
UI styles and theming for PineTime Dashboard.
"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPalette, QFont

DARK_THEME = {
    "background": "#1e1e2e",
    "surface": "#2d2d3f",
    "surface_elevated": "#3d3d4f",
    "primary": "#89b4fa",
    "primary_variant": "#74a8f9",
    "secondary": "#a6e3a1",
    "accent": "#f9e2af",
    "error": "#f38ba8",
    "warning": "#f9c74f",
    "success": "#a6e3a1",
    "text_primary": "#cdd6f4",
    "text_secondary": "#a6adc8",
    "text_muted": "#6c7086",
    "border": "#45475a",
    "chart_steps": "#89b4fa",
    "chart_hr": "#f38ba8",
}

LIGHT_THEME = {
    "background": "#eff1f5",
    "surface": "#ffffff",
    "surface_elevated": "#e6e9ef",
    "primary": "#1e66f5",
    "primary_variant": "#0a48b3",
    "secondary": "#40a02b",
    "accent": "#df8e1d",
    "error": "#d20f39",
    "warning": "#df8e1d",
    "success": "#40a02b",
    "text_primary": "#4c4f69",
    "text_secondary": "#5c5f77",
    "text_muted": "#9ca0b0",
    "border": "#ccd0da",
    "chart_steps": "#1e66f5",
    "chart_hr": "#d20f39",
}


def get_theme(is_dark: bool = True) -> dict:
    """Get theme colors."""
    return DARK_THEME if is_dark else LIGHT_THEME


def apply_theme(app, is_dark: bool = True) -> None:
    """Apply theme to application."""
    theme = get_theme(is_dark)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(theme["background"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(theme["text_primary"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(theme["surface"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme["surface_elevated"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(theme["surface"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(theme["text_primary"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(theme["text_primary"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(theme["surface"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme["text_primary"]))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(theme["text_primary"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(theme["primary"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(theme["background"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(theme["text_muted"]))

    app.setPalette(palette)


def get_font(size: int = 10, weight: int = 400) -> QFont:
    """Get configured font."""
    font = QFont("Segoe UI", size)
    font.setWeight(weight)
    return font


def get_icon_size() -> QSize:
    """Get standard icon size."""
    return QSize(24, 24)


class Fonts:
    """Font definitions."""
    TITLE = get_font(18, 600)
    HEADING = get_font(14, 600)
    BODY = get_font(10, 400)
    BODY_BOLD = get_font(10, 600)
    LABEL = get_font(9, 400)
    STAT_VALUE = get_font(24, 700)
    STAT_LABEL = get_font(10, 400)
    MONO = QFont("Consolas", 10)
