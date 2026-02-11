# CSV Export

WebMACS lets you download all datapoints from a completed experiment as a CSV file — ready to open in Excel, Google Sheets, or import into analysis tools like Python/pandas or MATLAB.

---

## How It Works

The CSV is generated **on-the-fly** using streaming. This means:

- :material-check: No temporary file is created on the server
- :material-check: Memory usage stays constant regardless of dataset size
- :material-check: Download starts immediately, even for millions of rows
- :material-check: Data is ordered by timestamp (oldest first)

---

## Using the UI

1. Navigate to **Experiments** in the sidebar
2. Find a **stopped** experiment
3. Click the :material-download: **CSV** button
4. The browser downloads a file named like `experiment_Fluidised_Bed_Run_07_a1b2c3d4.csv`

!!! info "Running experiments"
    You can only export data from stopped experiments. Stop the experiment first if it's still running.

---

## Using the API

```bash
curl -o results.csv \
  http://localhost:8000/api/v1/experiments/$EXP_ID/export/csv \
  -H "Authorization: Bearer $TOKEN"
```

### Response Headers

```
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="experiment_My_Run_a1b2c3d4.csv"
Transfer-Encoding: chunked
```

---

## CSV Format

```csv
timestamp,event_name,event_public_id,value,unit,datapoint_public_id
2025-01-15T14:32:10.000000,Inlet Temperature,evt_temp01,23.45,°C,dp_001
2025-01-15T14:32:10.000000,Chamber Pressure,evt_pres01,1.23,bar,dp_002
2025-01-15T14:32:10.500000,Inlet Temperature,evt_temp01,23.51,°C,dp_003
```

### Columns

| Column | Description |
|---|---|
| `timestamp` | ISO 8601 timestamp (UTC) |
| `event_name` | Human-readable sensor/actuator name |
| `event_public_id` | Event unique identifier |
| `value` | Measured value (float) |
| `unit` | Measurement unit (°C, bar, L/min, …) |
| `datapoint_public_id` | Unique datapoint identifier |

---

## Working with the Data

=== "Excel / Google Sheets"

    Simply open the downloaded `.csv` file. Columns are comma-separated with UTF-8 encoding. Most spreadsheet applications detect the format automatically.

=== "Python / pandas"

    ```python
    import pandas as pd

    df = pd.read_csv("experiment_Run_07_a1b2c3d4.csv", parse_dates=["timestamp"])

    # Filter by sensor
    temp = df[df["event_name"] == "Inlet Temperature"]

    # Plot
    temp.plot(x="timestamp", y="value", title="Inlet Temperature")
    ```

=== "MATLAB"

    ```matlab
    data = readtable('experiment_Run_07_a1b2c3d4.csv');
    temp = data(strcmp(data.event_name, 'Inlet Temperature'), :);
    plot(temp.timestamp, temp.value);
    ```

---

## Tips

!!! tip "Recommendations"
    - **Export frequently** — CSV files are the easiest way to back up experiment data
    - **Filter in your analysis tool** — the CSV contains all events mixed together; filter by `event_name` or `event_public_id` to isolate individual sensors
    - **Timestamps are UTC** — convert to your local timezone in your analysis tool if needed
    - **Large datasets** — the streaming approach handles millions of rows, but very large files may take a moment to download

---

## Next Steps

- [Experiments](experiments.md) — manage experiment lifecycle
- [Events & Sensors](events.md) — understand what data is collected
- [Dashboard](dashboard.md) — monitor live data while an experiment runs
