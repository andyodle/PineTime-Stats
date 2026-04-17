"""
Main window for PineTime Dashboard application.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QFrame, QStatusBar,
    QMessageBox, QDialog, QComboBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThread
from PyQt6.QtGui import QAction, QColor

import pyqtgraph as pg

from .styles import get_theme, Fonts
from .widgets import StatCard, ConnectionStatus, SyncButton, StatusMessage
from .dialogs import DeviceSelectionDialog, SettingsDialog

logger = logging.getLogger(__name__)


class BLESyncWorker(QThread):
    """
    Background worker for BLE sync operations.
    Runs in separate thread to avoid blocking UI.
    """

    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    data_fetched = pyqtSignal(int, int, int, str)

    def __init__(self, ble_client, parent=None, paired_address: Optional[str] = None,
                 heart_rate_enabled: bool = True, clear_steps: bool = True):
        super().__init__(parent)
        self._ble_client = ble_client
        self._paired_address = paired_address
        self._heart_rate_enabled = heart_rate_enabled
        self._clear_steps = clear_steps
        self._loop = None
        self._stop_event = False

    def run(self) -> None:
        """Execute sync operation in async loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            if self._paired_address:
                self.progress.emit("Connecting to paired device...")
                try:
                    self._loop.run_until_complete(
                        self._ble_client.connect_by_address(self._paired_address, timeout=10.0)
                    )
                except Exception as e:
                    self.finished.emit(False, f"Connection failed: {e}")
                    return
            else:
                self.progress.emit("Scanning for PineTime...")
                try:
                    device = self._loop.run_until_complete(
                        self._ble_client.scan(timeout=5.0)
                    )
                except Exception as e:
                    self.finished.emit(False, f"Device not found: {e}")
                    return

                if self._stop_event:
                    return

                self.progress.emit("Connecting...")
                try:
                    self._loop.run_until_complete(
                        self._ble_client.connect(device)
                    )
                except Exception as e:
                    self.finished.emit(False, f"Connection failed: {e}")
                    return

            if self._stop_event:
                try:
                    self._loop.run_until_complete(self._ble_client.disconnect())
                except:
                    pass
                return

            self.progress.emit("Reading data...")
            try:
                steps = self._loop.run_until_complete(
                    self._ble_client.get_steps()
                )
                battery = self._loop.run_until_complete(
                    self._ble_client.get_battery_level()
                )
                firmware = self._loop.run_until_complete(
                    self._ble_client.get_firmware_version()
                )

                heart_rate = 0
                if self._heart_rate_enabled:
                    hr = self._loop.run_until_complete(
                        self._ble_client.get_heart_rate()
                    )
                    heart_rate = hr or 0

                self.data_fetched.emit(
                    steps,
                    heart_rate,
                    battery if battery else -1,
                    firmware or "Unknown",
                )

                if self._clear_steps and steps > 0:
                    self.progress.emit("Clearing steps on watch...")
                    cleared = self._loop.run_until_complete(
                        self._ble_client.clear_steps()
                    )
                    if cleared:
                        self.progress.emit("Steps cleared on PineTime")

                self.progress.emit("Disconnecting...")
                self._loop.run_until_complete(
                    self._ble_client.disconnect()
                )

                self.finished.emit(True, "Sync completed successfully")
                return

            except Exception as e:
                self.finished.emit(False, f"Data read failed: {e}")
                try:
                    self._loop.run_until_complete(
                        self._ble_client.disconnect()
                    )
                except:
                    pass
                return

        except Exception as e:
            self.finished.emit(False, f"Unexpected error: {e}")
        finally:
            try:
                if self._loop.is_running():
                    self._loop.run_until_complete(
                        self._ble_client.disconnect()
                    )
            except:
                pass
            self._loop.close()

    def stop(self) -> None:
        """Stop the worker."""
        self._stop_event = True


from PyQt6.QtCore import pyqtSignal

