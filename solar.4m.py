#!/usr/bin/env python3

# Solar monitoring xbar plugin for Enphase Envoy (IQ Gateway)
# By rodos@haywood.org
#
# Displays current solar production, consumption and grid import/export.
# Reads JWT token from macOS Keychain.
#
# TOKEN SETUP:
#   The Envoy requires a JWT token from Enphase (valid for 1 year).
#   To fetch or refresh a token, run this script with --setup:
#
#     python3 ~/Library/Application\ Support/xbar/plugins/solar.4m.py --setup
#
#   This will prompt for your Enphase account credentials, fetch a token,
#   and store it securely in the macOS Keychain.

import json
import os
import subprocess
import sys
import ssl
import urllib.error
import urllib.request

KEYCHAIN_ACCOUNT = "envoy-solar"
KEYCHAIN_SERVICE = "envoy-jwt-token"
SCRIPT_PATH = os.path.abspath(__file__)
CONFIG_PATH = os.path.join(os.path.dirname(SCRIPT_PATH), "solar.config.json")


def setup_menu_item():
    """Return an xbar menu item that runs --setup in Terminal when clicked."""
    return f"Run setup...| bash={sys.executable} param1={SCRIPT_PATH} param2=--setup terminal=true size=12"


def load_config():
    """Load config from solar.config.json next to the script."""
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(envoy_ip, system_size_watts):
    """Save config to solar.config.json next to the script."""
    with open(CONFIG_PATH, "w") as f:
        json.dump({"envoy_ip": envoy_ip, "system_size_watts": system_size_watts}, f, indent=2)


