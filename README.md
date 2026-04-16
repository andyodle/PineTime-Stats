# PineTime Step Tracking Dashboard

A desktop application for tracking steps and heart rate data from the PineTime smartwatch running InfiniTime firmware.

## Features

- **Bluetooth Low Energy (BLE) Connection** - Connect to PineTime via Bluetooth
- **Step Tracking** - View daily step count with progress towards goal
- **Heart Rate Monitoring** - Display current and average heart rate
- **Battery Status** - See PineTime battery level
- **Data Persistence** - Store data in SQLite database
- **Historical Charts** - View 7-day step and heart rate history
- **Manual Sync** - Trigger data sync on demand
- **Dark/Light Theme** - Choose your preferred color scheme

## Requirements

- Python 3.9 or higher
- PineTime smartwatch with [InfiniTime firmware](https://github.com/InfiniTimeOrg/InfiniTime) v1.7+
- Bluetooth adapter with BLE support (BlueZ 5.55+ on Linux)

## Installation

### 1. Clone or Download

```bash
cd /path/to/StatsApp
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Bluetooth (Linux)

Ensure your user has permission to access Bluetooth:

```bash
sudo usermod -a -G bluetooth $USER
# Log out and log back in for changes to take effect
```

## Usage

### Basic Usage

```bash
source venv/bin/activate
python main.py
```

### Command Line Options

```bash
python main.py [options]

Options:
  -d, --database PATH   Database file path (default: pinetime_stats.db)
  -v, --verbose         Enable verbose logging
  --dark                Use dark theme (default)
  --light               Use light theme
```

### Examples

```bash
# Use custom database location
python main.py -d ~/Documents/pinetime.db

# Enable verbose debug output
python main.py -v

# Use light theme
python main.py --light
```

## How It Works

### BLE Communication

The app connects to PineTime using the [bleak](https://github.com/hbldh/bleak) library and reads the following data:

| Data | BLE UUID | Format |
|------|----------|--------|
| Step Count | `00030001-78fc-48fe-8e23-433b3a1942d0` | uint32 (4 bytes) |
| Heart Rate | `00002a37-0000-1000-8000-00805f9b34fb` | uint16 (2 bytes) |
| Battery Level | `00002a19-0000-1000-8000-00805f9b34fb` | uint8 (1 byte) |
| Firmware Version | `00002a26-0000-1000-8000-00805f9b34fb` | UTF-8 string |

### Data Storage

Daily statistics are stored in SQLite:

- **daily_stats** - Aggregated daily data (steps, heart rate averages, min/max)
- **sync_log** - Record of all sync operations for debugging

### Sync Process

1. Click "Sync" button or app starts
2. Scan for "InfiniTime" Bluetooth device
3. Connect to PineTime
4. Read current step count, heart rate, and battery level
5. Store data in database
6. Update UI with new values
7. Disconnect

## Project Structure

```
StatsApp/
├── main.py                 # Application entry point
├── requirements.txt         # Python dependencies
├── ble/
│   ├── constants.py        # BLE UUID definitions
│   └── client.py          # BLE client implementation
├── db/
│   ├── schema.py          # SQLite schema
│   └── repository.py      # Database operations
└── ui/
    ├── styles.py          # Theme and styling
    ├── widgets.py         # Custom UI widgets
    └── main_window.py     # Main application window
```

## Troubleshooting

### Device Not Found

- Ensure PineTime is nearby and InfiniTime is running
- Check that Bluetooth is enabled on your computer
- Try running `bluetoothctl scan on` to verify Bluetooth is working

### Connection Fails

- PineTime may have disconnected. Try again.
- Some systems require root privileges for BLE. Try running with `sudo`.
- Check firewall settings if using a firewall.

### No Data Appears

- Make sure you're running InfiniTime v1.7 or later (required for step data)
- The Steps app on PineTime must be running to track steps
- Heart rate requires the Heart Rate app or sensor to be active

## Development

### Running Tests

```bash
source venv/bin/activate
python -c "
import sys
sys.path.insert(0, '.')
# Run individual module tests
from ble.constants import *
from ble.client import *
from db.repository import Database
# ... etc
"
```

### Testing PineTime
```
# Run with hardware (requires PineTime nearby)
python tests/watch_sync_tests.py

# Run without hardware (database tests only)
python tests/watch_sync_tests.py --skip-hardware

# With verbose output
python tests/watch_sync_tests.py -v
```


### Dependencies

- [bleak](https://github.com/hbldh/bleak) - BLE communication
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
- [pyqtgraph](http://www.pyqtgraph.org/) - Charting library

## License

This project is provided as-is for personal use with PineTime smartwatches.

## References

- [InfiniTime Firmware](https://github.com/InfiniTimeOrg/InfiniTime)
- [InfiniTime BLE API Documentation](https://github.com/InfiniTimeOrg/InfiniTime/blob/main/doc/ble.md)
- [InfiniTime Motion Service](https://github.com/InfiniTimeOrg/InfiniTime/blob/main/doc/MotionService.md)
- [Pine64 Wiki - PineTime Development](https://wiki.pine64.org/wiki/PineTime_Development)
