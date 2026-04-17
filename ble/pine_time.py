"""
PineTime Bluetooth operations for sync, pairing, connecting, and settings.

This module contains BLE workers and utilities for communicating with
PineTime smartwatch running InfiniTime firmware.
"""

import asyncio
import logging
import struct
import uuid
from typing import Optional, Callable

from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot

from .client import PineTimeBLEClient

logger = logging.getLogger(__name__)

BLE_FS_SERVICE_UUID = uuid.UUID("0000febb-0000-1000-8000-00805f9b34fb")
BLE_FS_TRANSFER_UUID = uuid.UUID("adaf0200-4669-6c65-5472-616e73666572")


class BLESyncWorker(QThread):
    """
    Background worker for BLE sync operations.
    Runs in separate thread to avoid blocking UI.
    """

    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    data_fetched = pyqtSignal(int, int, int, str)

    def __init__(self, ble_client: PineTimeBLEClient, parent=None,
                 paired_address: Optional[str] = None,
                 heart_rate_enabled: bool = True,
                 clear_steps: bool = True,
                 sync_time_enabled: bool = True):
        super().__init__(parent)
        self._ble_client = ble_client
        self._paired_address = paired_address
        self._heart_rate_enabled = heart_rate_enabled
        self._clear_steps = clear_steps
        self._sync_time_enabled = sync_time_enabled
        self._loop: Optional[asyncio.AbstractEventLoop] = None
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
                try:
                    self._loop.run_until_complete(
                        self._ble_client.disconnect()
                    )
                except:
                    pass
                return

            if self._sync_time_enabled:
                self.progress.emit("Syncing time to PineTime...")
                time_synced = self._loop.run_until_complete(
                    self._ble_client.set_current_time()
                )
                if time_synced:
                    self.progress.emit("Time synced to PineTime")

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
                if self._loop and self._loop.is_running():
                    self._loop.run_until_complete(
                        self._ble_client.disconnect()
                    )
            except:
                pass
            if self._loop:
                self._loop.close()

    def stop(self) -> None:
        """Stop the worker."""
        self._stop_event = True


class DeviceScanWorker(QThread):
    """Background worker for scanning BLE devices."""

    devices_found = pyqtSignal(list)
    scan_error = pyqtSignal(str)
    scan_complete = pyqtSignal()

    def __init__(self, ble_client: PineTimeBLEClient, parent=None):
        super().__init__(parent)
        self._ble_client = ble_client
        self._loop: Optional[asyncio.AbstractEventLoop] = None

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
            if self._loop:
                self._loop.close()
            self.scan_complete.emit()


