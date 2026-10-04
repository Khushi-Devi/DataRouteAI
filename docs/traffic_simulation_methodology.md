# DataRoute AI: Synthetic Traffic Dataset, Methodology and Code

> **All values are SYNTHETIC / SIMULATED. They are not real measurements.**
> Purpose: training and evaluating an LSTM that forecasts hourly traffic volume per directional region pair. The forecast feeds the routing and cost-optimization pipeline.

---

## 1. Outputs

| File | Contents |
|---|---|
| `traffic_history_30d.csv` | 72 pairs x 30 days x 24 h = 51,840 rows (2026-09-01 00:00 to 2026-09-30 23:00) |
| `traffic_history_15d.csv` | First 15 days of the 30-day file, identical values (25,920 rows, to 2026-09-15 23:00) |
| `anomaly_events_30d.csv` | Injected spikes and dips (94 events), kept separate from the data |
| `anomaly_events_15d.csv` | The 47 events that fall inside days 1 to 15 |
| `generate_traffic.py` | Full generator (reproduced in section 9) |

CSV columns: `timestamp,source_region,destination_region,traffic_volume_gb`

- `traffic_volume_gb` is GB per hour for the directional pair.
- Timestamps are IST (UTC+5:30), format `YYYY-MM-DD HH:MM:SS`, no timezone suffix.
- Rows are sorted by `timestamp`, then `source_region`, then `destination_region`. There is no index column and no anomaly column.

## 2. Reproducibility

- A single `np.random.RandomState(42)` drives every random draw.
- The 30-day series is generated first and the 15-day file is sliced from it, so days 1 to 15 are identical in both files.
- Suggested split: train on days 1 to 15 and validate or test on days 16 to 30.
- Draw order: (1) unordered-pair baselines, (2) directional split, (3) weekend factors for all pairs, (4) noise levels for all pairs, (5) per-pair day-level drift, noise initialisation and noise shocks in sorted pair order, (6) spike and dip events.

## 3. Pair baselines (off-peak level, GB/hour)

**3.1 City weights.** India hubs get higher weights.

| City | Weight |
|---|---|
| MUM | 1.0 |
| HYD | 0.8 |
| DEL | 0.7 |
| CIN (Pune) | 0.75 |
| SEA (assumed Chennai) | 0.6 |
| SIN | 0.5 |

**3.2 Unordered-pair raw level.** For each of the 36 unordered pairs {A, B}:

```
raw = weight(A) * weight(B) * same_provider_factor * LogNormal(0, 0.5)
same_provider_factor = 4.0 if same cloud provider else 1.0
```

Same-provider pairs, which model inter-region replication, therefore get larger baselines.

**3.3 Directional split.** The two directions of a pair differ by 10 to 30%.

```
diff       = Uniform(0.10, 0.30)
f_A->B     = 1 + diff/2   (or 1 - diff/2, chosen by a fair coin flip)
f_B->A     = 2 - f_A->B
dir_raw    = raw * f_direction
```

**3.4 Scale.** `k = 350 / max(dir_raw)`, then `baseline = clip(dir_raw * k, 5, 400)`. The baseline is the typical overnight or off-peak level.

## 4. Per-pair parameters

| Parameter | Distribution | Meaning |
|---|---|---|
| Weekend multiplier | `1 - Uniform(0.20, 0.35)` | 20 to 35% weekend reduction, fixed per pair |
| Noise standard deviation `sd` | `Uniform(0.05, 0.10)` | 5 to 10% multiplicative noise |
| AR(1) coefficient `phi` | 0.7 (fixed) | Hourly noise autocorrelation |

## 5. Clean (non-anomalous) series

For each directional pair and each hour `t`:

```
value(t) = baseline * profile(t) * weekend(t) * day_factor(t) * exp(e(t))
```

**5.1 Daily profile.** Off-peak equals 1.0. A business-hours Gaussian peaks near 14:00 and an evening bump sits near 21:00. Distances wrap around midnight.

```
f(h) = 1 + 1.25 * G(h; mu=14, sd=3.5) + 0.55 * G(h; mu=21, sd=2.0)
```

