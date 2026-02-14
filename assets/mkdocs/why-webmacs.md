# Why WebMACS?

## The Problem

Traditional lab monitoring setups rely on:

- **Proprietary SCADA software** — expensive licenses, vendor lock-in, Windows-only
- **LabVIEW** — powerful but complex, requires specialized skills, expensive per-seat licensing
- **Spreadsheets + manual logging** — error-prone, no real-time visibility, no alerts
- **Custom scripts** — no UI, no experiment management, breaks when the author leaves

None of these give you a **browser-based, real-time dashboard with alerts and CSV export** that runs on a €200 Raspberry Pi.

---

## What Makes WebMACS Different

| Capability | WebMACS | Proprietary SCADA | LabVIEW | Manual Logging |
|---|---|---|---|---|
| **Cost** | Free (open-source, MIT) | €5,000–50,000+ | €3,000+ per seat | Free |
| **Real-time dashboard** | :material-check: Browser-based | :material-check: Desktop app | :material-check: Desktop | :material-close: |
| **Custom dashboards** | :material-check: Drag & drop widget builder | :material-check: Proprietary | :material-check: Custom code | :material-close: |
| **Plugin system** | :material-check: Upload `.whl`, instant | :material-close: Vendor-only | :material-check: Custom code | :material-close: |
| **Threshold alerts** | :material-check: Slack, Teams, webhooks | :material-check: Proprietary | :material-check: Custom code | :material-close: |
| **CSV export** | :material-check: One-click, streaming | :material-check: | :material-check: | Manual |
| **Runs on Raspberry Pi** | :material-check: | :material-close: | :material-close: | N/A |
| **No cloud required** | :material-check: Fully offline | Varies | :material-check: | :material-check: |
| **Open REST + WebSocket API** | :material-check: | Varies | :material-check: | :material-close: |
| **Setup time** | ~5 minutes | Days / weeks | Hours / days | N/A |
| **Vendor lock-in** | None | High | Medium | None |
| **Multi-user access** | :material-check: Admin + operator roles | Varies | :material-close: | :material-close: |

---

## Deep Dive: Custom Dashboards — No Code, Full Control

With proprietary SCADA, changing a dashboard layout means calling the vendor or
writing custom scripts. With LabVIEW, it means editing a VI and recompiling.

With WebMACS, any operator can:

1. Click **"New Dashboard"** and name it (e.g., "Reactor Zone A")
2. **Add widgets** with a type picker and size presets (Small → Full Width)
3. Choose from **4 widget types**:
   - :material-chart-line: **Line Chart** — real-time trend for any sensor
   - :material-gauge: **Gauge** — at-a-glance value with colour-coded range
   - :material-card-text: **Stat Card** — big number with label and unit
   - :material-toggle-switch: **Actuator Toggle** — ON/OFF control for valves, relays, motors
4. Link each widget to a **live sensor event** — data refreshes automatically
5. Create **as many dashboards as needed** — one per zone, process, or team
6. Share a dashboard with all users by marking it as **global**

No recompilation. No vendor call. No license upgrade.