class ChartWidget(QWidget):
    """Chart widget using pyqtgraph for step and heart rate history."""

    filter_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._current_filter = "7d"
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the chart layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()

        self._title_label = QLabel("History")
        self._title_label.setFont(Fonts.HEADING)
        self._title_label.setStyleSheet(f"color: {self._theme['text_primary']};")
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["Day", "7 Days", "Month", "Year", "All"])
        self._filter_combo.setCurrentText("Day")
        self._filter_combo.setStyleSheet(f"""
            QComboBox {{
                color: {self._theme['text_secondary']};
                background-color: {self._theme['surface']};
                border: 1px solid {self._theme['border']};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 80px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                color: {self._theme['text_primary']};
                background-color: {self._theme['surface']};
                selection-background-color: {self._theme['primary']};
            }}
        """)
        self._filter_combo.currentTextChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self._filter_combo)

        layout.addLayout(header_layout)

        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground(QColor(self._theme["surface"]))
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.setMinimumHeight(150)

        self._steps_bar = pg.BarGraphItem(
            x=[], height=[], width=0.6,
            brush=self._theme["chart_steps"],
            name="Steps"
        )
        self._plot_widget.addItem(self._steps_bar)

        self._hr_line = self._plot_widget.plot(
            [], [], pen=pg.mkPen(color=self._theme["chart_hr"], width=2),
            symbol='s', symbolSize=8, symbolBrush=self._theme["chart_hr"],
            name="Heart Rate"
        )

        legend = self._plot_widget.addLegend(offset=(10, 10))
        legend.setLabelTextColor(QColor(self._theme["text_secondary"]))

        self._plot_widget.setLabel(
            "left", "Steps", color=self._theme["text_secondary"]
        )
        self._plot_widget.setLabel(
            "bottom", "Date", color=self._theme["text_secondary"]
        )
        self._plot_widget.getAxis("left").setTextPen(
            QColor(self._theme["text_secondary"])
        )
        self._plot_widget.getAxis("bottom").setTextPen(
            QColor(self._theme["text_secondary"])
        )

        layout.addWidget(self._plot_widget, stretch=1)

        self._no_data_label = QLabel("No historical data yet")
        self._no_data_label.setFont(Fonts.BODY)
        self._no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_data_label.setStyleSheet(
            f"color: {self._theme['text_muted']};"
        )
        self._no_data_label.hide()

    def _on_filter_changed(self, text: str) -> None:
        """Handle filter dropdown change."""
        filter_map = {
            "Day": "1d",
            "7 Days": "7d",
            "Month": "30d",
            "Year": "365d",
            "All": "all",
        }
        self._current_filter = filter_map.get(text, "7d")
        self._title_label.setText(f"History ({text})")
        logger.debug(f"Filter changed to: {self._current_filter}")
        self.filter_changed.emit(self._current_filter)

    def get_filter(self) -> str:
        """Get current filter."""
        return self._current_filter

    def update_data(self, dates: list, steps: list, heart_rates: list) -> None:
        """
        Update chart with new data.

        Args:
            dates: List of date strings (YYYY-MM-DD).
            steps: List of step counts (one per day).
            heart_rates: List of average heart rates per day.
        """
        logger.debug(f"ChartWidget.update_data: dates={dates}, steps={steps}, heart_rates={heart_rates}")
        if not dates:
            self._no_data_label.show()
            self._steps_bar.setOpts(x=[], height=[])
            self._hr_line.setData([], [])
            return

        self._no_data_label.hide()

        x_values = list(range(len(dates)))
        self._steps_bar.setOpts(x=x_values, height=steps)

        hr_normalized = []
        max_steps = max(steps) if steps else 1
        for hr in heart_rates:
            if hr > 0:
                normalized = (hr / 200) * max_steps
                hr_normalized.append(normalized)
            else:
                hr_normalized.append(0)

        self._hr_line.setData(x_values, hr_normalized)

        tick_strings = []
        for d in dates:
            try:
                dt = datetime.strptime(d, "%Y-%m-%d")
                tick_strings.append(dt.strftime("%m/%d"))
            except ValueError:
                tick_strings.append(d)

        if tick_strings:
            x_axis = self._plot_widget.getAxis("bottom")
            ticks = [(i, tick_strings[i] if i < len(tick_strings) else "")
                    for i in range(len(tick_strings))]
            x_axis.setTicks([ticks])
            
            if len(dates) > 1:
                self._plot_widget.setXRange(-0.5, len(dates) - 0.5)

    def refresh_theme(self, is_dark: bool = True) -> None:
        """Refresh chart theme."""
        self._theme = get_theme(is_dark)
        self._setup_ui()


