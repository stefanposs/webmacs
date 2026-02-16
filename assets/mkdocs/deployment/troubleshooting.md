# Troubleshooting

Common issues and their solutions when running WebMACS in production.

---

## Connection Issues

### WebSocket Disconnects

**Symptom:** Frontend shows "Connection lost" repeatedly, real-time data stops.

**Causes & Fixes:**

| Cause | Fix |
|---|---|
| nginx proxy timeout | Set `proxy_read_timeout 86400s;` in nginx config |
| Network instability | WebMACS auto-reconnects with exponential backoff — check network |
| Token expired | Re-login to refresh JWT (24h TTL) |
| Rate limiting | WS paths (`/ws/*`) are exempt by default — verify middleware config |

**Diagnostic:**

```bash
# Check WebSocket connectivity
wscat -c ws://localhost:8000/ws/controller/telemetry?token=<jwt>

# Check backend logs
docker compose logs backend --tail=100 | grep -i "websocket\|disconnect"
```

### Controller Cannot Reach Backend

**Symptom:** Controller logs `connection refused` or `timeout` errors, no sensor data arrives.

**Causes & Fixes:**

| Cause | Fix |
|---|---|
| Wrong `BACKEND_URL` | Verify `BACKEND_URL` in controller `.env` (default: `http://backend:8000`) |
| Backend not running | `docker compose ps` — check backend health |
| Docker network issue | Ensure both services are on the same Docker network |
| Auth failure | Check controller logs for `401` — re-register controller user |

**Diagnostic:**

```bash
# From controller container, test connectivity
docker compose exec controller curl -s http://backend:8000/health

# Check controller logs
docker compose logs controller --tail=100
```

---

## Database Issues

### Connection Pool Exhaustion

**Symptom:** `TimeoutError` or `QueuePool limit of X overflow Y reached` in backend logs.

**Causes & Fixes:**

| Cause | Fix |
|---|---|
| Too many concurrent requests | Increase `pool_size` in database config |
| Slow queries holding connections | Check for missing indexes, optimize queries |
| Connection leak | Ensure all sessions are properly closed (use `async with`) |

**Diagnostic:**

```bash
# Check active connections
just db-shell
SELECT count(*) FROM pg_stat_activity WHERE datname = 'webmacs';

# Check for long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC
LIMIT 10;
```

### Migration Failures

**Symptom:** `alembic upgrade head` fails on startup.

```bash
# Check current revision
docker compose exec backend alembic current

# View pending migrations
docker compose exec backend alembic history --verbose

# Force stamp to a known good state (last resort)
docker compose exec backend alembic stamp head
```

See [Database Migrations](../development/database-migrations.md) for detailed guide.

---

## Plugin Issues

### Plugin Fails to Load

**Symptom:** Plugin shows as installed but no channels appear, controller logs show errors.

**Common Causes:**

```bash
# Check controller logs for plugin errors
docker compose logs controller --tail=100 | grep -i "plugin\|error\|traceback"
```

| Cause | Fix |
|---|---|
| Missing entry point | Plugin `.whl` must declare `webmacs.plugins` entry point |
| Dependency conflict | Install with `--no-deps` and add dependencies separately |
| Wrong Python version | Plugin must be compatible with Python 3.13 |
| Architecture mismatch | ARM plugin on x86 host (or vice versa) |

### Plugin Channels Not Syncing

**Symptom:** Plugin is loaded, channels exist, but no events are created in the backend.

```bash
# Trigger manual sync
docker compose restart controller

# Check channel_mappings table
just db-shell
SELECT * FROM channel_mappings;
```

---

## OTA Update Issues

### Upload Fails (413 Entity Too Large)

**Symptom:** Bundle upload hangs or returns `413`.

**Fix:** Increase nginx upload limit:

```nginx
# nginx.conf
client_max_body_size 500M;
```

Then restart nginx:

```bash
docker compose restart nginx
```

### Update Stuck in "applying"

**Symptom:** Status stays at `applying` for more than 15 minutes.

```bash
# Check what's happening
docker compose logs --tail=200

# Force restart if safe
sudo systemctl restart webmacs

# The bundle moves to updates/failed/ on error
ls /opt/webmacs/updates/failed/
```

### Health Check Fails After Update

**Symptom:** All containers running but `/health` returns errors.

```bash
# Check each service
docker compose ps
docker compose logs backend --tail=50
docker compose logs controller --tail=50

# Restore database from pre-update backup
cat /opt/webmacs/updates/backups/webmacs_backup_*.sql | \
  docker compose exec -T db psql -U webmacs webmacs

# Restart
sudo systemctl restart webmacs
```

---

## Performance Issues

### Slow Datapoint Queries

**Symptom:** Dashboard loads slowly, CSV export times out.

**Causes:**

| Cause | Fix |
|---|---|
| Missing index | Verify `ix_datapoints_event_ts` exists: `\di` in psql |
| Too many datapoints | Use time-bounded queries, consider archival |
| No experiment filter | Always filter by experiment for bounded result sets |

**Diagnostic:**

```bash
just db-shell

-- Check table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(oid))
FROM pg_class
WHERE relname LIKE '%datapoint%';

-- Check index usage
SELECT indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
WHERE relname = 'datapoints';
```

### High Memory Usage

**Symptom:** Backend container uses excessive RAM.

**Causes:**

| Cause | Fix |
|---|---|
| Rate limiter state | Normal for high-traffic deployments; entries pruned every 60s |
| Large query results | Add pagination (`?skip=0&limit=100`) to API calls |
| Plugin memory leak | Check plugin code, restart controller periodically |

---

## Docker Issues

### Container Won't Start

```bash
# Check container state and exit code
docker compose ps -a

# View last logs before crash
docker compose logs backend --tail=50

# Common: database not ready yet
# The backend waits for PostgreSQL — check db container
docker compose logs db --tail=20
```

### Disk Space Full

```bash
# Check Docker disk usage
docker system df

# Remove unused images and volumes
docker system prune -a --volumes

# Check database backup directory
du -sh /opt/webmacs/updates/backups/
```

---

## Logging

### Enable Debug Logging

Set `DEBUG=true` in your `.env` file:

```bash
# .env
DEBUG=true
```

Then restart:

```bash
docker compose restart backend
```

### View Structured Logs

WebMACS uses `structlog` for structured logging. Filter by event type:

```bash
# All authentication events
docker compose logs backend | grep "auth\|login\|token"

# All WebSocket events
docker compose logs backend | grep "websocket\|ws_"

# All plugin events
docker compose logs controller | grep "plugin\|sync\|channel"
```

---

## Getting Help

If your issue isn't covered here:

1. Check the [Logs](../guide/logs.md) in the WebMACS UI
2. Search [GitHub Issues](https://github.com/stefanposs/webmacs/issues)
3. Open a new issue with:
    - WebMACS version (`curl http://localhost/api/v1/health`)
    - Docker logs (last 100 lines)
    - Steps to reproduce

---

## Next Steps

- [Production Deployment](production.md) — hardening, HTTPS, backups
- [Security](../guide/security.md) — authentication, rate limiting
- [OTA Updates](../guide/ota.md) — update process and recovery
