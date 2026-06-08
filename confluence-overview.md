# reef-tools — Shared Python Utilities for the DETSI Group

## What Is It?

`reef-tools` is a Python package — a collection of reusable scripts and functions
that anyone in the group can install with one command and import into their own
code. Think of it as a shared toolbox: instead of copying functions between scripts
or digging through old notebooks, you `import reef_tools` and everything is there.

It lives on GitHub and installs directly into your Python environment.
You don't need to know git to use it; you just need to run the install command once.

## Why Use It?

| Problem | How reef-tools solves it |
|---------|--------------------------|
| "Where's that CSV reader Fred wrote?" | `from reef_tools.io import read_csv_smart` |
| "I have five different copies of the same trend function" | One canonical version, imported by everyone |
| "My script works on my machine but not my colleague's" | Package ensures consistent dependencies for everyone |
| "How do I document this for the next person?" | Automatic docs from docstrings — no separate effort |

## What's In It Right Now (v0.1.0)

| Area | What it does | Import it with |
|------|-------------|----------------|
| **I/O** | Read CSV files, extract metadata from filenames, parse dates | `from reef_tools.io import read_csv_smart` |
| **Utils** | Decorators: `@timer` (measure execution time), `@cache_result` (avoid recomputing) | `from reef_tools.utils import timer, cache_result` |
| **Stats** | *(coming)* Mann-Kendall trends, Sen's slope, Monte Carlo uncertainty | `from reef_tools.stats import mann_kendall` |
| **Viz** | *(coming)* Faceted time series plots, multi-model comparison charts | `from reef_tools.viz import faceted_timeseries` |
| **Climate** | *(coming)* CMIP6 model name parsing, downscaling label conventions | `from reef_tools.climate import parse_model_name` |
| **Water Quality** | *(coming)* DIN, TSS, discharge calculations, load estimation | `from reef_tools.water_quality import calc_din_load` |

## How to Install (One-Time Setup)

Open a terminal (Command Prompt, Anaconda Prompt, or WSL) and run:

```
pip install git+https://github.com/frbennett/reef-tools.git
```

That's it. After this, `import reef_tools` works in any Python script or notebook.

To upgrade to the latest version later:

```
pip install --upgrade git+https://github.com/frbennett/reef-tools.git
```

## How to Use It

Once installed, use it like any other Python package:

```python
# Read a CSV and auto-extract metadata from the filename
from reef_tools.io import read_csv_smart

df = read_csv_smart("ACCESS-CM2_CCAM10_Tully.csv")
print(df.columns)
# ['Model', 'Downscaling', 'Region', 'time', 'value']

# Time a slow function to see how long it takes
from reef_tools.utils import timer

@timer
def my_analysis(data):
    # ... complex calculations ...
    return result

my_analysis(large_dataset)
# Prints: my_analysis took 12.3456s
```

Everything works in Jupyter notebooks too — same imports, same results.

## How the Package Is Organised (Modularity)

`reef-tools` is split into domains (called "subpackages"), each covering one topic:

```
reef_tools/
├── io/              Everything about reading and writing data
├── stats/           Statistical tests and trend analysis
├── viz/             Plots and visualisation
├── climate/         Climate model conventions and metadata
├── water_quality/   Water quality calculations and metrics
└── utils/           Helpers, decorators, convenience functions
```

Each domain is **independent**. Adding a new one (like `sediment/`) doesn't touch
or risk breaking any of the others. This is the same pattern used by `scipy`
and `scikit-learn` — proven across thousands of packages.

### Example: Importing from a Specific Domain

```python
# Import one function
from reef_tools.io import read_csv_smart

# Import everything from a domain
from reef_tools.io import *

# Access a domain directly
import reef_tools.stats as stats
result = stats.mann_kendall(my_data)
```

## Adding Your Own Functions (Extensibility)

The package is designed to grow. Adding a new function or an entire new domain
is straightforward — it does **not** require editing any central config file
or registry. If you're comfortable writing Python functions, you can contribute.

### Adding a Single Function to an Existing Domain

Suppose you have a function that belongs in `stats/`. Steps:

1. **Write your function** in a `.py` file inside `src/reef_tools/stats/`
   (or ask someone with git access to add it for you)

2. **Add your function to the exports** in `src/reef_tools/stats/__init__.py`

Once merged, everyone gets the new function on their next `pip install --upgrade`.

### Adding a Whole New Domain

Example: creating a `sediment/` subpackage for sediment transport.

1. Create the directory: `src/reef_tools/sediment/`
2. Add `__init__.py` and your module file (e.g., `transport.py`)
3. Write tests in `tests/test_sediment/`
4. Add a short doc page (optional)

That's the entire process. No other files need to change — the package discovers
the new subpackage automatically.

### If You Don't Use Git

The workflow for non-git users is:

1. Write your function as a standalone `.py` file and test it locally
2. Send it to a git user (Fred, or whoever maintains the package)
3. They integrate it, commit, and push
4. Everyone runs `pip install --upgrade` to get the new function

If the group grows and more people want to contribute directly, a
[GitHub Desktop](https://desktop.github.com/) guide can be provided — it's
a visual tool that doesn't require terminal commands.

## Documentation

Full documentation with examples is at:

**[https://frbennett.github.io/reef-tools/](https://frbennett.github.io/reef-tools/)**

It updates automatically whenever new code is added — nobody needs to
manually maintain docs pages. Every function's docstring becomes
searchable documentation.

## Requirements

- **Python 3.10 or newer** (check with `python --version`)
- Core dependencies install automatically: `numpy`, `pandas`, `matplotlib`, `scipy`
- Optional: `xarray` and `netCDF4` (only if you work with netCDF files)

## Getting Help

- **Package documentation:** [frbennett.github.io/reef-tools](https://frbennett.github.io/reef-tools/)
- **Source code + issues:** [github.com/frbennett/reef-tools](https://github.com/frbennett/reef-tools)
- **Direct questions:** Ask Fred (bennett.f@…)

---

*Version 0.1.0 — this is an early release with the core structure in place.
New modules for stats, viz, climate, and water quality are actively being developed.
Feedback and feature requests are welcome.*
