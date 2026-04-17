"""
Custom widgets for PineTime Dashboard UI.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QProgressBar, QPushButton, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QPainter, QPen

from .styles import get_theme, Fonts, get_icon_size


class StatCard(QFrame):
    """
    Statistics display card with value and label.

    Usage:
        card = StatCard(title="Steps")
        card.set_value(12450)
        card.set_progress(83, 15000)  # 83% of 15000 goal
    """

    def __init__(self, title: str, unit: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self._unit = unit
        self._value = None
        self._progress = None
        self._max_value = None
        self._theme = get_theme()

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the card layout."""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setObjectName("statCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        self._title_label = QLabel(self._title)
        self._title_label.setFont(Fonts.LABEL)
        self._title_label.setStyleSheet(
            f"color: {self._theme['text_secondary']}; background: transparent;"
        )
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_label)

        self._value_label = QLabel("--")
        self._value_label.setFont(Fonts.STAT_VALUE)
        self._value_label.setStyleSheet(
            f"color: {self._theme['text_primary']}; background: transparent;"
        )
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._value_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {self._theme['border']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {self._theme['primary']};
                border-radius: 3px;
            }}
        """)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._unit_label = QLabel("")
        self._unit_label.setFont(Fonts.LABEL)
        self._unit_label.setStyleSheet(
            f"color: {self._theme['text_muted']}; background: transparent;"
        )
        self._unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._unit_label)

        self._update_style()

    def _update_style(self) -> None:
        """Update card styling."""
        self.setStyleSheet(f"""
            #statCard {{
                background: {self._theme['surface']};
                border: 1px solid {self._theme['border']};
                border-radius: 12px;
            }}
        """)

    def set_value(self, value, format_number: bool = True) -> None:
        """
        Set the displayed value.

        Args:
            value: Numeric value to display.
            format_number: Whether to format with thousand separators.
        """
        if value is None:
            self._value_label.setText("--")
            self._value = None
            return

        self._value = value

        if format_number and isinstance(value, (int, float)):
            if isinstance(value, int):
                text = f"{value:,}"
            else:
                text = f"{value:.1f}"
        else:
            text = str(value)

        self._value_label.setText(text)

    def set_progress(self, current: int, maximum: int) -> None:
        """
        Set progress bar values.

        Args:
            current: Current progress value.
            maximum: Maximum (goal) value.
        """
        if maximum > 0:
            self._progress_bar.setMaximum(maximum)
            self._progress_bar.setValue(min(current, maximum))
            self._progress_bar.setVisible(True)
            self._progress = current
            self._max_value = maximum
        else:
            self._progress_bar.setVisible(False)

    def set_unit(self, unit: str) -> None:
        """Set the unit label."""
        self._unit_label.setText(unit)

    def get_value(self):
        """Get current value."""
        return self._value

    def refresh_theme(self, is_dark: bool = True) -> None:
        """Refresh theme colors."""
        self._theme = get_theme(is_dark)
        self._update_style()
        self._setup_ui()
        if self._value is not None:
            self.set_value(self._value)
        if self._progress is not None and self._max_value:
            self.set_progress(self._progress, self._max_value)


class ConnectionStatus(QFrame):
    """Connection status indicator widget."""

    connection_changed = pyqtSignal(bool)
    restart_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self._device_name = ""
        self._firmware_version = ""
        self._battery_level = None
        self._theme = get_theme()

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the status layout."""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        self._status_indicator = QLabel()
        self._status_indicator.setFixedSize(12, 12)
        self._status_indicator.setStyleSheet(
            f"background: {self._theme['error']}; "
            f"border-radius: 6px;"
        )
        layout.addWidget(self._status_indicator)

        self._status_text = QLabel("Not Connected")
        self._status_text.setFont(Fonts.BODY)
        self._status_text.setStyleSheet(f"color: {self._theme['text_primary']};")
        layout.addWidget(self._status_text, stretch=1)

        self._battery_label = QLabel("")
        self._battery_label.setFont(Fonts.BODY)
        self._battery_label.setStyleSheet(f"color: {self._theme['text_secondary']};")
        self._battery_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._battery_label)

        self._restart_button = QPushButton("Restart")
        self._restart_button.setFont(Fonts.LABEL)
        self._restart_button.setFixedWidth(70)
        self._restart_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._restart_button.setVisible(False)
        self._restart_button.clicked.connect(self._on_restart_clicked)
        self._restart_button.setStyleSheet(f"""
            QPushButton {{
                background: {self._theme['warning']};
                color: {self._theme['background']};
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #d97706;
            }}
        """)
        layout.addWidget(self._restart_button)

        self._update_style()

    def _update_style(self) -> None:
        """Update styling."""
        self.setStyleSheet(f"""
            QFrame {{
                background: {self._theme['surface']};
                border: 1px solid {self._theme['border']};
                border-radius: 8px;
            }}
        """)

    def set_connected(
        self,
        connected: bool,
        device_name: str = "",
        firmware_version: str = ""
    ) -> None:
        """Update connection status."""
        self._connected = connected
        self._device_name = device_name
        self._firmware_version = firmware_version

        if connected:
            status_color = self._theme["success"]
            status_text = f"Connected to {device_name or 'PineTime'}"
            if firmware_version:
                status_text += f" v{firmware_version}"
            self._restart_button.setVisible(True)
        else:
            status_color = self._theme["error"]
            status_text = "Not Connected"
            self._restart_button.setVisible(False)

        self._status_indicator.setStyleSheet(
            f"background: {status_color}; border-radius: 6px;"
        )
        self._status_text.setText(status_text)
        self.connection_changed.emit(connected)

    def set_battery_level(self, level: int) -> None:
        """Update battery level display."""
        self._battery_level = level
        if level >= 0:
            self._battery_label.setText(f"Battery: {level}%")
        else:
            self._battery_label.setText("")

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    def _on_restart_clicked(self) -> None:
        """Handle restart button click."""
        self.restart_requested.emit()


