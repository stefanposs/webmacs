# WebMACS Weather Station Plugin — Example

A complete, ready-to-upload example demonstrating how to write a custom
plugin for [WebMACS](https://github.com/stefanposs/webmacs).

## Channels

| Channel ID   | Name                 | Direction | Unit  | Range          |
| ------------ | -------------------- | --------- | ----- | -------------- |
| temperature  | Ambient Temperature  | input     | °C    | −40 … 60       |
| humidity     | Relative Humidity    | input     | %     | 0 … 100        |
| wind_speed   | Wind Speed           | input     | km/h  | 0 … 200        |
| pressure     | Barometric Pressure  | input     | hPa   | 900 … 1 100    |
| rainfall     | Rainfall Rate        | input     | mm/h  | 0 … 100        |

## Quick start

### 1. Build the wheel

```bash
pip install build
python -m build          # creates dist/webmacs_plugin_weather-0.1.0-py3-none-any.whl
```

### 2. Upload via the WebMACS UI

1. Open **Settings → Plugins** in your WebMACS dashboard.
2. Click **Upload Plugin**.
3. Select the `.whl` file from `dist/`.
4. The plugin appears in the list — click **Enable**.

### 3. Upload via the REST API

```bash
curl -X POST https://your-webmacs/api/v1/plugins/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@dist/webmacs_plugin_weather-0.1.0-py3-none-any.whl"
```

### 4. Configure & connect

After uploading, create a plugin instance with:

```json
{
  "plugin_id": "weather",
  "instance_name": "Roof Station",
  "demo_mode": true,
  "poll_interval_ms": 2000
}
```

Set `demo_mode` to `false` and implement the `_do_connect` / `_do_read`
methods to connect to real hardware.

## Running tests

```bash
pip install -e ".[dev]"        # or: pip install webmacs-plugins-core pytest pytest-asyncio
pytest tests/ -v
```

All conformance tests (metadata, channels, lifecycle, demo-mode read/write,
health check) are inherited automatically from `PluginConformanceSuite`.

## Project structure

```
examples/custom-plugin/
├── pyproject.toml                          # Package metadata + entry-point
├── README.md
├── src/
│   └── webmacs_plugin_weather/
│       ├── __init__.py                     # Re-exports WeatherStationPlugin
│       └── plugin.py                       # Plugin implementation
└── tests/
    ├── __init__.py
    └── test_weather.py                     # Conformance suite
```

## Adapting for your own hardware

1. **Copy** this directory and rename `webmacs_plugin_weather` to your
   package name (e.g. `webmacs_plugin_modbus_sensor`).
2. **Update** `pyproject.toml`: change `name`, `version`, entry-point key,
   and package path.
3. **Edit** `plugin.py`:
   - Set `meta` fields (id, name, vendor, …).
   - Define your channels in `get_channels()`.
   - Implement `_do_connect()`, `_do_disconnect()`, `_do_read()`, and
     optionally `_do_write()` with real protocol logic.
4. **Add** a custom config class if your plugin needs extra settings
   (serial port, IP address, etc.) — subclass `PluginInstanceConfig`.
5. **Run** `pytest tests/` to verify contract compliance.
6. **Build** and **upload** as shown above.

## License

MIT