class MainWindow(QMainWindow):
    """
    Main application window for PineTime Dashboard.
    """

    def __init__(self, ble_client, database, parent=None):
        super().__init__(parent)
        self._ble_client = ble_client
        self._db = database
        self._theme = get_theme()
        self._sync_worker: Optional[BLESyncWorker] = None
        self._last_sync_time: Optional[datetime] = None
        self._current_steps: int = 0

        self.setWindowTitle("PineTime Dashboard")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)

        self._setup_ui()
        self._setup_menu()
        self._load_initial_data()
        self._update_sync_timer()

        self._connection_status.restart_requested.connect(self._on_restart_device)
        self._chart_widget.filter_changed.connect(self._on_chart_filter_changed)

        if self._db.has_paired_device():
            paired = self._db.get_paired_device()
            self._connection_status.set_connected(False, paired['name'])
            QTimer.singleShot(500, self._auto_connect)
        else:
            QTimer.singleShot(500, self._show_pairing_dialog)

    def _setup_ui(self) -> None:
        """Set up the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 8)
        main_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        self._connection_status = ConnectionStatus()
        header_layout.addWidget(self._connection_status, stretch=1)

        self._sync_button = SyncButton()
        self._sync_button.clicked.connect(self._on_sync_clicked)
        header_layout.addWidget(self._sync_button)

        main_layout.addLayout(header_layout)

        stats_layout = QGridLayout()
        stats_layout.setSpacing(12)

        self._steps_card = StatCard("Steps", "today")
        self._steps_card.set_unit("Goal: 10,000")
        stats_layout.addWidget(self._steps_card, 0, 0)

        self._hr_card = StatCard("Heart Rate", "BPM")
        stats_layout.addWidget(self._hr_card, 0, 1)

        main_layout.addLayout(stats_layout)

        self._chart_widget = ChartWidget()
        main_layout.addWidget(self._chart_widget, stretch=1)

        footer_layout = QHBoxLayout()

        self._status_message = StatusMessage()
        footer_layout.addWidget(self._status_message, stretch=1)

        self._last_sync_label = QLabel("Last sync: Never")
        self._last_sync_label.setFont(Fonts.LABEL)
        self._last_sync_label.setStyleSheet(
            f"color: {self._theme['text_muted']};"
        )
        footer_layout.addWidget(self._last_sync_label)

        main_layout.addLayout(footer_layout)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

    def _setup_menu(self) -> None:
        """Set up application menu."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        pair_action = QAction("Pair Device...", self)
        pair_action.setShortcut("Ctrl+P")
        pair_action.triggered.connect(self._show_pairing_dialog)
        file_menu.addAction(pair_action)

        unpair_action = QAction("Unpair Device", self)
        unpair_action.triggered.connect(self._on_unpair_device)
        file_menu.addAction(unpair_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        settings_menu = menubar.addMenu("Settings")

        settings_action = QAction("Preferences...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._show_settings)
        settings_menu.addAction(settings_action)

        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _load_initial_data(self) -> None:
        """Load initial data from database."""
        today_stats = self._db.get_today_stats()
        if today_stats:
            self._steps_card.set_value(today_stats.steps)
            if today_stats.steps > 0:
                self._steps_card.set_progress(today_stats.steps, 10000)

            if today_stats.heart_rate_avg > 0:
                self._hr_card.set_value(int(today_stats.heart_rate_avg))

        self._update_chart()

    def _update_chart(self, filter_value: Optional[str] = None) -> None:
        """Update the history chart."""
        if filter_value is None:
            filter_value = self._chart_widget.get_filter()

        days_map = {
            "1d": 1,
            "7d": 7,
            "30d": 30,
            "365d": 365,
            "all": 3650,
        }
        days = days_map.get(filter_value, 7)

        stats = self._db.get_daily_stats(days=days)
        logger.info(f"_update_chart: filter={filter_value}, days={days}, stats_count={len(stats)}")
        if stats:
            dates = [s.date for s in reversed(stats)]
            steps = [s.steps for s in reversed(stats)]
            hr_avg = [int(s.heart_rate_avg) if s.heart_rate_avg > 0 else 0
                     for s in reversed(stats)]
            logger.info(f"_update_chart: dates={dates}, steps={steps}")
            self._chart_widget.update_data(dates, steps, hr_avg)

    def _on_chart_filter_changed(self, filter_value: str) -> None:
        """Handle chart filter change."""
        self._update_chart(filter_value)

    def _update_sync_timer(self) -> None:
        """Update last sync time display."""
        last_sync = self._db.get_last_sync()
        if last_sync and last_sync.get("success"):
            try:
                sync_time = datetime.fromisoformat(last_sync["synced_at"])
                self._last_sync_time = sync_time
                self._update_last_sync_label()
            except (ValueError, KeyError):
                pass

        QTimer.singleShot(60000, self._update_sync_timer)

    def _update_last_sync_label(self) -> None:
        """Update the last sync time label."""
        if self._last_sync_time:
            delta = datetime.now() - self._last_sync_time

            if delta.total_seconds() < 60:
                text = "Last sync: Just now"
            elif delta.total_seconds() < 3600:
                minutes = int(delta.total_seconds() / 60)
                text = f"Last sync: {minutes} min ago"
            elif delta.total_seconds() < 86400:
                hours = int(delta.total_seconds() / 3600)
                text = f"Last sync: {hours} hour{'s' if hours > 1 else ''} ago"
            else:
                text = f"Last sync: {self._last_sync_time.strftime('%Y-%m-%d')}"

            self._last_sync_label.setText(text)

    def _auto_connect(self) -> None:
        """Auto-connect to paired device on startup."""
        paired = self._db.get_paired_device()
        if paired:
            logger.info(f"Auto-connecting to {paired['name']}...")
            self._status_bar.showMessage(f"Connecting to {paired['name']}...")
            self._on_sync_clicked()

    def _on_restart_device(self) -> None:
        """Handle restart device request."""
        QMessageBox.information(
            self,
            "Restart PineTime",
            "To restart the PineTime:\n\n"
            "1. Hold the side button for ~8 seconds\n"
            "2. Wait until the PineTime logo turns blue\n"
            "3. The watch will restart automatically\n\n"
            "Note: InfiniTime does not support remote restart via BLE."
        )

    def _show_pairing_dialog(self) -> None:
        """Show the device pairing dialog."""
        if self._sync_button.is_syncing():
            return

        dialog = DeviceSelectionDialog(self._ble_client, self._db, self)

        paired = self._db.get_paired_device()
        if paired:
            self._connection_status.set_connected(False, paired['name'])
            self._connection_status.set_battery_level(-1)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            device_info = dialog.get_selected_device()
            if device_info:
                address, name = device_info
                self._db.set_paired_device(address, name)
                logger.info(f"Paired with device: {name} ({address})")
                self._status_message.show_message(
                    f"Paired with {name}", is_error=False, duration_ms=3000
                )

                QTimer.singleShot(500, self._auto_connect)

    def _on_unpair_device(self) -> None:
        """Handle unpair device action."""
        paired = self._db.get_paired_device()
        if paired:
            reply = QMessageBox.question(
                self,
                "Unpair Device",
                f"Unpair from {paired['name']} ({paired['address']})?\n\n"
                "You can pair again later from the File menu.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._db.clear_paired_device()
                self._connection_status.set_connected(False)
                self._connection_status.set_battery_level(-1)
                self._steps_card.set_value(None)
                self._hr_card.set_value(None)
                self._status_message.show_message("Device unpaired", is_error=False)
                logger.info("Device unpaired")

    @pyqtSlot()
    def _on_sync_clicked(self) -> None:
        """Handle sync button click."""
        if self._sync_button.is_syncing():
            return

        paired = self._db.get_paired_device()
        if not paired:
            self._show_pairing_dialog()
            return

        heart_rate_enabled = self._db.get_setting('heart_rate_enabled') != 'false'
        clear_steps = self._db.get_setting('clear_steps_after_sync') != 'false'

        self._status_bar.showMessage("Starting sync...")
        self._sync_button.set_syncing(True)

        self._sync_worker = BLESyncWorker(
            self._ble_client, self,
            paired_address=paired['address'],
            heart_rate_enabled=heart_rate_enabled,
            clear_steps=clear_steps
        )
        self._sync_worker.progress.connect(self._on_sync_progress)
        self._sync_worker.data_fetched.connect(self._on_data_fetched)
        self._sync_worker.finished.connect(self._on_sync_finished)
        self._sync_worker.start()

    @pyqtSlot(str)
    def _on_sync_progress(self, message: str) -> None:
        """Handle sync progress updates."""
        self._status_bar.showMessage(message)

    @pyqtSlot(int, int, int, str)
    def _on_data_fetched(self, steps: int, heart_rate: int,
                         battery: int, firmware: str) -> None:
        """Handle fetched data."""
        self._connection_status.set_connected(
            True, "InfiniTime", firmware
        )
        if battery >= 0:
            self._connection_status.set_battery_level(battery)

        if heart_rate > 0:
            self._hr_card.set_value(heart_rate)

        self._steps_card.set_value(steps)
        if steps > 0:
            self._steps_card.set_progress(steps, 10000)

    @pyqtSlot(bool, str)
    def _on_sync_finished(self, success: bool, message: str) -> None:
        """Handle sync completion."""
        self._sync_button.set_syncing(False)

        if success:
            self._status_bar.showMessage("Sync completed - steps cleared on watch", 3000)
            self._status_message.show_message(
                "Sync completed. Steps cleared on watch.", is_error=False
            )

            steps = self._steps_card.get_value()
            heart_rate = self._hr_card.get_value()

            battery_text = self._connection_status._battery_label.text()
            battery = -1
            if "Battery:" in battery_text:
                try:
                    battery = int(battery_text.split(":")[1].strip().replace("%", ""))
                except (ValueError, IndexError):
                    pass

            self._db.sync_data(
                steps=steps if steps else 0,
                heart_rate=heart_rate,
                battery_level=battery,
            )

            self._current_steps = steps if steps else 0
            self._steps_card.set_value(self._current_steps)

            self._update_chart()
            self._update_last_sync_label()
        else:
            self._status_bar.showMessage("Sync failed", 3000)
            self._status_message.show_message(message, is_error=True)

        if self._sync_worker:
            self._sync_worker.deleteLater()
            self._sync_worker = None

    def _show_settings(self) -> None:
        """Show settings dialog."""
        dialog = SettingsDialog(self._db, self._ble_client, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self, settings: dict) -> None:
        """Handle settings changes."""
        logger.info(f"Settings changed: {settings}")

    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About PineTime Dashboard",
            "<h3>PineTime Dashboard</h3>"
            "<p>Step tracking and health monitoring for PineTime smartwatch.</p>"
            "<p>Connects via Bluetooth Low Energy to InfiniTime firmware.</p>"
            "<br>"
            "<small>Version 1.0</small>"
        )

    def closeEvent(self, event) -> None:
        """Handle window close."""
        if self._sync_worker is not None:
            self._sync_worker.stop()
            if self._sync_worker.isRunning():
                self._sync_worker.wait(5000)
            self._sync_worker = None

        if self._ble_client:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                if self._ble_client._client and self._ble_client._client.is_connected:
                    loop.run_until_complete(self._ble_client.disconnect())
                loop.close()
            except Exception as e:
                logger.warning(f"Error disconnecting on close: {e}")

        event.accept()
