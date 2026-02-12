# Frontend Architecture

The frontend is a **Vue 3 Single Page Application** built with TypeScript, PrimeVue 4, and Vite 6.

---

## Project Structure

```
frontend/src/
├── main.ts                 # App bootstrap, plugin registration
├── App.vue                 # Root component (sidebar + router view)
├── router/
│   └── index.ts            # Vue Router routes (12 views + 404)
├── views/
│   ├── LoginView.vue       # Public — JWT authentication
│   ├── DashboardView.vue   # Default overview dashboard
│   ├── DashboardsView.vue  # Dashboard list (CRUD)
│   ├── DashboardCustomView.vue  # User-built widget dashboard
│   ├── ExperimentsView.vue # Experiment lifecycle management
│   ├── EventsView.vue      # Sensor/channel definitions
│   ├── DatapointsView.vue  # Time-series data explorer
│   ├── LogsView.vue        # System log viewer
│   ├── UsersView.vue       # User management (admin)
│   ├── RulesView.vue       # Automation rule builder (admin)
│   ├── WebhooksView.vue    # Webhook management (admin)
│   ├── OtaView.vue         # Firmware OTA updates (admin)
│   └── NotFoundView.vue    # 404 page
├── components/
│   ├── AppSidebar.vue      # Navigation sidebar
│   ├── AppTopbar.vue       # Top bar with user menu
│   ├── AppToast.vue        # Global toast container
│   └── widgets/
│       ├── WidgetWrapper.vue       # Grid drag-drop wrapper
│       ├── LineChartWidget.vue     # Time-series line chart
│       ├── GaugeWidget.vue         # Radial gauge display
│       ├── StatCardWidget.vue      # KPI stat card
│       └── ActuatorToggleWidget.vue # On/off toggle control
├── stores/                 # Pinia state stores (8)
│   ├── auth.ts             # JWT token, user info, login/logout
│   ├── experiments.ts      # Experiment CRUD + active tracking
│   ├── events.ts           # Event/channel CRUD
│   ├── datapoints.ts       # Datapoint queries + time-series
│   ├── dashboards.ts       # Dashboard + widget CRUD
│   ├── rules.ts            # Rule CRUD
│   ├── webhooks.ts         # Webhook CRUD + delivery history
│   └── ota.ts              # OTA update management
├── composables/
│   ├── useRealtimeDatapoints.ts  # WS-first with HTTP polling fallback
│   ├── usePolling.ts             # Generic polling composable
│   ├── useNotification.ts       # Toast notification helper
│   └── useFormatters.ts         # Date/number formatting
├── services/
│   ├── api.ts              # Axios instance with JWT interceptor
│   └── websocket.ts        # Reconnecting WebSocket client
├── types/
│   └── index.ts            # TypeScript interfaces + enums
└── assets/
    └── main.css            # Global styles
```

---

## State Management — Pinia

Eight stores manage application state, each corresponding to a backend resource:

| Store | Key State | Key Actions |
|---|---|---|
| `auth` | `user`, `token`, `isAuthenticated` | `login()`, `logout()`, `fetchMe()` |
| `experiments` | `experiments`, `activeExperiment` | `fetchAll()`, `create()`, `stop()`, `exportCsv()` |
| `events` | `events` | `fetchAll()`, `create()`, `update()`, `delete()` |
| `datapoints` | `datapoints`, `series` | `fetchAll()`, `fetchSeries()`, `fetchLatest()` |
| `dashboards` | `dashboards`, `currentDashboard` | `fetchAll()`, `createWidget()`, `updateWidget()` |
| `rules` | `rules` | `fetchAll()`, `create()`, `update()`, `toggleActive()` |
| `webhooks` | `webhooks`, `deliveries` | `fetchAll()`, `create()`, `fetchDeliveries()` |
| `ota` | `updates`, `checking` | `fetchAll()`, `checkForUpdate()`, `applyUpdate()` |

---

## Real-Time Data — `useRealtimeDatapoints`

The core composable implements a **WebSocket-first strategy with automatic HTTP polling fallback**:

```
┌──────────────┐    Connected     ┌──────────────┐
│  connecting  │ ───────────────► │  websocket   │
└──────┬───────┘                  └──────┬───────┘
       │ 3 failures                      │ disconnect
       ▼                                 │
┌──────────────┐                         │
│   polling    │ ◄───────────────────────┘
└──────────────┘   WS reconnects → back to 'websocket'
```

- **Default poll interval**: 1500ms (configurable)
- **WS max failures before fallback**: 3 attempts
- **WS reconnect**: Exponential back-off (1s → 30s max)
- **WS keep-alive**: Ping every 25s

```typescript
type ConnectionMode = 'websocket' | 'polling' | 'connecting'

const { latestDatapoints, connectionMode, isConnected } = useRealtimeDatapoints()
```

---

## WebSocket Client

The `WebSocketClient` class in `services/websocket.ts` is a generic reconnecting wrapper:

- **Auto-reconnect** with exponential back-off (1s initial, 30s max)
- **Ping/pong** keep-alive (25s interval)
- **Protocol auto-detection** (`ws:` / `wss:` based on page protocol)
- **Clean dispose** for component unmount

---

## Dashboard Widgets

The custom dashboard system uses a **grid layout** with drag-and-drop positioning:

| Widget | Type Enum | Purpose |
|---|---|---|
| `LineChartWidget` | `line_chart` | Time-series chart (Chart.js) |
| `GaugeWidget` | `gauge` | Radial gauge for single values |
| `StatCardWidget` | `stat_card` | KPI card with current value |
| `ActuatorToggleWidget` | `actuator_toggle` | On/off toggle control |

Each widget has a JSON `config` object and grid position (`x`, `y`, `w`, `h`).

---

## API Service

All HTTP requests go through a single Axios instance (`services/api.ts`):

- **Base URL**: `/api/v1/` (proxied by Vite dev server or Nginx)
- **JWT interceptor**: Attaches `Authorization: Bearer <token>` to every request
- **401 handling**: Auto-logout on expired tokens
- **Error transform**: Normalizes API errors for toast notifications

---

## Routing

Vue Router with navigation guards:

- **Public routes**: `/login`
- **Protected routes**: Everything else (redirects to `/login` if no token)
- **Admin routes**: Users, Rules, Webhooks, OTA (hidden from non-admins)
- **404 catch-all**: `NotFoundView`

---

## UI Framework — PrimeVue 4

- **Theme**: Aura Dark (customized via CSS variables)
- **Key components**: DataTable, Dialog, Chart, InputNumber, Dropdown, Toast, Sidebar
- **Accessibility**: ARIA labels on all icon-only buttons

---

## Next Steps

- [WebSocket Protocol](websocket.md) — message formats and authentication
- [Dashboard Guide](../guide/dashboard.md) — creating custom dashboards
- [REST API](../api/rest.md) — backend endpoints