def get_token_from_keychain():
    """Retrieve the Envoy JWT token from macOS Keychain."""
    result = subprocess.run(
        ["security", "find-generic-password", "-a", KEYCHAIN_ACCOUNT, "-s", KEYCHAIN_SERVICE, "-w"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def save_token_to_keychain(token):
    """Store the Envoy JWT token in macOS Keychain."""
    subprocess.run(
        ["security", "add-generic-password", "-a", KEYCHAIN_ACCOUNT, "-s", KEYCHAIN_SERVICE, "-w", token, "-U"],
        check=True
    )


def setup_token():
    """Interactive setup: configure Envoy IP, system size, and fetch JWT token."""
    import getpass

    print("Enphase Envoy Setup")
    print("=" * 40)

    # Load existing config for defaults
    existing = load_config()
    default_ip = existing.get("envoy_ip", "") if existing else ""
    default_size = existing.get("system_size_watts", 6000) if existing else 6000

    # Prompt for Envoy IP
    if default_ip:
        envoy_ip = input(f"Envoy IP address [{default_ip}]: ").strip() or default_ip
    else:
        envoy_ip = input("Envoy IP address: ").strip()
    if not envoy_ip:
        print("IP address is required.")
        sys.exit(1)

    # Prompt for system size
    size_input = input(f"System size in watts [{default_size}]: ").strip()
    try:
        system_size = int(size_input) if size_input else default_size
    except ValueError:
        print(f"Invalid number: {size_input}")
        sys.exit(1)

    # Save config
    save_config(envoy_ip, system_size)
    print(f"Config saved: IP={envoy_ip}, Size={system_size}W")

    # Prompt for Enphase credentials
    email = input("Enphase account email: ")
    password = getpass.getpass("Enphase account password: ")

    # Get session ID
    print("Fetching session ID...")
    login_data = json.dumps({"user": {"email": email, "password": password}}).encode()
    req = urllib.request.Request(
        "https://enlighten.enphaseenergy.com/login/login.json",
        data=login_data,
        headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=30)
    login_resp = json.loads(resp.read())
    session_id = login_resp.get("session_id")
    if not session_id:
        print(f"Login failed: {login_resp.get('message', 'unknown error')}")
        sys.exit(1)

    # Get serial number from Envoy
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(f"https://{envoy_ip}/info.xml")
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    import re
    match = re.search(r"<sn>(\d+)</sn>", resp.read().decode())
    if not match:
        print("Could not find serial number in Envoy info.xml")
        sys.exit(1)
    serial = match.group(1)
    print(f"Envoy serial: {serial}")

    # Fetch token
    print("Fetching token...")
    token_data = json.dumps({"session_id": session_id, "serial_num": serial, "username": email}).encode()
    req = urllib.request.Request(
        "https://entrez.enphaseenergy.com/tokens",
        data=token_data,
        headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=30)
    token = resp.read().decode().strip()

    if not token.startswith("ey"):
        print(f"Unexpected token response: {token}")
        sys.exit(1)

    # Decode expiry for display
    import base64
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    claims = json.loads(base64.b64decode(payload))
    from datetime import datetime
    expiry = datetime.fromtimestamp(claims["exp"])
    print(f"Token expires: {expiry.strftime('%Y-%m-%d')}")

    # Store in keychain
    save_token_to_keychain(token)
    print("Token saved to macOS Keychain.")

    # Verify it works
    print("Testing against Envoy...")
    req = urllib.request.Request(
        f"https://{envoy_ip}/production.json?details=1",
        headers={"Authorization": f"Bearer {token}"}
    )
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    if resp.status == 200:
        print("Success! Script should now work.")
    else:
        print(f"Warning: Envoy returned HTTP {resp.status}")


def envoy_request(envoy_ip, path, token):
    """Make an authenticated HTTPS request to the Envoy."""
    # Envoy uses a self-signed certificate on the local network
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        f"https://{envoy_ip}{path}",
        headers={"Authorization": f"Bearer {token}"}
    )
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    return json.loads(resp.read())


def short_number(val):
    """Format a number: values >= 1000 get a 'k' suffix."""
    val = abs(val)
    if val < 1000:
        return str(round(val))
    return f"{val / 1000:.1f}k"


def format_kwh(wh):
    """Format watt-hours as kWh with appropriate precision."""
    kwh = abs(wh) / 1000
    if kwh < 10:
        return f"{kwh:.1f} kWh"
    elif kwh < 1000:
        return f"{kwh:.0f} kWh"
    else:
        return f"{kwh / 1000:.1f} MWh"


def comma_separated(val):
    """Add comma separators to a number."""
    return f"{round(val):,}"


def main():
    if "--setup" in sys.argv:
        setup_token()
        return

    try:
        config = load_config()
        token = get_token_from_keychain()
        if not config or not token:
            print(":warning: Run --setup| size=12")
            print("---")
            print(setup_menu_item())
            return

        # Check token expiry
        import base64
        from datetime import datetime
        try:
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            claims = json.loads(base64.b64decode(payload))
            expiry = datetime.fromtimestamp(claims["exp"])
            if datetime.now() > expiry:
                print(":warning: Token expired| size=12")
                print("---")
                print(f"Expired {expiry.strftime('%Y-%m-%d')}| size=12")
                print(setup_menu_item())
                return
            days_left = (expiry - datetime.now()).days
            token_warning = f"Token expires in {days_left} days" if days_left < 30 else None
        except Exception:
            token_warning = None

        envoy_ip = config.get("envoy_ip")
        system_size = config.get("system_size_watts", 6000)
        if not envoy_ip:
            print(":warning: Run --setup| size=12")
            print("---")
            print("Missing envoy_ip in config| size=12")
            print(setup_menu_item())
            return

        # Get production and consumption data
        data = envoy_request(envoy_ip, "/production.json?details=1", token)
        production = data["production"][1]
        consumption = data["consumption"][0]
        net = data["consumption"][1]

        producing = production["wNow"]
        consuming = consumption["wNow"]
        importing = net["wNow"]

        # Choose icon based on power state
        if importing > 0:
            icon = "\U0001F50C"  # Power plug
        elif producing < (system_size / 2):
            icon = "\u26C5"  # Cloudy
        else:
            icon = "\u2600\uFE0F"  # Sun

        colour = "orange" if importing > 0 else "green"
        print(f"{icon} {short_number(importing)}W| color={colour} size=12")
        print("---")

        # Current power
        print(f"Producing  {comma_separated(producing)}W| size=12")

        # House consumption with solar percentage
        if producing > 0:
            solar_pct = min(100, (producing / consuming) * 100) if consuming > 0 else 0
            pct_colour = "green" if solar_pct >= 100 else "orange"
            print(f"\U0001F3E0 {comma_separated(consuming)}W ({solar_pct:.0f}% solar)| size=12 color={pct_colour}")
        else:
            print(f"\U0001F3E0 {comma_separated(consuming)}W| size=12")

        # Grid direction: → exporting, ← importing
        if importing > 0:
            print(f"\u2190 {comma_separated(importing)}W \u26A1| size=12 color=orange")
        else:
            print(f"\u2192 {comma_separated(abs(importing))}W \u26A1| size=12 color=green")

        print("---")

        # Energy totals
        print(f"Today      {format_kwh(production['whToday'])}| size=12")
        print(f"This Week  {format_kwh(production['whLastSevenDays'])}| size=12")
        print(f"Lifetime   {format_kwh(production['whLifetime'])}| size=12")

        print("---")

        # Inverter data
        inverters = envoy_request(envoy_ip, "/api/v1/production/inverters", token)
        active = [inv["lastReportWatts"] for inv in inverters if inv["lastReportWatts"] >= 2]
        yield_pct = (producing / system_size) * 100 if system_size > 0 else 0
        if active:
            print(f"{len(inverters)} panels: {min(active)}W\u2013{max(active)}W ({yield_pct:.0f}% yield)| size=12")
        else:
            print("No inverters generating.| size=12")


        # Token expiry warning
        if token_warning:
            print("---")
            print(f":warning: {token_warning}| size=12 color=orange")

    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(":warning: Token invalid| size=12")
            print("---")
            print(setup_menu_item())
        else:
            print(":warning: Error| size=12")
            print("---")
            print(f"HTTP {e.code}: {e.reason}")
    except Exception as e:
        print(":warning: Error| size=12")
        print("---")
        print(str(e))


if __name__ == "__main__":
    main()