[**Dashboard Guide →**](guide/dashboard.md#custom-dashboards){ .md-button }

---

## Deep Dive: Plugin System — Your Hardware, Your Rules

With traditional SCADA systems, adding a new sensor type means waiting for the
vendor to ship a driver update — or reverse-engineering a proprietary protocol.
With LabVIEW, it means writing a new VI, rebuilding, and redeploying.

With WebMACS, you **write a Python class, build a wheel, and upload it through
the browser**. Done.

### How It Works

```mermaid
flowchart LR
    Dev["Write plugin.py<br/>(Python)"] --> Build["python -m build<br/>→ .whl file"]
    Build --> Upload["Upload via UI<br/>or REST API"]
    Upload --> Discover["Auto-discovered<br/>on restart"]
    Discover --> Data["Channels → Events<br/>→ Dashboards"]
```

### What Makes It Unique

1. **No recompilation** — plugins are regular Python packages loaded at runtime
2. **Built-in demo mode** — every plugin can simulate realistic sensor data out of the box, no hardware needed for development
3. **Conformance testing** — inherit from `PluginConformanceSuite` and get 13 tests for free (lifecycle, channels, health, etc.)
4. **Channel mapping** — link any plugin channel to a WebMACS event with one click; data flows into dashboards, rules, webhooks, and CSV exports automatically
5. **Sync and async** — use `DevicePlugin` for async protocols (MQTT, OPC-UA) or `SyncDevicePlugin` for blocking libraries (serial, Modbus) — the SDK handles threading for you
6. **Safety by design** — define `safe_value` per output channel; on disconnect or error, actuators are driven to safe state automatically
7. **Example included** — a complete Weather Station example plugin ships in `examples/custom-plugin/` with build instructions

### Example: Add a Custom Sensor in 4 Steps

| Step | What You Do | Time |
|------|-------------|------|
| 1 | Copy the example plugin and edit `get_channels()` | 5 min |
| 2 | Implement `_do_connect()` and `_do_read()` for your protocol | 15 min |
| 3 | Run `python -m build` to create a `.whl` file | 10 sec |
| 4 | Upload via **Plugins → Upload** and create an instance | 1 min |

**Total: ~20 minutes from idea to live data on your dashboard.**

Compare that to weeks of vendor coordination or days of LabVIEW rewiring.

### Bundled Plugins

WebMACS ships with three plugins — no installation required:

| Plugin | Channels | Purpose |
|--------|----------|---------|
| **Simulated Device** | 9 (temperatures, pressures, flow, valve, heater) | Testing & demos without hardware |
| **System Monitor** | 4 (CPU, memory, disk, temperature) | Host health monitoring |
| **Revolution Pi** | Dynamic (via piCtory) | Direct RevPi I/O access |

!!! success "The Bottom Line"
    Other systems force you to choose from the vendor's catalogue.
    WebMACS lets you **connect anything that speaks a protocol** — Modbus,
    MQTT, HTTP, serial, OPC-UA — with a Python class and a `.whl` upload.

[**Plugin Development Guide →**](development/plugin-development.md){ .md-button }
[**Plugin User Guide →**](guide/plugins.md){ .md-button }

---

## Deep Dive: Open Integration — The Swiss Army Knife

Most monitoring systems are walled gardens. WebMACS is designed as a
**composable building block** that connects to anything.

### Three Integration Layers

```mermaid
graph TB
    subgraph WebMACS
        REST["REST API<br/>30+ endpoints"]
        WS["WebSocket<br/>Live streaming"]
        WH["Webhooks<br/>Event-driven push"]
    end

    REST -->|"GET/POST/PUT/DELETE"| Client["Custom Apps<br/>Scripts · Mobile"]
    WS -->|"Sub-second"| CustomUI["Custom Dashboards<br/>Grafana · HMI panels"]
    WH -->|"HMAC-signed POST"| Slack["Slack / Teams"]
    WH -->|"Automation"| NR["Node-RED"]
    WH -->|"Smart Home"| HA["Home Assistant"]
    WH -->|"Data Pipeline"| Cloud["AWS / Azure / S3"]
```

| Layer | Best For | Example |
|-------|---------|---------|
| **REST API** | CRUD, scripted pipelines, mobile apps | `GET /experiments/{id}/export/csv` → feed a reporting tool |
| **WebSocket** | Live dashboards, low-latency custom UIs | Stream values to Grafana or a wall-mounted HMI panel |
| **Webhooks** | Alerts, cross-system automation | `sensor.threshold_exceeded` → Slack alert + Node-RED safety shutdown |

!!! success "The Bottom Line"
    WebMACS doesn't replace your other tools — it **powers them**. Use the REST
    API to build, WebSocket to stream, and webhooks to react. Your lab's
    monitoring system becomes the data backbone of your entire workflow.

[**Integration Guide →**](guide/integrations.md){ .md-button }

---

## Ideal Use Cases

<div class="grid-container" markdown>

<div class="grid-item" markdown>
### :material-school: University Research Labs
Monitor fluidised-bed reactors, autoclaves, fermenters — with full experiment tracking and CSV export for thesis data.
</div>

<div class="grid-item" markdown>
### :material-factory: Pilot Plants
Track temperature, pressure, and flow across multiple zones. Set threshold alerts to catch anomalies early.
</div>

<div class="grid-item" markdown>
### :material-clipboard-check: Quality Assurance
Log every sensor reading with timestamps for compliance audits. Export complete data trails on demand.
</div>

<div class="grid-item" markdown>
### :material-account-group: Teaching Labs
Students interact via browser — no software installation needed. Each team gets their own dashboard view.
</div>

</div>

---

## What You Get Out of the Box

1. **Live dashboard** — sensor cards, actuator toggles, trend charts with configurable time ranges
2. **Custom dashboards** — build your own widget layouts with line charts (incl. unit-labelled axes), gauges, stat cards, and actuator controls
3. **Plugin system** — upload custom device drivers as Python wheels; connect any sensor or protocol in minutes
4. **Experiment tracking** — named runs with automatic data linking and one-click CSV export
5. **Alerting** — threshold rules with Slack/Teams/webhook notifications and cooldown periods
6. **Data export** — streaming CSV downloads for Excel, Python, or MATLAB analysis
7. **User management** — admin and operator roles with JWT authentication
8. **OTA updates** — deploy new versions over USB, browser upload, or network
9. **Full API** — extend or integrate with anything via REST and WebSocket
10. **Webhook integrations** — HMAC-signed event delivery with retry logic

---

## Open Source & Extensible

WebMACS is licensed under [MIT](https://github.com/stefanposs/webmacs/blob/main/LICENSE). You can:

- Build custom dashboards with widgets tailored to your process
- Write and upload new device plugins for any sensor, actuator, or protocol
- Integrate with Slack, Node-RED, Home Assistant, or any HTTP endpoint
- Deploy on a Raspberry Pi and self-host with zero ongoing costs

!!! tip "Getting Started"
    Ready to try it? Follow the [Quick Start Guide](getting-started/quick-start.md) to have WebMACS running in under 5 minutes.

[**Get Started →**](getting-started/quick-start.md){ .md-button .md-button--primary }
[**View Architecture →**](architecture/overview.md){ .md-button }
