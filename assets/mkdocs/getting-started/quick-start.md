# Quick Start

This guide walks you through your first WebMACS session — from login to running an experiment.

---

## 1. Start the Stack

```bash
cd webmacs/v2
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

## 3. Explore the Dashboard

The **Dashboard** shows real-time sensor data:

- **WebSocket mode** — data streams in via `/ws/datapoints/stream` (green indicator)
- **Polling fallback** — if WebSocket fails after 3 attempts, the dashboard falls back to HTTP polling (amber indicator)

---

## 4. Create an Experiment

1. Navigate to **Experiments** in the sidebar
2. Click **New Experiment**
3. Enter a name (e.g. `Test Run 01`)
4. Click **Start** — all incoming datapoints are now associated with this experiment

---

## 5. View Events & Sensors

The **Events** page lists all configured sensor/actuator events. Each event has:

- A unique `public_id`
- A `type` (sensor, actuator, range, cmd_button, cmd_opened, cmd_closed)
- A human-readable `name`

---

## 6. Stop & Export

1. Go back to **Experiments**
2. Click **Stop** on the running experiment
3. Click the **CSV** download button to export all datapoints

---

## Next Steps

- [Configuration](configuration.md) — customise settings via environment variables
- [Dashboard Guide](../guide/dashboard.md) — deep dive into real-time monitoring
- [Architecture Overview](../architecture/overview.md) — understand how the pieces fit together
