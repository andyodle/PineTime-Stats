"""
BLE Client for InfiniTime PineTime smartwatch.

Handles device discovery, connection, and data retrieval using bleak library.
"""

import asyncio
import struct
import logging
from typing import Optional, Callable, Any, List, Tuple
from dataclasses import dataclass

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .constants import (
    INFINTIME_DEVICE_NAME,
    STEP_COUNT_CHAR,
    HEART_RATE_MEASUREMENT_CHAR,
    BATTERY_LEVEL_CHAR,
    FIRMWARE_VERSION_CHAR,
    MOTION_SERVICE,
    HEART_RATE_SERVICE,
    BATTERY_SERVICE,
    CONNECTION_TIMEOUT,
    SCAN_TIMEOUT,
)

logger = logging.getLogger(__name__)


@dataclass
class PineTimeData:
    """Data retrieved from PineTime."""
    steps: int
    heart_rate: Optional[int]
    battery_level: Optional[int]
    firmware_version: Optional[str]


@dataclass
class DiscoveredDevice:
    """A discovered BLE device."""
    address: str
    name: str
    rssi: int
    device: BLEDevice


class PineTimeBLEError(Exception):
    """Base exception for PineTime BLE operations."""
    pass


class DeviceNotFoundError(PineTimeBLEError):
    """Raised when InfiniTime device is not found."""
    pass


class ConnectionError(PineTimeBLEError):
    """Raised when connection to PineTime fails."""
    pass


