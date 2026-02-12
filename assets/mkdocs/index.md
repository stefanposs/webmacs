---
hide:
  - navigation
  - toc
---

# WebMACS

## Monitor. Automate. Control. — From Any Browser.

WebMACS is an **open-source control system** that turns your Raspberry Pi or Revolution Pi into a real-time monitoring and automation hub for lab experiments and industrial processes.

**No cloud. No subscriptions. No vendor lock-in.** Your data stays on your hardware.

![WebMACS Dashboard — Real-Time Monitoring](images/web_gui_dashboard-v2.png){ .screenshot }

---

## Who Is WebMACS For?

<div class="grid-container" markdown>

<div class="grid-item" markdown>
### :material-flask-outline: Process Engineers & Researchers
Monitor fluidised-bed reactors, temperature profiles, pressure readings, and flow rates — all from your browser. Export experiment data to CSV for analysis in Excel, Python, or MATLAB.
</div>

<div class="grid-item" markdown>
### :material-cog-outline: Lab Technicians & Operators
Toggle valves, adjust setpoints, and track sensor trends on a live dashboard. Get alerted via Slack or email when values go out of range.
</div>

<div class="grid-item" markdown>
### :material-code-braces: Developers & Integrators
Extend the system with a clean REST + WebSocket API. Add new sensor types, build custom dashboards, or integrate with external systems via webhooks.
</div>

</div>

---

## What Can You Do With WebMACS?

| Capability | What It Means For You |
|---|---|
| :material-monitor-dashboard: **Real-Time Dashboard** | See every sensor value live, toggle actuators, build custom widget layouts — updated via WebSocket in under 100 ms |
| :material-flask: **Experiment Management** | Group all readings into named experiments. Start, stop, and export with one click |
| :material-chart-line: **Custom Dashboards** | Build your own dashboards with line charts, gauges, stat cards, and actuator toggles on a 12-column grid |
| :material-alert: **Threshold Alerts** | Define rules like "if temperature > 200 °C → notify Slack". No code required |
| :material-webhook: **Webhook Integrations** | Push events to Slack, Teams, Node-RED, Home Assistant, or any HTTP endpoint |
| :material-file-delimited: **CSV Export** | Download millions of datapoints as a CSV — streamed, instant, ready for pandas or Excel |
| :material-update: **Over-The-Air Updates** | Deploy new versions via USB, file upload, or network — works fully offline |
| :material-docker: **One-Command Install** | Single script installs Docker, generates credentials, starts all services, and enables auto-boot |

---

## Get Started in 5 Minutes

=== "Production (RevPi / Raspberry Pi)"

    ```bash
    # Transfer the bundle to your device and run:
    sudo bash scripts/install.sh webmacs-update-2.0.0.tar.gz
    ```

    Open `http://<device-ip>` and log in with the credentials shown during install.
    See the [Installation Guide](deployment/installation-guide.md) for step-by-step details.

=== "Development (Local)"

    ```bash
    git clone https://github.com/stefanposs/webmacs.git
    cd webmacs
    docker compose up --build -d
    ```

    Open `http://localhost` and log in. See [Quick Start](getting-started/quick-start.md) for default credentials.

[**Quick Start Guide →**](getting-started/quick-start.md){ .md-button .md-button--primary }
[**View on GitHub →**](https://github.com/stefanposs/webmacs){ .md-button }

---

## Architecture at a Glance

```mermaid
graph LR
    Hardware["Sensors & Actuators"] -->|I/O| Controller["IoT Controller<br/>(Python)"]
    Controller -->|HTTP / WebSocket| Backend["FastAPI Backend"]
    Backend -->|async| DB[(PostgreSQL)]
    Frontend["Vue 3 Dashboard<br/>(Browser)"] -->|REST + WS| Backend
    Backend -->|Webhooks| External["Slack / Teams / APIs"]
```

| Layer | Technology |
|---|---|
| **Backend** | FastAPI · SQLAlchemy 2 async · Pydantic v2 · Python 3.13 |
| **Frontend** | Vue 3 · TypeScript · Vite · PrimeVue · Pinia |
| **Controller** | Python 3.13 · HTTPX · RevPi I/O |
| **Database** | PostgreSQL 17 |
| **Deployment** | Docker Compose · Nginx · systemd |

[**Architecture Deep Dive →**](architecture/overview.md)

---

## Documentation Map

| Section | For | What You'll Find |
|---|---|---|
| [Getting Started](getting-started/quick-start.md) | Everyone | Install, configure, first login |
| [User Guide](guide/index.md) | Operators & Engineers | Dashboard, experiments, rules, CSV export, OTA |
| [Architecture](architecture/overview.md) | Developers | System design, WebSocket protocol, database layer |
| [API Reference](api/rest.md) | Developers | REST + WebSocket endpoint docs, Pydantic schemas |
| [Development](development/contributing.md) | Contributors | Code style, testing, CI/CD, how to contribute |
| [Deployment](deployment/docker.md) | DevOps | Docker, production hardening, environment variables |

---

## Built With

<div class="grid-container" markdown>
<div class="grid-item" markdown>
:material-language-python: **Python 3.13** — Backend & Controller
</div>
<div class="grid-item" markdown>
:material-vuejs: **Vue 3** — Reactive SPA with TypeScript
</div>
<div class="grid-item" markdown>
:material-database: **PostgreSQL 17** — Reliable, proven storage
</div>
<div class="grid-item" markdown>
:material-docker: **Docker Compose** — One command, all services
</div>
</div>

---

## Contributing

Contributions are welcome! See the [Contributing Guide](development/contributing.md) for development setup and workflow.

---

## License

MIT — see [LICENSE](https://github.com/stefanposs/webmacs/blob/main/LICENSE) for details.