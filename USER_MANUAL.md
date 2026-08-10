# WeatherAlert User Manual

## 1. Overview

WeatherAlert is a Python service that monitors active National Weather Service (NWS) alerts for configured locations. It provides:

- A browser-based alert display and configuration interface
- Monitoring for NWS zone/county codes, 6-digit SAME codes, and latitude/longitude points
- Alert acknowledgement
- Optional remote TFT displays
- Optional remote LED status lighting
- Optional TCP audio announcements
- Optional radar API area selection from the Display page
- Optional Google Air Quality data on idle TFT clock screens
- Runtime statistics and raw NWS JSON viewing

The app supports up to 15 configured alert areas and eight LED weather groups numbered 0 through 7.

> This application supplements official weather information. Do not rely on it as your only source of emergency alerts.

## 2. Requirements

Required:

- Python 3.10 or newer
- Internet access to `api.weather.gov`
- The Python `requests` package
- A modern web browser

Optional:

- `terminal_tft.py` or `tft_terminal.py` in the application directory for TFT output
- A compatible TCP LED controller
- A compatible TCP text-to-speech or audio host
- A Google Air Quality API key for air-quality information

Install the required Python package from PowerShell:

```powershell
python -m pip install requests
```

## 3. Starting the Application

Open PowerShell in the application directory and run:

```powershell
python python-walert.py
```

The default web address is:

```text
http://localhost:8080
```

From another device on the same network, replace `localhost` with the computer's IP address:

```text
http://192.168.1.50:8080
```

The first NWS fetch begins at startup. The default refresh interval is 60 seconds.

Stop the application by pressing `Ctrl+C` in its PowerShell window. A normal shutdown also sends an off command to all configured LEDs.

### Recommended User-Agent

The NWS requests that API clients identify themselves. Add a user-agent containing your contact information to `weatheralert_settings.json`:

```json
{
  "user_agent": "WeatherAlert/1.0 (your-email@example.com)"
}
```

The settings file is optional. When it exists, the app reads it at startup.

## 4. Web Interface

The navigation bar contains five pages.

### Display

The Display page lists active alerts by weather group and zone. Each row shows:

- Zone label
- Alert event
- Issued time in local time
- NWS message type
- Expiration time in local time
- A link to the complete alert detail

The page updates automatically after the service processes new data.

#### Acknowledging an Alert

Click the colored alert-name button to acknowledge that alert. Acknowledgement suppresses the alert from TFT and LED output. The alert remains visible in the web interface with a dimmed acknowledgement style.

Acknowledgements are held in memory and are removed when the alert is no longer active. They do not survive an application restart.

For an NWS message with type `Update`:

- The update is treated as acknowledged when all messages referenced by the update have been acknowledged.
- If any referenced message is unacknowledged, the update remains unacknowledged.
- An update can also be acknowledged directly by clicking its alert button.
- An unacknowledged update participates in LED priority selection using the update's event type.

### Stats

The Stats page displays:

- Service uptime
- NWS connection attempts
- HTTP error count
- Reboot and fetch-loop restart counters
- Per-zone HTTP status and attempt count
- Alert count and JSON response size
- Network load and JSON parsing times
- In-memory page and detail sizes

Use **Reset Statistics** to clear the counters. The reboot counter resets to 1 for the current run.

Runtime counters are stored in `weatheralert_runtime.json` by default.

### Detail

The Detail page shows the event, headline, description, effective time, and expiration time for active alerts. The page refreshes at the configured alert-cycle interval.

### Areas

The Areas page shows the current fetch state for every configured area. Use **View JSON** to inspect the original NWS response for a zone. The JSON page can also copy or download the response.

This page is useful when diagnosing an unexpected alert count, location match, or API response.

### Config

The Config page manages all monitored areas and output assignments.

Changes take effect in the running service immediately, but they are not persistent until **Save Current Zones** is selected.

## 5. Configuring Alert Areas

### NWS Zone or County Code

Select the **NWS / SAME Code** tab and enter:

- **NWS or SAME Code:** an NWS zone/county identifier such as `NCC183`, or a 6-digit SAME code such as `037183`
- **Short Label:** a display name containing 1 to 7 characters
- **Weather Group:** LED group 0 through 7, or `None`

For a 6-digit SAME code, the app queries the corresponding state and filters returned alerts by the SAME code.

### Latitude and Longitude

Select the **Geographic Lat/Lon** tab and enter:

- Latitude from -90 through 90
- Longitude from -180 through 180
- A short label containing 1 to 7 characters
- A weather group

The app uses the NWS active-alert point query for this location.

### Zone Controls

Each configured zone provides these controls:

- **TFT:** includes or excludes the zone from the primary TFT alert display
- **Audio:** enables or disables new-alert announcements for the zone
- **Weather Group:** assigns the zone to LED group 0 through 7, or disables LED assignment with `None`
- **Up/Down:** changes the zone order
- **Enable/Disable:** controls whether the zone is fetched
- **Remove:** deletes the zone from the running configuration

Multiple zones may share one weather group. Their unacknowledged alerts are combined when selecting that group's LED color.

### Saving and Restoring

- **Save Current Zones:** writes the complete running zone configuration to `weatheralert_config.json`.
- **Restore from Saved:** immediately replaces the running configuration with the saved file.
- **Clear Saved Config:** deletes the saved configuration. Built-in defaults will load at the next service start.

The application loads the saved configuration at startup when the file exists and is valid.

## 6. LED Behavior

LED output is enabled by setting an LED host. Each weather group maps directly to LED number 0 through 7.

Set the controller address in `weatheralert_settings.json` before startup:

```json
{
  "led_host": "192.168.1.60",
  "led_port": 7777
}
```

When a group contains multiple unacknowledged alerts, the highest-priority event determines the LED color:

| Priority | Event match | Color |
|---:|---|---|
| 1 | Tornado Warning | White |
| 2 | Tornado Watch | Orange |
| 3 | Other Warning | Red |
| 4 | Other Watch | Yellow |
| 5 | Statement | Blue |
| 6 | Advisory | Green |
| 7 | Other alert | Purple |

A newly detected NWS message of type `Alert` blinks for approximately 30 seconds and then remains steadily illuminated. Color changes, acknowledgement, expiration, and alert removal update the LED state. A group with no unacknowledged alerts is turned off.

Unacknowledged `Update` messages affect the steady LED color according to their event priority. Updates are not treated as new-alert blink triggers.

## 7. TFT Display

The optional TFT output shows active alerts from every zone whose TFT option is enabled.

When no applicable alert is active, the display shows a clock. If air-quality data is configured, it is included on the idle clock screen.

Example configuration:

```json
{
  "tft_host": "192.168.1.70",
  "tft_port": 8888,
  "tft_display": "ili9341",
  "tft_rotation": 1
}
```

If no TFT host is set, or the TFT library is unavailable, the web service continues to operate.

## 8. Audio Announcements

Audio output sends UTF-8 text over TCP, terminated by a carriage return. Configure the destination with:

```json
{
  "audio_host": "192.168.1.80",
  "audio_port": 5000
}
```

The app announces newly detected NWS messages of type `Alert`. It does not announce `Update` messages. The announcement format is similar to:

```text
Weather area 2. NC F. Severe Thunderstorm Warning
```

Use the Audio checkbox on the Config page to enable or disable announcements for individual zones.

## 9. Radar API

Radar output is optional. Configure the destination with:

```json
{
  "radar_host": "192.168.1.90",
  "radar_port": 8081
}
```

On the Display page, each area row starts with zoom `7`. Click the Radar button on a row to center the radar map using that row's current zoom. Use the zoom selector beside it to choose zoom `6`, `7`, `8`, or `9`; only that row's zoom changes, and the new zoom is sent immediately. Latitude/longitude areas are sent as `lat=<area latitude> lon=<area longitude> zoom=<zoom>`. NWS zone/county and SAME areas are sent as `same=<assigned code> zoom=<zoom>`.

