# Getting Started

## Installation

```bash
pip install reef-tools
```

Or install with all optional dependencies:

```bash
pip install "reef-tools[all]"
```

For development, install in editable mode with dev tooling:

```bash
git clone https://github.com/frbennett/reef-tools.git
cd reef-tools
pip install -e ".[dev,docs]"
```

## Quick Example

```python
from reef_tools.io import read_csv_smart
from reef_tools.utils import timer

@timer
def load_and_summarize(path: str) -> dict:
    df = read_csv_smart(path)
    return {
        "rows": len(df),
        "columns": list(df.columns),
    }

result = load_and_summarize("ACCESS-CM2_CCAM10_Tully.csv")
print(result)
```

Output:
```
load_and_summarize took 0.0123s
{'rows': 1200, 'columns': ['Model', 'Downscaling', 'Region', 'time', 'value']}
```

## Requirements

- Python 3.10 or later
- Core dependencies: numpy, pandas, matplotlib, scipy
- Optional: xarray, netCDF4 (for netCDF support)

## Where to Go Next

- Browse the [Module Guides](modules/io.md) for API usage
- See the [API Reference](api/index.md) for complete function signatures
- Read [Contributing](contributing.md) to add your own modules
