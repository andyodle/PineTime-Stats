"""
Device selection dialog for pairing with PineTime.
"""

import asyncio
import logging
from typing import Optional, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QProgressBar, QDialogButtonBox, QMessageBox,
    QLineEdit, QCompleter, QApplication, QWidget, QGroupBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor

from .styles import get_theme, Fonts, get_font

logger = logging.getLogger(__name__)


class DeviceScanWorker(QThread):
    """Background worker for scanning BLE devices."""

    devices_found = pyqtSignal(list)
    scan_error = pyqtSignal(str)
    scan_complete = pyqtSignal()

    def __init__(self, ble_client, parent=None):
        super().__init__(parent)
        self._ble_client = ble_client
        self._loop = None

    def run(self) -> None:
        """Execute scan in async loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            logger.info("Starting device scan...")
            devices = self._loop.run_until_complete(
                self._ble_client.scan_all_devices(timeout=10.0)
            )
            logger.info(f"Scan found {len(devices)} devices")
            self.devices_found.emit(devices)

        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.scan_error.emit(str(e))

        finally:
            self._loop.close()
            self.scan_complete.emit()


class DeviceSelectionDialog(QDialog):
    """
    Dialog for selecting and pairing with a PineTime device.
    """

    device_selected = pyqtSignal(str, str)

    def __init__(self, ble_client, db, parent=None):
        super().__init__(parent)
        self._ble_client = ble_client
        self._db = db
        self._theme = get_theme()
        self._scan_worker: Optional[DeviceScanWorker] = None
        self._devices: List = []

        self.setWindowTitle("Select PineTime Device")
        self.setMinimumSize(450, 400)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog layout."""
        layout = QVBoxLayout(self)

        title_label = QLabel("Select your PineTime device to pair")
        title_label.setFont(Fonts.HEADING)
        title_label.setStyleSheet(f"color: {self._theme['text_primary']};")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        self._status_label = QLabel("Click 'Scan' to find nearby devices")
        self._status_label.setFont(Fonts.BODY)
        self._status_label.setStyleSheet(f"color: {self._theme['text_secondary']};")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {self._theme['border']};
                border-radius: 4px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: {self._theme['primary']};
            }}
        """)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._device_list = QListWidget()
        self._device_list.setStyleSheet(f"""
            QListWidget {{
                background: {self._theme['surface']};
                border: 1px solid {self._theme['border']};
                border-radius: 8px;
                color: {self._theme['text_primary']};
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {self._theme['border']};
            }}
            QListWidget::item:selected {{
                background: {self._theme['primary']};
                color: {self._theme['background']};
            }}
        """)
        self._device_list.itemDoubleClicked.connect(self._on_device_selected)
        layout.addWidget(self._device_list, stretch=1)

        manual_layout = QHBoxLayout()
        manual_label = QLabel("Or enter MAC address:")
        manual_label.setFont(Fonts.LABEL)
        manual_label.setStyleSheet(f"color: {self._theme['text_secondary']};")
        manual_layout.addWidget(manual_label)

        self._mac_input = QLineEdit()
        self._mac_input.setPlaceholderText("AA:BB:CC:DD:EE:FF")
        self._mac_input.setFont(Fonts.BODY)
        self._mac_input.setStyleSheet(f"""
            QLineEdit {{
                background: {self._theme['surface']};
                border: 1px solid {self._theme['border']};
                border-radius: 4px;
                color: {self._theme['text_primary']};
                padding: 6px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self._theme['primary']};
            }}
        """)
        self._mac_input.textChanged.connect(self._on_mac_changed)
        self._mac_input.returnPressed.connect(self._on_pair_manual)
        manual_layout.addWidget(self._mac_input, stretch=1)

        self._pair_manual_button = QPushButton("Pair")
        self._pair_manual_button.setFont(Fonts.BODY_BOLD)
        self._pair_manual_button.setEnabled(False)
        self._pair_manual_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pair_manual_button.setStyleSheet(f"""
            QPushButton {{
                background: {self._theme['success']};
                color: {self._theme['background']};
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: 600;
            }}
            QPushButton:disabled {{
                background: {self._theme['border']};
                color: {self._theme['text_muted']};
            }}
        """)
        self._pair_manual_button.clicked.connect(self._on_pair_manual)
        manual_layout.addWidget(self._pair_manual_button)

        layout.addLayout(manual_layout)

        button_layout = QHBoxLayout()

        self._scan_button = QPushButton("Scan")
        self._scan_button.setFont(Fonts.BODY_BOLD)
        self._scan_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scan_button.setStyleSheet(f"""
            QPushButton {{
                background: {self._theme['primary']};
                color: {self._theme['background']};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {self._theme['primary_variant']};
            }}
            QPushButton:disabled {{
                background: {self._theme['border']};
            }}
        """)
        self._scan_button.clicked.connect(self._on_scan_clicked)
        button_layout.addWidget(self._scan_button)

        button_layout.addStretch()

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)

        ok_button = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText("Pair")
        ok_button.setEnabled(False)
        ok_button.setStyleSheet(f"""
            QPushButton {{
                background: {self._theme['success']};
                color: {self._theme['background']};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
            }}
            QPushButton:disabled {{
                background: {self._theme['border']};
                color: {self._theme['text_muted']};
            }}
        """)

        cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setText("Cancel")
        cancel_button.setStyleSheet(f"""
            QPushButton {{
                background: {self._theme['surface']};
                color: {self._theme['text_primary']};
                border: 1px solid {self._theme['border']};
                border-radius: 6px;
                padding: 10px 20px;
            }}
        """)

        button_layout.addWidget(self._button_box)
        layout.addLayout(button_layout)

    @pyqtSlot()
    def _on_scan_clicked(self) -> None:
        """Handle scan button click."""
        self._scan_button.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._status_label.setText("Scanning for devices...")
        self._device_list.clear()
        self._devices = []

        self._scan_worker = DeviceScanWorker(self._ble_client, self)
        self._scan_worker.devices_found.connect(self._on_devices_found)
        self._scan_worker.scan_error.connect(self._on_scan_error)
        self._scan_worker.scan_complete.connect(self._on_scan_complete)
        self._scan_worker.start()

    @pyqtSlot(list)
    def _on_devices_found(self, devices: list) -> None:
        """Handle devices found."""
        self._devices = devices

        self._device_list.clear()

        infinitime_devices = [d for d in devices if 'InfiniTime' in d.name]

        if infinitime_devices:
            for device in infinitime_devices:
                item = QListWidgetItem(f"{device.name} ({device.address})")
                item.setData(Qt.ItemDataRole.UserRole, (device.address, device.name))
                self._device_list.addItem(item)
        else:
            for device in devices:
                item = QListWidgetItem(f"{device.name} ({device.address}) [RSSI: {device.rssi}]")
                item.setData(Qt.ItemDataRole.UserRole, (device.address, device.name))
                self._device_list.addItem(item)

    @pyqtSlot(str)
    def _on_scan_error(self, error: str) -> None:
        """Handle scan error."""
        self._status_label.setText(f"Scan error: {error}")
        self._status_label.setStyleSheet(f"color: {self._theme['error']};")

    @pyqtSlot()
    def _on_scan_complete(self) -> None:
        """Handle scan complete."""
        self._scan_button.setEnabled(True)
        self._progress_bar.setVisible(False)

        if self._devices:
            self._status_label.setText(
                f"Found {len(self._devices)} devices. Double-click to select."
            )
        else:
            self._status_label.setText("No devices found. Click 'Scan' to try again.")

        self._scan_worker.deleteLater()
        self._scan_worker = None

    def _on_device_selected(self, item: QListWidgetItem) -> None:
        """Handle device selection."""
        self.accept()

    def _on_mac_changed(self, text: str) -> None:
        """Handle MAC address input change."""
        mac_pattern = r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
        import re
        is_valid = bool(re.match(mac_pattern, text.strip()))
        self._pair_manual_button.setEnabled(is_valid)

        if is_valid and not self._device_list.currentItem():
            item = QListWidgetItem(f"Manual: {text.strip()} (InfiniTime)")
            item.setData(Qt.ItemDataRole.UserRole, (text.strip(), "InfiniTime"))
            self._device_list.addItem(item)
            self._device_list.setCurrentItem(item)

    def _on_pair_manual(self) -> None:
        """Handle manual pair button."""
        mac = self._mac_input.text().strip()
        if mac:
            self.accept()

    def _on_accept(self) -> None:
        """Handle accept button."""
        manual_mac = self._mac_input.text().strip()
        if manual_mac:
            self.accept()
            return

        current_item = self._device_list.currentItem()
        if current_item:
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "No Device Selected",
                "Please select a device from the list, scan for devices, or enter a MAC address."
            )

    def get_selected_device(self) -> Optional[tuple]:
        """
        Get the selected device address and name.

        Returns:
            Tuple of (address, name) or None if not selected.
        """
        manual_mac = self._mac_input.text().strip()
        if manual_mac:
            return (manual_mac, "InfiniTime")

        current_item = self._device_list.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None

    def closeEvent(self, event) -> None:
        """Handle dialog close."""
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.terminate()
            self._scan_worker.wait()
        event.accept()


class SettingsDialog(QDialog):
    """Settings dialog for app configuration."""

    settings_changed = pyqtSignal(dict)

    def __init__(self, db, ble_client, parent=None):
        super().__init__(parent)
        self._db = db
        self._ble_client = ble_client
        self._theme = get_theme()
        self._storage_info = {}

        self.setWindowTitle("Settings")
        self.setMinimumSize(450, 500)
        self.setModal(True)

        self._load_settings()
        self._setup_ui()

    def _load_settings(self) -> None:
        """Load current settings from database."""
        self._settings = {
            'clear_steps_after_sync': self._db.get_setting('clear_steps_after_sync') != 'false',
            'heart_rate_enabled': self._db.get_setting('heart_rate_enabled') != 'false',
            'weather_update_enabled': self._db.get_setting('weather_update_enabled') == 'true',
            'weather_update_interval': int(self._db.get_setting('weather_update_interval') or '60'),
        }

    def _setup_ui(self) -> None:
        """Set up the settings UI."""
        layout = QVBoxLayout(self)

        title_label = QLabel("Settings")
        title_label.setFont(Fonts.HEADING)
        title_label.setStyleSheet(f"color: {self._theme['text_primary']};")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        sync_group = self._create_group("Sync Settings")
        sync_layout = QVBoxLayout()

        self._clear_steps_cb = self._create_checkbox(
            "Clear steps after sync",
            "Automatically clear step count on PineTime after syncing"
        )
        self._clear_steps_cb.setChecked(self._settings['clear_steps_after_sync'])
        self._clear_steps_cb.stateChanged.connect(
            lambda s: self._on_setting_changed('clear_steps_after_sync', s == Qt.CheckState.Checked.value)
        )
        sync_layout.addWidget(self._clear_steps_cb)

        self._heart_rate_cb = self._create_checkbox(
            "Enable Heart Rate",
            "Fetch heart rate data during sync"
        )
        self._heart_rate_cb.setChecked(self._settings['heart_rate_enabled'])
        self._heart_rate_cb.stateChanged.connect(
            lambda s: self._on_setting_changed('heart_rate_enabled', s == Qt.CheckState.Checked.value)
        )
        sync_layout.addWidget(self._heart_rate_cb)

        sync_group.layout().addLayout(sync_layout)
        scroll_layout.addWidget(sync_group)

        weather_group = self._create_group("Weather Settings")
        weather_layout = QVBoxLayout()

        self._weather_enabled_cb = self._create_checkbox(
            "Enable Weather Updates",
            "Automatically update weather on PineTime"
        )
        self._weather_enabled_cb.setChecked(self._settings['weather_update_enabled'])
        self._weather_enabled_cb.stateChanged.connect(
            lambda s: self._on_setting_changed('weather_update_enabled', s == Qt.CheckState.Checked.value)
        )
        weather_layout.addWidget(self._weather_enabled_cb)

        interval_layout = QHBoxLayout()
        interval_label = QLabel("Update interval (minutes):")
        interval_label.setFont(Fonts.LABEL)
        interval_label.setStyleSheet(f"color: {self._theme['text_secondary']};")
        interval_layout.addWidget(interval_label)

        from PyQt6.QtWidgets import QSpinBox
        self._weather_interval = QSpinBox()
        self._weather_interval.setMinimum(15)
        self._weather_interval.setMaximum(1440)
        self._weather_interval.setValue(self._settings['weather_update_interval'])
        self._weather_interval.setStyleSheet(f"""
            QSpinBox {{
                background: {self._theme['surface']};
                border: 1px solid {self._theme['border']};
                border-radius: 4px;
                color: {self._theme['text_primary']};
                padding: 4px;
            }}
        """)
        self._weather_interval.valueChanged.connect(
            lambda v: self._on_setting_changed('weather_update_interval', str(v))
        )
        interval_layout.addWidget(self._weather_interval)
        weather_layout.addLayout(interval_layout)

        weather_group.layout().addLayout(weather_layout)
        scroll_layout.addWidget(weather_group)

        storage_group = self._create_group("PineTime Storage")
        storage_layout = QVBoxLayout()

        self._storage_label = QLabel("Click 'Refresh' to fetch storage info")
        self._storage_label.setFont(Fonts.BODY)
        self._storage_label.setStyleSheet(f"color: {self._theme['text_secondary']};")
        self._storage_label.setWordWrap(True)
        storage_layout.addWidget(self._storage_label)

        refresh_btn = QPushButton("Refresh Storage Info")
        refresh_btn.setFont(Fonts.BODY_BOLD)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
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
        """)
        refresh_btn.clicked.connect(self._refresh_storage_info)
        storage_layout.addWidget(refresh_btn)

        storage_group.layout().addLayout(storage_layout)
        scroll_layout.addWidget(storage_group)

        data_group = self._create_group("Data Management")
        data_layout = QVBoxLayout()

        clear_history_btn = QPushButton("Clear Sync History")
        clear_history_btn.setFont(Fonts.BODY_BOLD)
        clear_history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_history_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self._theme['warning']};
                color: {self._theme['background']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #d97706;
            }}
        """)
        clear_history_btn.clicked.connect(self._clear_sync_history)
        data_layout.addWidget(clear_history_btn)

        clear_stats_btn = QPushButton("Clear All Statistics")
        clear_stats_btn.setFont(Fonts.BODY_BOLD)
        clear_stats_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_stats_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self._theme['error']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #dc2626;
            }}
        """)
        clear_stats_btn.clicked.connect(self._clear_all_stats)
        data_layout.addWidget(clear_stats_btn)

        data_group.layout().addLayout(data_layout)
        scroll_layout.addWidget(data_group)

        scroll_layout.addStretch()
        layout.addWidget(scroll_widget, stretch=1)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setFont(Fonts.BODY_BOLD)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self._theme['surface']};
                color: {self._theme['text_primary']};
                border: 1px solid {self._theme['border']};
                border-radius: 6px;
                padding: 10px 20px;
            }}
        """)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _create_group(self, title: str) -> QGroupBox:
        """Create a settings group box."""
        group = QGroupBox(title)
        label_font = get_font(9, 600)
        group.setFont(label_font)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                color: {self._theme['text_primary']};
                border: 1px solid {self._theme['border']};
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
        """)

        inner_layout = QVBoxLayout()
        group.setLayout(inner_layout)
        return group

    def _create_checkbox(self, title: str, tooltip: str = "") -> QWidget:
        """Create a checkbox with label."""
        from PyQt6.QtWidgets import QCheckBox

        cb = QCheckBox(title)
        cb.setFont(Fonts.BODY)
        cb.setStyleSheet(f"""
            QCheckBox {{
                color: {self._theme['text_primary']};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {self._theme['border']};
                border-radius: 4px;
                background: {self._theme['surface']};
            }}
            QCheckBox::indicator:checked {{
                background: {self._theme['primary']};
                border-color: {self._theme['primary']};
            }}
        """)
        if tooltip:
            cb.setToolTip(tooltip)
        return cb

    def _on_setting_changed(self, key: str, value) -> None:
        """Handle setting change."""
        self._settings[key] = value
        self._db.set_setting(key, str(value).lower() if isinstance(value, bool) else str(value))
        self.settings_changed.emit(self._settings)

    def _refresh_storage_info(self) -> None:
        """Fetch storage info from PineTime."""
        from bleak import BleakClient

        self._storage_label.setText("Connecting to PineTime...")
        QApplication.processEvents()

        async def fetch_storage():
            try:
                paired = self._db.get_paired_device()
                if not paired:
                    return "No device paired"

                async with BleakClient(paired['address'], timeout=10) as client:
                    await client.connect()

                    storage_text = "=== PineTime Memory ===\n\n"
                    storage_text += "Internal RAM: 64 KB\n"
                    storage_text += "Internal Flash: 512 KB (Firmware)\n"
                    storage_text += "External SPI Flash: 4 MB (LittleFS)\n\n"

                    try:
                        battery = await client.read_gatt_char('00002a19-0000-1000-8000-00805f9b34fb')
                        storage_text += f"Battery Level: {battery[0]}%\n"
                    except:
                        pass

                    try:
                        firmware = await client.read_gatt_char('00002a26-0000-1000-8000-00805f9b34fb')
                        fw_version = bytes(firmware).decode('utf-8').strip('\x00')
                        storage_text += f"Firmware: {fw_version}\n"
                    except:
                        pass

                    storage_text += "\nNote: BLE FS does not expose\nfree space. Check on watch."

                    await client.disconnect()
                    return storage_text

            except Exception as e:
                return f"Error: {str(e)}"

        async def run_async():
            result = await fetch_storage()
            self._storage_label.setText(result)
            self._storage_label.setStyleSheet(f"color: {self._theme['text_secondary']};")

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_async())
        loop.close()

    def _clear_sync_history(self) -> None:
        """Clear sync history."""
        reply = QMessageBox.question(
            self,
            "Clear Sync History",
            "Are you sure you want to clear all sync history?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = self._db._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sync_log")
                conn.commit()
                QMessageBox.information(self, "Success", "Sync history cleared.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to clear history: {e}")

    def _clear_all_stats(self) -> None:
        """Clear all statistics."""
        reply = QMessageBox.question(
            self,
            "Clear All Statistics",
            "Are you sure you want to clear ALL step and heart rate statistics?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = self._db._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM daily_stats")
                cursor.execute("DELETE FROM sync_log")
                conn.commit()
                QMessageBox.information(self, "Success", "All statistics cleared.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to clear stats: {e}")