## 10. Air Quality

Air quality is optional and appears on idle TFT clock screens. Set a Google Air Quality API key:

```json
{
  "google_air_quality_api_key": "your-api-key",
  "air_quality_lat": "35.7796",
  "air_quality_lon": "-78.6382"
}
```

If explicit coordinates are not configured, the app uses the first active latitude/longitude alert area. The default air-quality refresh interval is 3600 seconds.

## 11. Command-Line Options

View every available option:

```powershell
python python-walert.py --help
```

Example:

```powershell
python python-walert.py --bind 127.0.0.1 --port 8085 --alert-cycle-seconds 90 --log-level DEBUG
```

Common options:

| Option | Purpose | Default |
|---|---|---|
| `--settings` | Optional app settings file | `weatheralert_settings.json` |
| `--bind` | Web server bind address | `0.0.0.0` |
| `--port` | Web server port | `8080` |
| `--alert-cycle-seconds` | NWS fetch interval | `60` |
| `--config` | Saved zone file | `weatheralert_config.json` |
| `--runtime` | Runtime counter file | `weatheralert_runtime.json` |
| `--user-agent` | NWS request identity | Built-in value |
| `--nws-timeout` | NWS request timeout | `60` seconds |
| `--led-host`, `--led-port` | LED controller connection | Disabled / `7777` |
| `--tft-host`, `--tft-port` | TFT connection | Disabled / `8888` |
| `--audio-host`, `--audio-port` | Audio TCP connection | Disabled |
| `--radar-host`, `--radar-port` | Radar API connection | Disabled |
| `--log-level` | Python logging level | `INFO` |

Settings-file keys match the long command-line option names without leading dashes. Use underscores or hyphens, for example `alert_cycle_seconds` or `alert-cycle-seconds`.

Command-line values override settings-file values for that run.

## 12. Security and Network Access

The default bind address, `0.0.0.0`, makes the web interface available through every network interface on the computer. The interface has no login or access control.

For access only from the same computer, use:

```powershell
python python-walert.py --bind 127.0.0.1
```

Do not expose the app directly to the public internet. Use firewall restrictions or an authenticated reverse proxy if access beyond a trusted local network is required.

## 13. Troubleshooting

### The web page does not open

- Confirm that the Python process is still running.
- Try `http://localhost:8080` on the host computer.
- Check whether another program is using port 8080.
- Try another port with `--port 8085`.
- Check the host firewall when connecting from another device.

### Alerts remain pending

- Allow enough time for the first fetch cycle.
- Confirm internet access and DNS resolution for `api.weather.gov`.
- Open the Stats page and inspect HTTP status, attempt count, and errors.
- Set a valid `user_agent` in `weatheralert_settings.json` containing contact information.

### A zone returns unexpected alerts

- Confirm the NWS/SAME code or coordinates on the Config page.
- Open Areas, then View JSON, to inspect the NWS response.
- For precise point monitoring, use a latitude/longitude area.

### Configuration disappeared after restart

Running changes are not automatically saved. Select **Save Current Zones** after editing the configuration.

### LED, TFT, audio, or radar output is missing

- Confirm the relevant host and port were set before startup.
- Confirm the remote device is reachable from the WeatherAlert computer.
- Check the application console for connection or write errors.
- Confirm the zone is enabled and assigned to the intended output.
- For LEDs, confirm the zone has weather group 0 through 7 rather than `None`.

### An alert stopped driving external outputs

It may have been acknowledged. Acknowledged alerts remain visible on the web page but are suppressed from TFT and LED output. Restarting the application clears in-memory acknowledgements.

## 14. Files Created by the App

| File | Purpose |
|---|---|
| `weatheralert_config.json` | Saved zone and output configuration |
| `weatheralert_runtime.json` | Persistent reboot, restart, connection, and HTTP-error counters |

Alternative paths can be selected with `--config`, `--runtime`, or by setting `config` and `runtime` in `weatheralert_settings.json`.