The business peak is about 2.25 times off-peak, and the evening bump is about 1.7 times.

**5.2 Source and destination local time.** The profile blends both ends of the pair.

```
profile(t) = 0.7 * f(local_hour_source) + 0.3 * f(local_hour_destination)
local_hour = (IST_hour + offset) mod 24      offset = +2.5 h for SIN regions, 0 otherwise
```

**5.3 Weekend effect.** Saturday and Sunday (IST date) are multiplied by the pair's weekend multiplier. Weekdays use 1.0. 2026-09-01 is a Tuesday.

**5.4 Day-level drift.** A slow AR(1) over the days, with standard deviation about 3%.

```
dl[i] = 0.5 * dl[i-1] + 0.03 * sqrt(0.75) * N(0,1)
day_factor = exp(dl[day])
```

**5.5 Hourly multiplicative AR(1) noise.** Adjacent hours are therefore correlated.

```
e[0] = sd * N(0,1)
e[t] = 0.7 * e[t-1] + sd * sqrt(1 - 0.7^2) * N(0,1)
```

## 6. Anomaly injection

Events are applied multiplicatively to the clean series. They are recorded only in the separate events file.

**6.1 Spikes.** 90 events in total, 45 in days 1 to 15 and 45 in days 16 to 30.

- Pair: chosen uniformly at random from the 72 pairs.
- Duration: 1 hour (30%), 2 hours (40%) or 3 hours (30%).
- Peak multiplier: `Uniform(1.5, 2.2)`.
- Shape across the duration: 1 h `[1.0]`, 2 h `[1.0, 0.7]`, 3 h `[0.6, 1.0, 0.6]`, applied as `1 + (peak - 1) * shape`.

**6.2 Dips.** 4 events, 2 in each half.

- Duration: 1 or 2 hours.
- Multiplier: `Uniform(0.30, 0.50)`, constant across the dip.

**6.3 Placement rules.** Events on the same pair keep a 2-hour gap, and no event crosses the day-15 boundary. This keeps the first 15 days self-contained.

## 7. Post-processing

1. Cap every value at 4 times the pair's baseline, to avoid extreme values.
2. Round to 2 decimals, with a floor of 0.01 so every value is positive.
3. Sort by timestamp, source, destination.
4. Write the 30-day file, then slice the first 360 hours for the 15-day file.

### Validation results (seed 42)

| Check | Result |
|---|---|
| Rows and pairs | 51,840 rows, 72 pairs, 720 rows each, no duplicates or nulls |
| 15-day file identical to first 15 days of 30-day file | Yes |
| Value range | 9.44 to 1,007.62 GB/hour, mean 96.6 |
| Peak and trough hours (all-pair average) | Peak 14:00, trough 03:00, ratio about 2.1 |
| Weekend reduction | Mean 27%, per-pair range 19% to 37% |
| Spike rows | 166 rows = 0.32% of all rows |
| Lag-24 autocorrelation (AWS_MUM to AWS_HYD) | 0.70 |
| Reverse-direction correlation (AWS_MUM to AWS_HYD vs reverse) | 0.93, mean volume ratio 1.14 |

## 8. Limitations

- The data is synthetic. It reflects assumptions about daily and weekly cycles, not observed cloud traffic.
- 15 days contains only about 4 weekend days, so an LSTM trained on it learns the weekly pattern weakly. The 30-day file has about 8 weekend days.
- Noise is lognormal-style and uniform across pairs. There are no long-term trends, holidays, or correlated failures across pairs.
- AZURE_SEA is assumed to be a South India (Chennai) region, based on the earlier supplied Azure latencies.
- "5 to 400 GB/hour" is the baseline, not the maximum. Peaks and spikes reach about 1,000 GB/hour.

## 9. Full code (`generate_traffic.py`)