class SyncButton(QPushButton):
    """Specialized sync button with loading state."""

    def __init__(self, parent=None):
        super().__init__("Sync", parent)
        self._syncing = False
        self._theme = get_theme()

        self.setFont(Fonts.BODY_BOLD)
        self.setMinimumWidth(80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def _update_style(self) -> None:
        """Update button styling."""
        self.setStyleSheet(f"""
            QPushButton {{
                background: {self._theme['primary']};
                color: {self._theme['background']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {self._theme['primary_variant']};
            }}
            QPushButton:disabled {{
                background: {self._theme['border']};
                color: {self._theme['text_muted']};
            }}
            QPushButton:pressed {{
                background: {self._theme['primary_variant']};
            }}
        """)

    def set_syncing(self, syncing: bool) -> None:
        """Set syncing state."""
        self._syncing = syncing
        self.setEnabled(not syncing)
        self.setText("Syncing..." if syncing else "Sync")

    def is_syncing(self) -> bool:
        """Check if currently syncing."""
        return self._syncing


class StatusMessage(QLabel):
    """Status message label with auto-hide."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._hide_timer = QTimer(self)

        self.setFont(Fonts.LABEL)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"color: {self._theme['text_secondary']};")
        self.hide()

    def show_message(self, message: str, is_error: bool = False,
                    duration_ms: int = 3000) -> None:
        """
        Show a status message.

        Args:
            message: Message text.
            is_error: Whether this is an error message.
            duration_ms: Auto-hide duration in milliseconds.
        """
        color = self._theme["error"] if is_error else self._theme["text_secondary"]
        self.setStyleSheet(f"color: {color};")
        self.setText(message)
        self.show()

        if duration_ms > 0:
            self._hide_timer.start(duration_ms)

    def hide_message(self) -> None:
        """Hide the message."""
        self._hide_timer.stop()
        self.hide()
