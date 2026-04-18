# PineTime Stats

A desktop application for tracking steps and heart rate data from the PineTime smartwatch running InfiniTime firmware.

## Features

- **Step Tracking**: Sync and display daily step count from PineTime
- **Heart Rate Monitoring**: View current heart rate readings
- **Battery Level**: Monitor PineTime battery status
- **Firmware Info**: Display firmware version
- **Data History**: View step history charts (Day, 7 Days, Month, Year, All)
- **System Tray**: Runs in background with system tray icon
- **Auto-pairing**: Remembers paired PineTime device

## Requirements

- PineTime with InfiniTime firmware (v1.7+ recommended)
- Linux desktop with Bluetooth support
- Python 3.9+
- PyQt6
- pyqtgraph
- bleak (BLE client library)


## Project Structure

```
pinetime-stats/
├── main.py              # Application entry point
├── build-deb.sh         # DEB package builder
├── pinetime-stats.desktop  # Desktop entry file
├── ble/
│   ├── client.py        # BLE communication
│   ├── pine_time.py    # BLE workers
│   └── constants.py    # BLE UUIDs
├── db/
│   ├── repository.py    # Database operations
│   └── schema.py      # Database schema
└── ui/
    ├── main_window.py  # Main application window
    ├── widgets.py    # Custom widgets
    ├── dialogs.py    # Dialog windows
    └── styles.py    # Theme styling
```

## Build

Install Python dependencies:

```bash
pip install PyQt6 pyqtgraph bleak
```

Run the application:

```bash
PYTHONPATH=. python3 main.py
```

Or using the installed command:

```bash
pinetime-stats
```

## Development

### Running Tests

```bash
pytest tests/
```

### Command Line Options

```bash
python main.py -h
```

Options:
- `-d, --database PATH` - Database file path (default: pinetime_stats.db)
- `-v, --verbose` - Enable verbose logging
- `--dark` - Use dark theme (default)
- `--light` - Use light theme

## Building DEB Package

Build the package:

```bash
./build-deb.sh
```

This creates `output/pinetime-stats-1.0.deb`.

## Installing DEB Package

### Option 1: Using dpkg

```bash
sudo dpkg -i output/pinetime-stats-1.0.deb
sudo apt-get install -y -f  # Install missing dependencies
```

### Option 2: Using gdebi

```bash
sudo gdebi output/pinetime-stats-1.0.deb
```

### Option 3: Using apt

```bash
sudo apt install ./output/pinetime-stats-1.0.deb
```

## Uninstalling

```bash
sudo apt remove pinetime-stats
```

Or:

```bash
sudo dpkg -r pinetime-stats
```

## Usage

1. **Launch the app** - Either from application menu or terminal
2. **Pair device** - The app will prompt to scan for PineTime
3. **Enable Bluetooth** on PineTime and set to companion mode
4. **Sync data** - Click "Sync Now" or use tray menu
5. **View stats** - Step count, heart rate, battery, and history charts on main window
6. **Close window** - App minimizes to system tray (use Exit to quit)

## Troubleshooting

### App doesn't launch after installing .deb

Install missing dependencies:

```bash
sudo apt install python3-pyqt6 python3-pyqtgraph python3-bleak bluez
```

### Bluetooth not working

- Ensure Bluetooth is enabled: `sudo systemctl start bluetooth`
- Check permissions: `sudo setcap cap_net_raw+eip $(which python3)`
- Pair PineTime in system Bluetooth settings first

### Database errors

Delete the database file and restart:

```bash
rm ~/.local/share/pinetime-stats/pinetime_stats.db
```