class PineTimeSettings:
    """Handler for saving settings to PineTime via BLE FS."""

    BLE_FS_SERVICE_UUID = uuid.UUID("0000febb-0000-1000-8000-00805f9b34fb")
    BLE_FS_TRANSFER_UUID = uuid.UUID("adaf0200-4669-6c65-5472-616e73666572")
    BLE_FS_VERSION_UUID = uuid.UUID("adaf0100-4669-6c65-5472-616e73666572")

    def __init__(self, ble_client: PineTimeBLEClient):
        """
        Initialize PineTime settings handler.

        Args:
            ble_client: PineTimeBLEClient instance for BLE communication.
        """
        self._ble_client = ble_client

    async def _check_ble_fs_version(self, client) -> Optional[int]:
        """Check BLE FS protocol version."""
        try:
            version_data = await client.read_gatt_char(self.BLE_FS_VERSION_UUID)
            if version_data:
                version = int.from_bytes(version_data[:4], 'little')
                logger.info(f"BLE FS Protocol Version: {version}")
                return version
        except Exception as e:
            logger.debug(f"Could not read BLE FS version: {e}")
        return None

    async def _check_firmware_version(self, client) -> Optional[str]:
        """Check InfiniTime firmware version."""
        try:
            fw_data = await client.read_gatt_char(uuid.UUID("00002a26-0000-1000-8000-00805f9b34fb"))
            if fw_data:
                version = bytes(fw_data).decode('utf-8').strip('\x00')
                logger.info(f"PineTime firmware: {version}")
                return version
        except Exception as e:
            logger.debug(f"Could not read firmware version: {e}")
        return None

    async def save_to_device(self, device_address: str, settings: dict) -> tuple[bool, str]:
        """
        Save settings to PineTime via BLE FS.

        Args:
            device_address: MAC address of the paired device.
            settings: Dictionary with settings to save.

        Returns:
            Tuple of (success: bool, message: str).
        """
        from bleak import BleakClient

        try:
            client = BleakClient(device_address, timeout=10)
            await client.connect()

            services = client.services
            has_ble_fs = False
            for service in services:
                if str(service.uuid).lower() == str(self.BLE_FS_SERVICE_UUID).lower():
                    has_ble_fs = True
                    break

            if not has_ble_fs:
                await client.disconnect()
                time_format = settings.get('time_format', '24h')
                sync_time = settings.get('sync_time_enabled', True)
                return False, (
                    f"BLE FS not available. Please set manually on watch:\n"
                    f"Time format: {time_format}\n"
                    f"Sync time: {'On' if sync_time else 'Off'}"
                )

            ble_fs_version = await self._check_ble_fs_version(client)
            fw_version = await self._check_firmware_version(client)

            time_format = settings.get('time_format', '24h')
            sync_time_enabled = 1 if settings.get('sync_time_enabled', True) else 0

            settings_json = (
                f'{{"settings": {{'
                f'"timeFormat": {1 if time_format == "12h" else 0}, '
                f'"syncTime": {sync_time_enabled}}}}}'
            )
            settings_bytes = settings_json.encode('utf-8')

            file_path = "/settings.json"
            path_len = len(file_path)

            header = bytearray()
            header.append(0x20)
            header.append(0x00)
            header.extend(struct.pack('<H', path_len))
            header.extend(struct.pack('<I', 0))
            header.extend(struct.pack('<Q', 0))
            header.extend(struct.pack('<I', len(settings_bytes)))

            full_header = header + file_path.encode('utf-8')
            await client.write_gatt_char(self.BLE_FS_TRANSFER_UUID, full_header, response=True)

            await client.write_gatt_char(self.BLE_FS_TRANSFER_UUID, settings_bytes, response=True)

            await client.disconnect()
            sync_on = "On" if settings.get('sync_time_enabled', True) else "Off"
            return True, f"Settings saved to PineTime!\nTime format: {time_format}\nSync time: {sync_on}"

        except Exception as e:
            error_str = str(e)
            time_format = settings.get('time_format', '24h')
            sync_on = "On" if settings.get('sync_time_enabled', True) else "Off"

            if "INSUFFICIENT_AUTHORIZATION" in error_str or "8" in error_str:
                await client.disconnect()
                logger.warning("BLE FS access is disabled on PineTime!")
                return False, (
                    f"BLE FS access is disabled on PineTime!\n\n"
                    f"Enable File Transfer on your watch:\n"
                    f"Settings > Over-the-air > File Transfer > Enable\n\n"
                    f"Manual settings:\n"
                    f"Time format: {time_format}\n"
                    f"Sync time: {sync_on}"
                )

            logger.error(f"Failed to save settings: {e}")
            return False, (
                f"Could not save to watch.\n"
                f"Please set manually:\n"
                f"Time format: {time_format}\n"
                f"Sync time: {sync_on}"
            )

    def save_settings_to_watch(self, device_address: str, settings: dict) -> tuple[bool, str]:
        """
        Synchronous wrapper for saving settings to PineTime.

        Args:
            device_address: MAC address of the paired device.
            settings: Dictionary with settings to save.

        Returns:
            Tuple of (success: bool, message: str).
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success, message = loop.run_until_complete(
                self.save_to_device(device_address, settings)
            )
            return success, message
        finally:
            loop.close()
