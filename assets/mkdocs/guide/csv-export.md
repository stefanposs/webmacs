# CSV Export

WebMACS lets you export all datapoints from a completed experiment as a CSV file with a single click.

---

## How It Works

The backend uses FastAPI's `StreamingResponse` to generate the CSV on-the-fly. This means:

- No file is written to disk
- Memory usage stays constant regardless of dataset size
- Download starts immediately

---

## Using the UI

1. Navigate to **Experiments**
2. Find a **stopped** experiment
3. Click the **:material-download: CSV** button
4. The browser downloads a file like `experiment_Fluidised_Bed_Run_07.csv`

---

## Using the API

```bash
curl -O http://localhost:8000/api/v1/experiments/$EXP_ID/export/csv \
  -H "Authorization: Bearer $TOKEN"
```

### Response Headers

```
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="experiment_My_Run.csv"
Transfer-Encoding: chunked
```

---

## CSV Format

```csv
public_id,value,timestamp,event_public_id,event_name,event_type,event_unit
dp_001,23.45,2025-01-15T14:32:10.000000,evt_temp01,Inlet Temperature,sensor,°C
dp_002,1.23,2025-01-15T14:32:10.500000,evt_pres01,Chamber Pressure,sensor,bar
```

| Column | Description |
|---|---|
| `public_id` | Unique datapoint ID |
| `value` | Measured value |
| `timestamp` | ISO 8601 timestamp |
| `event_public_id` | Parent event ID |
| `event_name` | Human-readable event name |
| `event_type` | Event type (sensor, actuator, …) |
| `event_unit` | Measurement unit |

---

## Next Steps

- [Experiments](experiments.md) — managing experiment lifecycle
- [REST API Reference](../api/rest.md) — full endpoint documentation
