# WebMACS — Product Roadmap & Feature Backlog

> Auto-generated from multi-agent strategy consultation (Stakeholder, Architect, Python Expert, Frontend Expert).

---

## Unique Value Proposition

> **WebMACS is the only open-source IoT platform purpose-built for running, monitoring, and exporting scientific experiments on resource-constrained edge hardware — with actuator control included.**

---

## Target Markets (Priority Order)

| Segment | Fit | Revenue Potential |
|---------|-----|-------------------|
| University Labs / Research | Excellent | €5K–20K (grants) |
| Vocational / STEM Education | Excellent | Institutional budgets |
| Small Industrial / Process Eng. | Good | €10K–50K |
| Hobbyist / Maker | Moderate | Community growth |
| Industrial OEMs (white-label) | Future | Very High |

---

## Roadmap

### Phase 1 — Now (0–3 months)

| Feature | Effort | Impact | Owner |
|---------|--------|--------|-------|
| Alerting & Thresholds | Medium | Critical | Backend + Frontend |
| Data Retention & Downsampling | Medium | Critical | Backend |
| Database Indexes | Low | Critical | Backend |
| WebSocket Authentication | Low | Critical | Backend |
| TLS Termination (nginx) | Low | High | DevOps |
| Rate Limiting | Low | High | Backend |
| Connection Pool Tuning (RPi) | Low | High | Backend |
| Dark Mode | Low | High | Frontend |
| Mobile Responsiveness | Low–Med | High | Frontend |
| Structured Logging | Low | Medium | Backend |
| One-Click Backup & Restore | Low | High | DevOps |
| LICENSE file | Low | Required | Done ✅ |

### Phase 2 — Next (3–6 months)

| Feature | Effort | Impact | Owner |
|---------|--------|--------|-------|
| MQTT / Modbus Driver Support | High | Critical | Controller |
| Plugin/Driver System (Entry-Point) | Medium | High | Controller |
| RBAC (viewer/operator/admin) | Medium | High | Backend |
| First-Run Setup Wizard | Medium | High | Frontend |
| i18n (German/English) | Medium | Medium | Frontend |
| Experiment Templates & Cloning | Low | Medium | Backend |
| Virtual Scrolling / Perf | Low–Med | High | Frontend |
| Threshold Alerts + Sound | Medium | High | Frontend |
| Sparklines / Gauges | Medium | High | Frontend |
| Controller Watchdog | Medium | High | Controller |
| In-Process Background Task Queue | Medium | High | Backend |
| Write Coalescing Buffer | Medium | High | Backend |
| Cursor Pagination + Filtering | Medium | Medium | Backend |

### Phase 3 — Later (6–12 months)

| Feature | Effort | Impact | Owner |
|---------|--------|--------|-------|
| Dashboard Customization (drag-and-drop) | High | High | Frontend |
| PWA / Offline Mode | Medium | Medium | Frontend |
| Audit Log & Experiment Annotations | Medium | Medium | Backend |
| OPC-UA Driver | High | High | Controller |
| Observability (Prometheus metrics) | Medium | Medium | Backend |
| Multi-tenant / White-label | Very High | Very High | All |

---

## Business Model Recommendation

**Open-Source Core (MIT)** + Commercial Add-ons:

1. **Consulting** — €5K–15K for on-site setup, custom sensor integration, training
2. **Hardware Bundles** — Pre-configured RevPi + WebMACS (partner with KUNBUS)
3. **Commercial Plugins** — Advanced alerting, LDAP/SSO, audit logs, OPC-UA
4. **Annual Support License** — €500–2K/year for priority support + updates

---

## Architecture Decisions

### RPi Resource Budget (2GB target)

| Component | Memory Target | Strategy |
|-----------|---------------|----------|
| PostgreSQL | 400 MB | `shared_buffers=128MB`, `max_connections=20` |
| Backend (uvicorn) | 150 MB | 2 workers, `pool_size=5` |
| Frontend (nginx) | 30 MB | Static files, 2 workers |
| Controller | 80 MB | Single process, async I/O |
| OS + Docker | 340 MB | Alpine-based images |
| **Total** | **~1 GB** | Leaves 1 GB headroom |

### Plugin Driver Architecture

- `ProtocolDriver` ABC with `connect/read/write/disconnect`
- Entry-point based registry via `importlib.metadata`
- Declarative channel-to-driver mapping (YAML config)
- Install only needed drivers (separate pip packages)

### Data Retention Strategy

- Tier 1: Raw data — last 24h, full precision
- Tier 2: 1-min averages — last 30 days
- Tier 3: 15-min averages — last 1 year
- Tier 4: Exported CSV — archive off-device

---

## Security Priorities

1. ~~LICENSE file~~ ✅
2. TLS termination (nginx self-signed certs)
3. Rate limiting (in-memory, no Redis)
4. WebSocket authentication (token param)
5. Validate `SECRET_KEY` at startup
6. RBAC (viewer/operator/admin roles)
7. Token blacklist auto-cleanup
8. WebSocket input validation (Pydantic)

---

## Frontend Priorities

1. Dark mode (CSS vars already in place)
2. Mobile responsiveness (collapsible sidebar)
3. Accessibility improvements
4. Virtual scrolling for large tables
5. Threshold alerts + sound notifications
6. Sparklines in sensor cards
7. i18n (DE/EN)
8. UX polish (keyboard shortcuts, breadcrumbs)
9. PWA / offline support
10. Dashboard customization (widget grid)
