# reef-tools

[![CI](https://github.com/frbennett/reef-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/frbennett/reef-tools/actions/workflows/ci.yml)
[![docs](https://github.com/frbennett/reef-tools/actions/workflows/docs.yml/badge.svg)](https://frbennett.github.io/reef-tools/)
[![Python](https://img.shields.io/pypi/pyversions/reef-tools.svg)](https://pypi.org/project/reef-tools/)
[![License](https://img.shields.io/github/license/frbennett/reef-tools.svg)](LICENSE)

**Modular Python package for reef and water quality analysis** — shared utilities for the
DETSI group.

## Quick Start

```bash
pip install reef-tools
```

```python
from reef_tools.io import read_csv_smart
from reef_tools.stats import mann_kendall
from reef_tools.viz import faceted_timeseries
```

Or install the development version with all extras:

```bash
pip install "reef-tools[all]"
```

## Package Structure

| Module | Purpose |
|--------|---------|
| `reef_tools.io` | Data I/O — CSV helpers, netCDF loading |
| `reef_tools.stats` | Statistical analysis — trends, distributions |
| `reef_tools.viz` | Visualization — time series, faceted plots |
| `reef_tools.climate` | Climate model utilities — name parsing, labels |
| `reef_tools.water_quality` | Water quality metrics — DIN, TSS, discharge |
| `reef_tools.utils` | General utilities — decorators, helpers |

## Documentation

Full documentation at **[frbennett.github.io/reef-tools](https://frbennett.github.io/reef-tools/)**.

## Contributing

See [CONTRIBUTING.md](docs/contributing.md) for how to add modules, run tests, and build docs.

## License

MIT — see [LICENSE](LICENSE).