```python
"""
DataRoute AI - SYNTHETIC hourly traffic generator (seed 42).

All values are SIMULATED. They are NOT real measurements.

Outputs (written next to this script):
  traffic_history_30d.csv   72 pairs x 30 days x 24 h = 51,840 rows
  traffic_history_15d.csv   first 15 days of the 30d file (25,920 rows, identical values)
  anomaly_events_30d.csv    injected spikes and dips (separate list, NOT a CSV column)
  anomaly_events_15d.csv    subset of events that fall inside days 1-15

CSV columns: timestamp,source_region,destination_region,traffic_volume_gb
traffic_volume_gb = GB per hour for the directional pair.
Timestamps are IST (UTC+5:30), no tz suffix, 2026-09-01 00:00:00 onward.
"""
import math
import os
import numpy as np
import pandas as pd

SEED = 42
START = pd.Timestamp("2026-09-01 00:00:00")      # Tuesday
DAYS = 30
HOURS = DAYS * 24
HALF = 15 * 24                                    # boundary between 15d and 30d files
OUT = os.path.dirname(os.path.abspath(__file__))

REGIONS = sorted(["AWS_MUM", "AWS_HYD", "AWS_SIN",
                  "AZURE_CIN", "AZURE_SIN", "AZURE_SEA",
                  "GCP_MUM", "GCP_DEL", "GCP_SIN"])

# City weight (India hubs higher) and local-time offset from IST in hours.
CITY_WEIGHT = {"MUM": 1.0, "HYD": 0.8, "DEL": 0.7, "CIN": 0.75, "SEA": 0.6, "SIN": 0.5}
TZ_OFFSET = {"MUM": 0.0, "HYD": 0.0, "DEL": 0.0, "CIN": 0.0, "SEA": 0.0, "SIN": 2.5}

def prov(r): return r.split("_")[0]
def city(r): return r.split("_")[1]

def gauss_wrap(h, mu, sd):
    d = abs(h - mu)
    d = np.minimum(d, 24 - d)
    return np.exp(-(d ** 2) / (2 * sd ** 2))

def daily_profile(local_hour):
    """Off-peak = 1.0, business peak (~14:00) ~2.25, evening bump (~21:00) ~1.7."""
    return 1.0 + 1.25 * gauss_wrap(local_hour, 14, 3.5) + 0.55 * gauss_wrap(local_hour, 21, 2.0)

rng = np.random.RandomState(SEED)

# ---- Step 1: pair baselines (GB/hour, off-peak level) ----------------------
pairs = [(s, d) for s in REGIONS for d in REGIONS if s != d]       # sorted
unordered = sorted({tuple(sorted(p)) for p in pairs})
raw = {}
for a, b in unordered:
    same = 4.0 if prov(a) == prov(b) else 1.0
    raw[(a, b)] = CITY_WEIGHT[city(a)] * CITY_WEIGHT[city(b)] * same * rng.lognormal(0, 0.5)

# Directional split: reverse baselines differ by 10-30%.
dir_raw = {}
for a, b in unordered:
    diff = rng.uniform(0.10, 0.30)
    hi_first = rng.rand() < 0.5
    f_a = 1 + diff / 2 if hi_first else 1 - diff / 2
    f_b = 2 - f_a
    dir_raw[(a, b)] = raw[(a, b)] * f_a
    dir_raw[(b, a)] = raw[(a, b)] * f_b
k = 350.0 / max(dir_raw.values())
baseline = {p: float(np.clip(v * k, 5.0, 400.0)) for p, v in dir_raw.items()}

# ---- Step 2: per-pair parameters --------------------------------------------
weekend_mult = {p: 1 - rng.uniform(0.20, 0.35) for p in pairs}      # 20-35% reduction
noise_sd = {p: rng.uniform(0.05, 0.10) for p in pairs}              # 5-10% multiplicative
PHI = 0.7                                                           # hourly AR(1)

idx = pd.date_range(START, periods=HOURS, freq="h")
ist_hour = np.asarray(idx.hour).astype(float)
is_weekend = np.asarray(idx.dayofweek >= 5)

# ---- Step 3: clean (non-anomalous) series per pair ---------------------------
series = {}
for (s, d) in pairs:
    loc_s = (ist_hour + TZ_OFFSET[city(s)]) % 24
    loc_d = (ist_hour + TZ_OFFSET[city(d)]) % 24
    prof = 0.7 * daily_profile(loc_s) + 0.3 * daily_profile(loc_d)
    wk = np.where(is_weekend, weekend_mult[(s, d)], 1.0)
    # slow day-level drift (AR(1) on days, sd 3%)
    dl = np.zeros(DAYS)
    for i in range(DAYS):
        dl[i] = (0.5 * dl[i - 1] if i else 0) + 0.03 * math.sqrt(1 - 0.25) * rng.randn()
    day_factor = np.exp(np.repeat(dl, 24))
    # hourly AR(1) multiplicative noise
    sd = noise_sd[(s, d)]
    e = np.zeros(HOURS)
    e[0] = sd * rng.randn()
    shocks = rng.randn(HOURS)
    for t in range(1, HOURS):
        e[t] = PHI * e[t - 1] + sd * math.sqrt(1 - PHI ** 2) * shocks[t]
    series[(s, d)] = baseline[(s, d)] * prof * wk * day_factor * np.exp(e)

# ---- Step 4: inject spikes and dips ------------------------------------------
SPIKE_SHAPE = {1: [1.0], 2: [1.0, 0.7], 3: [0.6, 1.0, 0.6]}
events = []
occupied = {p: np.zeros(HOURS, dtype=bool) for p in pairs}

def place(kind, n_events, lo, hi):
    placed = 0
    while placed < n_events:
        p = pairs[rng.randint(len(pairs))]
        dur = int(rng.choice([1, 2, 3], p=[0.3, 0.4, 0.3])) if kind == "spike" else int(rng.choice([1, 2]))
        start = int(rng.randint(lo, hi - dur + 1))
        if occupied[p][max(0, start - 2):start + dur + 2].any():
            continue
        occupied[p][start:start + dur] = True
        if kind == "spike":
            peak = rng.uniform(1.5, 2.2)
            shape = SPIKE_SHAPE[dur]
            mult = [1 + (peak - 1) * x for x in shape]
        else:
            peak = rng.uniform(0.30, 0.50)
            mult = [peak] * dur
        series[p][start:start + dur] *= np.array(mult)
        events.append(dict(event_type=kind, source_region=p[0], destination_region=p[1],
                           start_timestamp=idx[start], end_timestamp=idx[start + dur - 1],
                           duration_hours=dur, peak_multiplier=round(peak, 3),
                           in_15d_file=(start + dur) <= HALF))
        placed += 1

place("spike", 45, 0, HALF)
place("spike", 45, HALF, HOURS)
place("dip", 2, 0, HALF)
place("dip", 2, HALF, HOURS)

# ---- Step 5: cap extremes (<= 4x pair baseline), round, assemble -------------
rows = []
for (s, d) in pairs:
    v = np.minimum(series[(s, d)], 4.0 * baseline[(s, d)])
    v = np.maximum(np.round(v, 2), 0.01)
    rows.append(pd.DataFrame({"timestamp": idx.strftime("%Y-%m-%d %H:%M:%S"),
                              "source_region": s, "destination_region": d,
                              "traffic_volume_gb": v}))
df = pd.concat(rows).sort_values(["timestamp", "source_region", "destination_region"]).reset_index(drop=True)

df.to_csv(os.path.join(OUT, "traffic_history_30d.csv"), index=False)
cut = (START + pd.Timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
df15 = df[df["timestamp"] < cut]
df15.to_csv(os.path.join(OUT, "traffic_history_15d.csv"), index=False)

ev = pd.DataFrame(events).sort_values(["start_timestamp", "source_region", "destination_region"])
ev["start_timestamp"] = ev["start_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
ev["end_timestamp"] = ev["end_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
ev.insert(0, "event_id", range(1, len(ev) + 1))
ev.to_csv(os.path.join(OUT, "anomaly_events_30d.csv"), index=False)
ev[ev["in_15d_file"]].drop(columns="in_15d_file").to_csv(os.path.join(OUT, "anomaly_events_15d.csv"), index=False)
print("rows 30d:", len(df), " rows 15d:", len(df15), " events:", len(ev))
```