# Statistics Module

Statistical analysis tools for trend detection, change-point analysis,
and serial-dependence testing on hydrological time series.

All functions accept 1-D array-like inputs (typically annual flow totals)
and return dictionaries with p-values, test statistics, and significance flags.

## Stationarity & Trend Tests

::: reef_tools.stats.stationarity.pettitt_test
    options:
      heading_level: 3

::: reef_tools.stats.stationarity.mann_kendall
    options:
      heading_level: 3

::: reef_tools.stats.stationarity.rank_sum_test
    options:
      heading_level: 3

## Randomness & Serial Dependence

::: reef_tools.stats.stationarity.median_crossing_test
    options:
      heading_level: 3

::: reef_tools.stats.stationarity.rank_difference_test
    options:
      heading_level: 3

## Quick Reference

| Test | Purpose | Key output |
|---|---|---|
| `pettitt_test` | Step change detection | p-value, change index |
| `mann_kendall` | Monotonic trend | tau, Sen slope, direction |
| `rank_sum_test` | Pre/post median comparison | delta %, p-value |
| `median_crossing_test` | Serial independence (crossings) | p-value, description |
| `rank_difference_test` | Serial independence (rank diffs) | von Neumann ratio |

## Usage

```python
import numpy as np
from reef_tools.stats import pettitt_test, mann_kendall

annual_flows = np.array([...])  # ML/yr

# Check for step change
pt = pettitt_test(annual_flows)
if pt["significant"]:
    print(f"Step change at index {pt['change_idx']}")

# Check for monotonic trend
mk = mann_kendall(annual_flows)
print(f"Trend: {mk['direction']}, tau={mk['tau']:.3f}, p={mk['p_value']:.4f}")
```
