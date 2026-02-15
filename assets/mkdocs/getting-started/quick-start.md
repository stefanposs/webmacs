# Quick Start

This guide walks you through your first WebMACS session — from login to seeing live sensor data on a dashboard.

---

## 1. Start the Stack

```bash
cd webmacs
docker compose up -d
```

Open **http://localhost** in your browser.

---

## 2. Log In

The backend automatically seeds an initial admin user on first startup:

| Field | Default |
|---|---|
| Email | `admin@webmacs.io` |
| Password | `admin123` |

!!! warning "Change the default password"
    Set `INITIAL_ADMIN_PASSWORD` in your `.env` file before deploying to any shared environment.

---

## 3. Set Up a Plugin (Data Source)

WebMACS receives sensor data through **plugins**. A plugin is a device driver that reads hardware (or simulated) channels and feeds values into the telemetry pipeline.

!!! tip "Development mode auto-setup"
    In **development mode** (the default when using `docker compose up`), the controller automatically creates a **Simulated Device** plugin instance with 9 demo channels on first boot. You can skip to [Step 4](#4-explore-the-dashboard) and come back here when you want to add your own data sources.

### Create a Plugin Instance

1. Navigate to **Plugins** in the sidebar.
2. Click **:material-plus: New Instance**.
3. Select a plugin — e.g., **Simulated Device** for testing or **System Monitor** for real host metrics.
4. Enter an instance name (e.g., `Lab Sensors`).
5. Toggle **Demo Mode** on if you don't have real hardware connected.
6. Click **Create**.

The plugin automatically discovers its channels (e.g., `temperature`, `humidity`, `cpu_percent`) and creates matching **events** for each channel.

### Verify Channel → Event Mapping

Once the instance is created, its channels are listed under the instance card. Each channel is auto-linked to a WebMACS event:

- Navigate to **Events** in the sidebar to see the newly created events.
- Each event has a **type** (sensor, actuator, range), a **unit**, and a unique `public_id`.

!!! info "How data flows"
    Plugin channel → Event → Datapoint stream → Dashboard / Rules / Webhooks / CSV export.
    Without at least one active plugin instance, no sensor data reaches the system.

---

## 4. Explore the Dashboard

The **Dashboard** shows real-time sensor data from your active plugin instances:

- **WebSocket mode** — data streams in via `/ws/datapoints/stream` (green indicator)
- **Polling fallback** — if WebSocket fails after 3 attempts, the dashboard falls back to HTTP polling (amber indicator)

You should now see live values from the channels you configured in the previous step. If using demo mode, the values follow realistic simulation profiles (sine waves, random walks, etc.).

---

## 5. Create an Experiment

1. Navigate to **Experiments** in the sidebar
2. Click **New Experiment**
3. Enter a name (e.g. `Test Run 01`)
4. Click **Start** — all incoming datapoints are now associated with this experiment

---

## 6. Stop & Export

1. Go back to **Experiments**
2. Click **Stop** on the running experiment
3. Click the **CSV** download button to export all datapoints

---

## Next Steps

- [Plugins Guide](../guide/plugins.md) — manage plugin instances, channels, and custom packages
- [Configuration](configuration.md) — customise settings via environment variables
- [Dashboard Guide](../guide/dashboard.md) — deep dive into real-time monitoring
- [Architecture Overview](../architecture/overview.md) — understand how the pieces fit together
