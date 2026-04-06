# EnvoyStats

Display the status of your Enphase Envoy (IQ Gateway) solar system in your macOS menu bar using [xbar](https://xbarapp.com/).

Queries your Envoy on the local network over HTTPS using token-based authentication. No external dependencies — uses only Python 3 standard library and macOS Keychain for secure token storage.

<!-- TODO: Add new screenshots here -->

## Menu Bar Display

The menu bar icon changes based on your power state:

| Icon | Meaning |
|------|---------|
| ☀️   | Exporting to grid, producing above 50% of system capacity |
| ⛅   | Exporting to grid, producing below 50% of system capacity |
| 🔌   | Importing from grid |

The dropdown shows:

- Current production (watts)
- House consumption with solar percentage
- Grid import/export with direction arrows
- Energy totals (today, this week, lifetime)
- Per-panel output range and system yield
- Voltage per phase

## Migrating from v1 (Ruby script)

Enphase firmware D8.x changed the Envoy (IQ Gateway) to require HTTPS and token-based authentication. The previous Ruby script used HTTP and digest auth which no longer works. This version has been rewritten in Python 3 with:

- HTTPS support (with self-signed certificate handling)
- JWT token authentication via Enphase cloud
- Secure token storage in macOS Keychain (no plaintext files)
- Built-in `--setup` command for token management

If upgrading, remove the old `solar.4m.rb` from your plugins directory and follow the setup steps below.

## Setup

### 1. Install xbar

Download and install from [xbarapp.com](https://xbarapp.com/).

### 2. Copy the script

Download `solar.4m.py` and place it in your xbar plugins directory:

```
~/Library/Application Support/xbar/plugins/
```

Make it executable:

```bash
chmod +x ~/Library/Application\ Support/xbar/plugins/solar.4m.py
```

### 3. Configure

Edit the script and set your Envoy's IP address and system size:

```python
ENVOY_IP = "ENTER_YOUR_ENVOY_IP"
SYSTEM_SIZE_WATTS = 6000  # Your system size in watts
```

To find your Envoy's IP address:

1. Open the Enlighten app on your device.
2. Tap Menu > Devices > Envoy > Connect Locally > Connect.

Alternatively, check your router's connected devices list.

### 4. Authenticate

Newer Envoy firmware requires a JWT token for API access. The script fetches this from Enphase and stores it securely in your macOS Keychain.

Run the setup command:

```bash
python3 ~/Library/Application\ Support/xbar/plugins/solar.4m.py --setup
```

This will prompt for your Enphase account credentials (the same ones you use for the Enlighten app), fetch a token, and store it in Keychain. The token is valid for 1 year — re-run the setup command to refresh it.

### 5. Refresh rate

xbar uses the filename to determine how often the script runs. The default `solar.4m.py` runs every 4 minutes. Rename the file to change the interval (e.g. `solar.2m.py` for every 2 minutes). Don't go below 1 minute to avoid overloading your Envoy.