class PineTimeBLEClient:
    """
    BLE client for communicating with PineTime running InfiniTime firmware.

    Usage:
        async with PineTimeBLEClient() as client:
            data = await client.get_all_data()
            print(f"Steps: {data.steps}, HR: {data.heart_rate}")
    """

    def __init__(self, device_address: Optional[str] = None):
        """
        Initialize the BLE client.

        Args:
            device_address: Specific MAC address of PineTime.
                          If None, will scan for device named 'InfiniTime'.
        """
        self._device_address = device_address
        self._client: Optional[BleakClient] = None
        self._device: Optional[BLEDevice] = None

    async def scan(self, timeout: float = SCAN_TIMEOUT) -> BLEDevice:
        """
        Scan for InfiniTime device.

        Args:
            timeout: Scan duration in seconds.

        Returns:
            BLEDevice object for the found PineTime.

        Raises:
            DeviceNotFoundError: If no InfiniTime device is found.
        """
        logger.info(f"Scanning for '{INFINTIME_DEVICE_NAME}' for {timeout}s...")

        devices = await BleakScanner.discover(timeout=timeout, return_adv=True)

        for address, device_info in devices.items():
            if isinstance(device_info, tuple):
                ble_device, adv_data = device_info
            else:
                ble_device = device_info
                adv_data = None

            name = ble_device.name

            if not name and adv_data:
                name = getattr(adv_data, 'local_name', None)

            if not name and adv_data:
                platform_data = getattr(adv_data, 'platform_data', None)
                if platform_data and len(platform_data) > 1:
                    name = platform_data[1].get('Alias', None)

            if name == INFINTIME_DEVICE_NAME:
                logger.info(f"Found device: {name} at {address}")
                self._device = ble_device
                return self._device

        raise DeviceNotFoundError(
            f"Could not find '{INFINTIME_DEVICE_NAME}' device. "
            f"Make sure your PineTime is nearby and InfiniTime is running."
        )

    async def connect(self, device: Optional[BLEDevice] = None) -> None:
        """
        Connect to PineTime.

        Args:
            device: BLEDevice to connect to. If None, scans for device.

        Raises:
            ConnectionError: If connection fails.
        """
        if device is None:
            if self._device is None:
                device = await self.scan()
            else:
                device = self._device

        if self._device is None:
            self._device = device

        logger.info(f"Connecting to {device.address}...")

        try:
            self._client = BleakClient(
                device,
                timeout=CONNECTION_TIMEOUT,
            )
            await self._client.connect()
            logger.info("Connected successfully")

            if not self._client.is_connected:
                raise ConnectionError("Connection established but not connected")

        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from PineTime."""
        if self._client and self._client.is_connected:
            logger.info("Disconnecting...")
            await self._client.disconnect()
        self._client = None

    async def scan_all_devices(self, timeout: float = SCAN_TIMEOUT) -> List[DiscoveredDevice]:
        """
        Scan for all nearby BLE devices.

        Args:
            timeout: Scan duration in seconds.

        Returns:
            List of DiscoveredDevice objects.
        """
        logger.info(f"Scanning for all devices for {timeout}s...")

        devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
        discovered = []

        for address, device_info in devices.items():
            if isinstance(device_info, tuple):
                ble_device, adv_data = device_info
            else:
                ble_device = device_info
                adv_data = None

            name = ble_device.name

            if not name and adv_data:
                name = getattr(adv_data, 'local_name', None)

            if not name and adv_data:
                platform_data = getattr(adv_data, 'platform_data', None)
                if platform_data and len(platform_data) > 1:
                    name = platform_data[1].get('Alias', None)

            rssi = 0
            if adv_data:
                rssi = getattr(adv_data, 'rssi', 0)

            discovered.append(DiscoveredDevice(
                address=address,
                name=name or "Unknown",
                rssi=rssi,
                device=ble_device,
            ))
            logger.debug(f"Found device: {name or 'Unknown'} at {address} (RSSI: {rssi})")

        discovered.sort(key=lambda d: d.rssi, reverse=True)
        logger.info(f"Found {len(discovered)} devices")
        return discovered

    async def connect_by_address(self, address: str, timeout: float = CONNECTION_TIMEOUT) -> None:
        """
        Connect to a device by its MAC address.

        Args:
            address: MAC address of the device.
            timeout: Connection timeout in seconds.

        Raises:
            ConnectionError: If connection fails.
        """
        logger.info(f"Connecting to {address}...")

        try:
            self._client = BleakClient(
                address,
                timeout=timeout,
            )
            await self._client.connect()
            logger.info("Connected successfully")

            if not self._client.is_connected:
                raise ConnectionError("Connection established but not connected")

        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}") from e

    async def clear_steps(self) -> bool:
        """
        Clear step count on PineTime by writing 0 to the characteristic.

        This is done after successfully syncing data to the database.

        Returns:
            True if steps were cleared, False otherwise.
        """
        if not self._client or not self._client.is_connected:
            raise ConnectionError("Not connected to device")

        try:
            step_bytes = struct.pack("<I", 0)
            await self._client.write_gatt_char(STEP_COUNT_CHAR, step_bytes)
            logger.info("Steps cleared on PineTime")
            return True
        except Exception as e:
            logger.warning(f"Failed to clear steps: {e}")
            return False

    async def _read_characteristic(self, uuid: str) -> Optional[bytearray]:
        """
        Read a characteristic value.

        Args:
            uuid: Characteristic UUID.

        Returns:
            Raw byte data or None if read fails.
        """
        if not self._client or not self._client.is_connected:
            raise ConnectionError("Not connected to device")

        try:
            return await self._client.read_gatt_char(uuid)
        except Exception as e:
            logger.warning(f"Failed to read {uuid}: {e}")
            return None

    async def get_steps(self) -> int:
        """
        Get step count from PineTime.

        Returns:
            Current step count (uint32).
        """
        data = await self._read_characteristic(STEP_COUNT_CHAR)
        if data is None:
            return 0

        try:
            steps = struct.unpack("<I", bytes(data))[0]
            return steps
        except struct.error as e:
            logger.error(f"Failed to parse step count: {e}")
            return 0

    async def get_heart_rate(self) -> Optional[int]:
        """
        Get current heart rate from PineTime.

        Returns:
            Heart rate in BPM or None if unavailable.
        """
        data = await self._read_characteristic(HEART_RATE_MEASUREMENT_CHAR)
        if data is None or len(data) < 2:
            return None

        try:
            heart_rate = struct.unpack("<H", bytes(data[1:3]))[0]
            return heart_rate
        except struct.error as e:
            logger.error(f"Failed to parse heart rate: {e}")
            return None

    async def get_battery_level(self) -> Optional[int]:
        """
        Get battery level from PineTime.

        Returns:
            Battery percentage (0-100) or None if unavailable.
        """
        data = await self._read_characteristic(BATTERY_LEVEL_CHAR)
        if data is None or len(data) < 1:
            return None

        return data[0]

    async def get_firmware_version(self) -> Optional[str]:
        """
        Get firmware version from PineTime.

        Returns:
            Version string (e.g., "1.16.0") or None if unavailable.
        """
        data = await self._read_characteristic(FIRMWARE_VERSION_CHAR)
        if data is None:
            return None

        try:
            return bytes(data).decode("utf-8").strip("\x00")
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode firmware version: {e}")
            return None

    async def get_all_data(self) -> PineTimeData:
        """
        Get all available data from PineTime in a single call.

        Returns:
            PineTimeData object with all retrieved values.
        """
        steps, heart_rate, battery, firmware = await asyncio.gather(
            self.get_steps(),
            self.get_heart_rate(),
            self.get_battery_level(),
            self.get_firmware_version(),
        )

        return PineTimeData(
            steps=steps,
            heart_rate=heart_rate,
            battery_level=battery,
            firmware_version=firmware,
        )

    async def start_heart_rate_notifications(
        self,
        callback: Callable[[int], None]
    ) -> None:
        """
        Start receiving heart rate notifications.

        Args:
            callback: Function called with heart rate value when it changes.
        """
        if not self._client or not self._client.is_connected:
            raise ConnectionError("Not connected to device")

        def notification_handler(sender: int, data: bytearray):
            if len(data) >= 2:
                heart_rate = struct.unpack("<H", bytes(data[1:3]))[0]
                callback(heart_rate)

        await self._client.start_notify(
            HEART_RATE_MEASUREMENT_CHAR,
            notification_handler
        )
        logger.info("Started heart rate notifications")

    async def stop_notifications(self) -> None:
        """Stop all notifications."""
        if self._client and self._client.is_connected:
            try:
                await self._client.stop_notify(HEART_RATE_MEASUREMENT_CHAR)
                logger.info("Stopped notifications")
            except Exception as e:
                logger.warning(f"Error stopping notifications: {e}")

    async def __aenter__(self) -> "PineTimeBLEClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()


async def scan_for_pinetime(timeout: float = SCAN_TIMEOUT) -> BLEDevice:
    """
    Convenience function to scan for PineTime.

    Args:
        timeout: Scan duration in seconds.

    Returns:
        BLEDevice object for found PineTime.

    Raises:
        DeviceNotFoundError: If device not found.
    """
    async with PineTimeBLEClient() as client:
        return await client.scan(timeout)


async def test_connection() -> bool:
    """
    Test BLE connection to PineTime.

    Returns:
        True if connection successful, False otherwise.
    """
    try:
        async with PineTimeBLEClient() as client:
            device = await client.scan()
            await client.connect(device)
            data = await client.get_all_data()
            logger.info(f"Connection test successful: {data}")
            return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
