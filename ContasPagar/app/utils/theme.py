"""Paleta explícita para evitar herança parcial do modo escuro do Windows."""

from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt, QLocale
from pathlib import Path


def apply_light_theme(app):
    app.setStyle("Fusion")
    QLocale.setDefault(QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil))
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: "#F5F7FA",
        QPalette.ColorRole.WindowText: "#1F2937",
        QPalette.ColorRole.Base: "#FFFFFF",
        QPalette.ColorRole.AlternateBase: "#F8FAFC",
        QPalette.ColorRole.Text: "#1F2937",
        QPalette.ColorRole.Button: "#FFFFFF",
        QPalette.ColorRole.ButtonText: "#1F2937",
        QPalette.ColorRole.Highlight: "#2563EB",
        QPalette.ColorRole.HighlightedText: "#FFFFFF",
        QPalette.ColorRole.ToolTipBase: "#FFFFFF",
        QPalette.ColorRole.ToolTipText: "#1F2937",
        QPalette.ColorRole.PlaceholderText: "#8290A3",
        QPalette.ColorRole.Light: "#FFFFFF",
        QPalette.ColorRole.Midlight: "#EEF2F7",
        QPalette.ColorRole.Mid: "#D8E0EB",
        QPalette.ColorRole.Dark: "#718096",
        QPalette.ColorRole.Shadow: "#CBD5E1",
        QPalette.ColorRole.Link: "#2563EB",
        QPalette.ColorRole.BrightText: "#FFFFFF",
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    for role in (
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
        QPalette.ColorRole.WindowText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#94A3B8"))
    app.setPalette(palette)
    if hasattr(app.styleHints(), "setColorScheme"):
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)


def load_stylesheet():
    assets = Path(__file__).resolve().parents[1] / "assets"
    return (
        (assets / "style.qss")
        .read_text(encoding="utf-8")
        .replace("@ASSET_DIR@", assets.as_posix())
    )
