# DataRoute AI: Simulation Methodology for `network_metrics.csv`

## 1. Data provenance

| Rows | latency_ms | packet_loss_pct | reliability |
|---|---|---|---|
| 6 AWS same-provider | Real/public | **Simulated** (Method A) | Derived (Method C) |
| 6 Azure same-provider | Real/public | **Simulated** (Method A) | Derived (Method C) |
| 6 GCP same-provider | Real/public | Real/public | Derived (Method C) |
| 54 cross-cloud | **Simulated** (Method B) | **Simulated** (Method B) | Derived (Method C) |

All simulation uses a NumPy legacy RNG seeded with 42: `np.random.seed(42)` for Method A and `np.random.RandomState(42)` for Method B.

---

## 2. Method A: AWS and Azure packet loss (12 rows)

- **Input:** The 12 same-provider AWS and Azure rows, taken in sorted (source, destination) order. GCP rows are skipped because their loss is real.
- **Distribution:** Uniform, `packet_loss_pct = round(uniform(0.002, 0.025), 4)`.
- **Why this range:** It is small and positive, it sits just above the real GCP range of 0 to 0.01%, and it has a hard cap of 0.025%. 4-decimal rounding avoids exact copies of GCP's values.
- **Draw order:** One uniform draw per row, so the same seed and order reproduce the same values.

```python
import numpy as np
np.random.seed(42)
p = round(float(np.random.uniform(0.002, 0.025)), 4)   # once per AWS/Azure row
```

---

## 3. Method B: 54 cross-cloud pairs (latency and packet loss)

**Scope:** All directional pairs where the source and destination providers differ. That is 9 x 6 = 54, because each region has 6 destinations on the other two providers.

### Step 1: Distance

Use the haversine great-circle distance (in km) between the two region cities.

| Region suffix | City used |
|---|---|
| MUM | Mumbai (19.076, 72.878) |
| HYD | Hyderabad (17.385, 78.487) |
| DEL | Delhi (28.614, 77.209) |
| SIN | Singapore (1.352, 103.820) |
| AZURE_CIN | Pune (18.520, 73.857) |
| AZURE_SEA | Chennai (13.083, 80.271), an assumption based on the supplied Azure latencies |

### Step 2: Latency formula (RTT, ms)

```
latency_ms = round( 2 * distance_km * 1.4 / 200  +  5  +  8  +  N(0, 2) ),  minimum 8
```

| Term | Meaning |
|---|---|
| `2 * distance * 1.4 / 200` | Round-trip fiber propagation. Light travels about 200 km/ms in fiber, and 1.4 is a route-inflation factor because cable paths are longer than straight lines. |
| `+ 5` | Fixed equipment and processing overhead, calibrated against the real same-provider latencies. |
| `+ 8` | Fixed cross-provider penalty for the peering or IX handoff between clouds. |
| `N(0, 2)` | Gaussian noise (mean 0, standard deviation 2 ms), drawn independently per direction so A to B and B to A can differ. |
| `min 8` | Floor so no latency is unrealistically low. |

### Step 3: Packet loss

Same distribution as Method A: `round(uniform(0.002, 0.025), 4)`.

### Step 4: Draw order

Rows are processed in sorted (source, destination) order. For each row, draw the normal noise value first, then the uniform packet-loss value.

```python
rng = np.random.RandomState(42)
for s, d in sorted_cross_cloud_pairs:
    km  = haversine(loc[city(s)], loc[city(d)])
    lat = max(round(2*km*1.4/200 + 5 + 8 + rng.normal(0, 2)), 8)
    p   = round(float(rng.uniform(0.002, 0.025)), 4)
```

### Worked example: AWS_HYD to GCP_MUM

The distance is about 622 km. The propagation term is 2 x 622 x 1.4 / 200 = about 8.7 ms. Adding 5 + 8 gives 21.7 ms. The noise draw was about +3.3 ms, so the final value is **25 ms**.

### Calibration check

The model gives about 16 ms for Mumbai to Delhi and about 56 ms for Mumbai to Singapore. The real GCP values are 22 ms and 60 ms.

---

## 4. Method C: Reliability (all 72 rows)

```
reliability = 1 - (packet_loss_pct / 100)
```

Round to 6 decimals.

**Examples:**

- `packet_loss_pct = 0.0188` gives 1 - 0.000188 = **0.999812**
- `packet_loss_pct = 0.01` (GCP) gives **0.9999**
- `packet_loss_pct = 0` (GCP) gives **1.0**

Reliability is never generated independently. It is always computed from the packet-loss column.

---

## 5. Limitations

- The cross-cloud latencies are a physics-based approximation, not measurements. Real inter-cloud paths depend on peering agreements, so actual values can differ noticeably.
- Packet loss is drawn uniformly and independently. It is not correlated with distance, latency, provider or time of day.
- The 8 ms cross-provider penalty and the 1.4 route factor are fixed assumptions, not fitted statistically.
- The AZURE_SEA location is an assumption (see Method B, Step 1).
- The dataset is meant for route evaluation and optimization experiments, not as ML training data.

---

## 6. Reproducibility

The network dataset can be regenerated deterministically using the
specified random seeds, row ordering, formulas, geographic coordinates,
and simulation parameters described above.

Any change to the seed, row ordering, region coordinates, distribution
bounds, or model parameters may produce different simulated values.

The generated values in `network_metrics.csv` should therefore be
treated as one reproducible simulation instance rather than measured
network observations.