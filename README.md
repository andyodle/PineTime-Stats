# PineTime Step Tracking Dashboard

A Python desktop application for tracking steps and heart rate data from the PineTime smartwatch running InfiniTime firmware.

## Summary

PineTime Step Tracking Dashboard is a PyQt6-based desktop application that connects to the PineTime smartwatch via Bluetooth Low Energy (BLE) and displays real-time step counting and heart rate monitoring with historical statistics. The application uses SQLite for local data persistence and provides a graphical interface with charts and detailed analytics.

### Features
- Real-time step and heart rate monitoring from PineTime smartwatch
- Historical data visualization with charts
- Daily statistics tracking
- Configurable database paths for data storage
- Support for dark and light themes
- Verbose logging mode for debugging
- Runs natively on Python 3.9+

### Requirements

- Python 3.9 or higher
- PineTime smartwatch with InfiniTime firmware (v1.7+ recommended)
- Bluetooth adapter with BLE support
- pip (Python package installer)

### Dependencies

- `bleak>=0.21.0` - Bluetooth Low Energy communication
- `PyQt6>=6.5.0` - GUI framework
- `pyqtgraph>=0.13.3` - Charting library (embedded in PyQt6)
- SQLite3 - Built-in Python module for database storage

## Building the Application

### Prerequisites
- Python 3.9+ installed on your system
- A virtual environment (recommended)

### Setup and Installation

```bash
# Clone or navigate to the project directory
cd /path/to/PineTime/StatsApp

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Test the application
python main.py --help
```

## Running the Application

### Basic Usage

```bash
python main.py
```

### Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--db-paths PATH` | SQLite database file path | `--db-path steps.db` |
| `--verbose` | Enable verbose logging | `--verbose` |
| `--theme` | Display theme (dark/light) | `--theme dark` |

### Running with Custom Configuration

```bash
# Single database path
python main.py --db-paths /home/user/.pinetime/stats.db --theme dark --verbose

# Multiple database paths
python main.py --db-paths /data1.db --db-paths /data2.db
```

## Testing the Application

### Automated Testing

The application can be tested programmatically:

```bash
# Run unit tests (if test suite exists)
python -m pytest tests/ -v

# Test BLE connection
python main.py --db-paths test.db --verbose
```

### Manual Testing Checklist

1. **BLE Connection**: Verify the app can discover and connect to a PineTime smartwatch
2. **Data Sync**: Confirm step and heart rate data is received and stored in the database
3. **GUI Display**: Check that charts and statistics display correctly
4. **Theme Switching**: Verify dark/light theme transitions work properly
5. **Persistence**: Ensure data persists across application restarts

### Debug Mode

For troubleshooting, use verbose logging:

```bash
python main.py --db-paths /path/to/your.db --verbose
```

## Package Installation (DEB)

### Generating DEB Package

The project includes a build script to create a Debian package:

```bash
# Navigate to the project root
cd /path/to/PineTime/StatsApp

# Build the DEB package
./build-deb.sh
```

This script will:
1. Create a temporary package directory structure
2. Copy all application files and dependencies
3. Generate the Debian package in the `output/` directory

### Installation from DEB Package

```bash
# Install the generated DEB package
sudo dpkg -i output/pinetime-stats_1.0_amd64.deb

# If dependency issues occur, fix with:
apt-get install -f

# Or update cache and reinstall
sudo apt-get update
sudo dpkg -i output/pinetime-stats_1.0_amd64.deb
```

### Automatic Package Creation with apt

To create a proper `.deb` package with automatic installation:

1. Install required build tools:
```bash
sudo apt-get update
sudo apt-get install -y debhelper dh-make debhelper-compat debian-devscripts python3-virtualenv
```

2. Run the build script which creates the package in `output/`:
```bash
./build-deb.sh
```

3. Install using the standard DEB package manager:
```bash
sudo dpkg -i output/pinetime-stats_*.deb
```

### Verifying Installation

```bash
# Check installation
dpkg -l | grep pinetime-stats

# Check desktop file installation
ls /usr/share/applications/pinetime-stats.desktop

# Launch the application
pinetime-stats
```

## Troubleshooting

### BLE Connection Issues

- Ensure Bluetooth is enabled and the PineTime is within range
- Verify the firmware version on your PineTime (v1.7+ recommended)
- Check that your Bluetooth adapter supports BLE

### Permission Errors

```bash
# If permission errors occur during package installation
sudo apt-get install -f
sudo apt-get update
```

### Application Won't Start

1. Check Python version: `python --version`
2. Verify dependencies are installed: `pip install -r requirements.txt`
3. Check the database file path is writable
4. Run with `--verbose` flag for detailed error messages

## Project Structure

```
PineTime/StatsApp/
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
├── build-deb.sh        # DEB package build script
├── pinetime-stats.desktop  # Desktop launch file
├── scratchpad.appdata.xml # AppStream metadata
├── db/                 # Database module
│   ├── repository.py   # Database operations
│   └── schema.py       # Database schema definitions
├── ui/                # UI module
│   ├── main_window.py  # Main application window
│   └── styles.py       # Theme styles
└── ble/               # BLE client module
    └── client.py       # PineTime BLE communication
```

## License

MIT License - See LICENSE file for details.
