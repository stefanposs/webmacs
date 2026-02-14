# Plugins

Extend WebMACS with **device plugins** — additional I/O sources that feed sensor data into the same telemetry pipeline as your hardware channels.

!!! info "Bundled Plugins"
    WebMACS ships with three plugins out of the box — no installation required:

    | Plugin | What It Does |
    |---|---|
    | **Simulated Device** | Virtual sensors & actuators for testing and demos |
    | **System Monitor** | CPU, memory, disk, and temperature of the host system |
    | **Revolution Pi** | Direct hardware I/O via the piCtory process image |

---

## Concepts

### Plugin vs. Plugin Instance

A **plugin** is a reusable device driver (e.g., "System Monitor"). A **plugin instance** is a configured, running copy of that plugin (e.g., "Lab PC Monitor" with demo mode enabled). You can create multiple instances of the same plugin with different settings.

### Channels

Each plugin instance exposes **channels** — named data points with a direction (`input`, `output`, or `bidirectional`), a unit, and an optional link to a WebMACS event. When a channel is mapped to an event, its values appear on dashboards and in the datapoint stream automatically.

### Demo Mode

Every plugin instance can run in **demo mode**. Instead of reading real hardware, it simulates realistic sensor values (sine waves, random walks, sawtooth patterns) — perfect for testing dashboards and rules without physical devices.

---

## Managing Plugin Instances

Navigate to **Plugins** in the sidebar to see all active plugin instances.

### Create an Instance

1. Click **:material-plus: New Instance**.
2. Select a plugin from the list of available plugins (e.g., "System Monitor").
3. Enter an **instance name** (e.g., "Production Server Metrics").
4. Toggle **Demo Mode** on or off.
5. Click **Create**.

The plugin auto-discovers its channels. You'll see them listed under the instance — e.g., `cpu_percent`, `memory_percent`, `disk_percent` for the System Monitor.

### Configure an Instance

Click the **Configure** button on any instance card to:

- Rename the instance
- Enable or disable it
- Toggle demo mode
- Map channels to WebMACS events (so their values appear on dashboards)

### Map a Channel to an Event

Each channel can be linked to a WebMACS **event**. Once linked, the plugin's sensor values flow into the standard telemetry pipeline:

1. Open the plugin instance detail page.
2. Find the channel you want (e.g., `cpu_percent`).
3. Select a target event from the dropdown.
4. The channel now feeds live data into that event's datapoint stream.

### Delete an Instance

Click the **:material-delete: Delete** button on the instance card and confirm. All channel mappings are removed automatically.

---

## Plugin Packages

:material-shield-lock:{ title="Admin only" } Navigate to **Plugins → Packages** to manage installed plugin packages.

### Bundled vs. Uploaded

| Type | Badge | Removable? |
|---|---|---|
| **Bundled** | :material-package-variant: *bundled* | No — ships with WebMACS |
| **Uploaded** | :material-cloud-upload: *uploaded* | Yes — admin can uninstall |

### Upload a Plugin Package

1. Click **:material-upload: Upload Plugin**.
2. Select a `.whl` (Python wheel) file from your computer.
3. A progress bar shows the upload status.
4. On success, the package appears in the list with its name, version, and contained plugin IDs.

!!! warning "Restart Required"
    After uploading or uninstalling a package, **restart the controller** to activate the changes. The new plugins will be discovered automatically on next startup.

### Validation

The system validates every uploaded wheel:

- File must be a `.whl` (Python wheel)
- Maximum size: **50 MB**
- Must contain valid wheel metadata (`METADATA` file)
- Must declare a `[webmacs.plugins]` entry point

Invalid files are rejected with a clear error message.

### Uninstall a Package

Click **:material-delete: Uninstall** on any uploaded package. Bundled packages cannot be removed.

---

## Status Indicators

Each plugin instance shows a status badge:

| Status | Meaning |
|---|---|
| :material-connection:{ style="color: var(--sensor-color)" } **connected** | Running and reading real hardware |
| :material-tune-variant:{ style="color: var(--range-color)" } **demo** | Running in demo/simulation mode |
| :material-power-standby:{ style="color: var(--cmd-button-color)" } **inactive** | Not yet started or disabled |
| :material-alert-circle:{ style="color: var(--actuator-color)" } **error** | Something went wrong — check the error message |

---

## Tips & Best Practices

!!! tip "Start with Demo Mode"
    Create your first plugin instance in demo mode. This lets you verify that dashboards, rules, and webhooks work correctly before connecting to real hardware.

!!! tip "One Instance per Device"
    Create separate instances for each physical device or system you want to monitor. This keeps channel mappings clean and makes it easy to disable individual sources.

!!! tip "Channel → Event Mapping"
    The real power of plugins is the channel-to-event mapping. Once a channel is linked to an event, all existing WebMACS features work automatically: live dashboards, threshold rules, webhooks, CSV export.

---

## Next Steps

- **[Plugin Development Guide](../development/plugin-development.md)** — build your own plugin
- **[API Reference: Plugins](../api/rest.md#plugins)** — REST endpoint documentation
- **[Dashboard Guide](dashboard.md)** — visualize plugin data on custom dashboards
