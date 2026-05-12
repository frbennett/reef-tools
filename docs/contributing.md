# Contributing

This guide covers how to add new modules and scripts to `reef_tools`,
run the test suite, build documentation, and follow project conventions.

## Table of Contents

- [Quick Setup](#quick-setup)
- [Running Tests](#running-tests)
- [Code Quality](#code-quality)
- [Docstring Style](#docstring-style)
- [Adding a New Module](#adding-a-new-module)
- [Adding a Script](#adding-a-script)
- [Building Documentation](#building-documentation)
- [Release Process](#release-process)

---

## Quick Setup

```bash
git clone https://github.com/frbennett/reef-tools.git
cd reef-tools
pip install -e ".[dev,docs]"
```

## Running Tests

```bash
pytest tests/ -v
```

With coverage:

```bash
pytest tests/ -v --cov=reef_tools --cov-report=term-missing
```

## Code Quality

We use `ruff` for linting and formatting, and `mypy` for type checking:

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
```

Run all three before committing:

```bash
ruff check src/ tests/ && mypy src/ && pytest tests/
```

---

## Docstring Style

All public functions use [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings):

```python
def example(param1: str, param2: int = 0) -> bool:
    """Short description.

    Longer description if needed.

    Args:
        param1: Description of param1.
        param2: Description of param2. Defaults to 0.

    Returns:
        Description of the return value.

    Raises:
        ValueError: When param1 is empty.

    Example:
        >>> example("hello", 42)
        True
    """
    ...
```

The [API Reference](api/index.md) is auto-generated from these docstrings by `mkdocstrings`
— no separate API docs to maintain.

---

## Adding a New Module

A **module** is a Python file inside one of the subpackages under `src/reef_tools/`.
You can add a module to an existing subpackage or create an entirely new subpackage.

### Step-by-Step: New Subpackage

Suppose you want to add a `sediment` subpackage for sediment transport utilities.

#### 1. Create the directory and files

```
src/reef_tools/sediment/
├── __init__.py          # Package init — docstring + public exports
└── transport.py         # Your module code
```

#### 2. Write `__init__.py`

```python
"""Sediment transport utilities — rating curves, load estimation."""

from reef_tools.sediment.transport import estimate_load, load_rating_curve

__all__ = ["estimate_load", "load_rating_curve"]
```

This makes imports clean for users:

```python
from reef_tools.sediment import estimate_load  # works
```

#### 3. Write your module (`transport.py`)

Every public function gets a Google-style docstring (see [above](#docstring-style)):

```python
"""Sediment transport calculations."""

import numpy as np
import pandas as pd


def load_rating_curve(discharge: pd.Series, concentration: pd.Series) -> dict:
    """Fit a power-law rating curve: C = a * Q^b.

    Args:
        discharge: Discharge time series (m³/s).
        concentration: Corresponding concentration (mg/L).

    Returns:
        dict with keys ``a``, ``b``, ``r2``.

    Example:
        >>> q = pd.Series([10, 20, 30])
        >>> c = pd.Series([5, 14, 27])
        >>> load_rating_curve(q, c)
        {'a': 0.5, 'b': 1.3, 'r2': 0.99}
    """
    ...
```

#### 4. Add tests

Tests mirror the package structure exactly:

```
tests/test_sediment/
├── __init__.py              # Empty file
└── test_transport.py        # One test file per module
```

Use `tmp_path` for any temporary files (never `tempfile.NamedTemporaryFile` — its random
prefixes can break string-split assertions on Python 3.13).

```python
"""Tests for reef_tools.sediment.transport."""

import pandas as pd

from reef_tools.sediment.transport import load_rating_curve


class TestLoadRatingCurve:
    def test_basic_fit(self):
        q = pd.Series([10, 20, 30])
        c = pd.Series([5, 14, 27])
        result = load_rating_curve(q, c)
        assert "a" in result
        assert "b" in result
        assert 0 <= result["r2"] <= 1
```

Run to verify:

```bash
pytest tests/test_sediment/ -v
```

#### 5. Add docs (optional but recommended)

Create `docs/modules/sediment.md`:

```markdown
# Sediment Module

Sediment transport utilities for load estimation and rating curves.

## `transport`

::: reef_tools.sediment.transport
    options:
      show_root_heading: false
      heading_level: 3
```

Then add it to the navigation in `mkdocs.yml`:

```yaml
nav:
  - Module Guides:
      - I/O: modules/io.md
      - Sediment: modules/sediment.md     # ← add this line
      - Statistics: modules/stats.md
```

#### 6. Run the full quality check and commit

```bash
ruff check src/ tests/ && mypy src/ && pytest tests/ -v
git add -A
git commit -m "feat: add sediment subpackage with rating curve fitting"
git push
```

### Adding a Module to an Existing Subpackage

Even simpler — just add your `.py` file to the existing subpackage directory,
export it from that subpackage's `__init__.py`, add a test file, and you're done.

---

## Adding a Script

A **script** is a standalone Python program that ships with the package and
can be run from the command line after `pip install`. There are two approaches:

### Approach A: Module with `__main__.py` (recommended for simple scripts)

Create a module that doubles as a runnable script:

```
src/reef_tools/scripts/
├── __init__.py          # Empty (or exports shared helpers)
├── summarize_csv.py     # The script logic
└── __main__.py          # Entry point when run as `python -m reef_tools.scripts`
```

**`summarize_csv.py`** — put the actual logic in a function:

```python
"""Summarize a CSV file — print row count and column names."""

import argparse
import sys
from pathlib import Path

from reef_tools.io import read_csv_smart


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on success, 1 on error."""
    parser = argparse.ArgumentParser(description="Summarize a CSV file.")
    parser.add_argument("path", type=Path, help="Path to CSV file")
    args = parser.parse_args(argv)

    try:
        df = read_csv_smart(args.path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    return 0
```

**Register as a console script** in `pyproject.toml`:

```toml
[project.scripts]
reef-summarize = "reef_tools.scripts.summarize_csv:main"
```

After `pip install -e .`, the user can run:

```bash
reef-summarize ACCESS-CM2_CCAM10_Tully.csv
```

### Approach B: `__main__.py` for subpackage-level scripts

If the script is more of a developer tool, add `__main__.py` to the subpackage:

```python
# src/reef_tools/scripts/__main__.py
"""Run as: python -m reef_tools.scripts <command> [args]"""

import sys
from reef_tools.scripts import summarize_csv

if __name__ == "__main__":
    sys.exit(summarize_csv.main())
```

Then it's runnable without a console_scripts entry:

```bash
python -m reef_tools.scripts path/to/file.csv
```

### Testing Scripts

Test the `main()` function directly (no subprocess needed):

```python
"""Tests for summarize_csv script."""

from reef_tools.scripts.summarize_csv import main


def test_valid_csv(tmp_path):
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("a,b,c\n1,2,3\n4,5,6\n")

    exit_code = main([str(csv_path)])
    assert exit_code == 0


def test_missing_file():
    exit_code = main(["nonexistent.csv"])
    assert exit_code == 1
```

### Conventions for Scripts

| Rule | Reason |
|------|--------|
| `main(argv=None) -> int` signature | Testable without `sys.argv` manipulation |
| Return 0 for success, 1 for errors | Standard Unix exit codes |
| Use `argparse` for argument parsing | Consistent with the Python ecosystem |
| Print errors to `stderr` | Lets users redirect stdout separately |
| Register in `[project.scripts]` | Makes the script available as a CLI command after install |

---

## Building Documentation

```bash
mkdocs serve    # Live preview at http://localhost:8000
mkdocs build    # Static build to site/
```

Docs deploy automatically to [frbennett.github.io/reef-tools](https://frbennett.github.io/reef-tools/)
on every push to `main` via the `docs.yml` workflow.

---

## Release Process

1. Update version in `src/reef_tools/_version.py`
2. Update `docs/changelog.md`
3. Run full checks: `ruff check src/ tests/ && mypy src/ && pytest tests/ -v`
4. Commit: `git commit -m "chore: bump to vX.Y.Z"`
5. Tag: `git tag vX.Y.Z`
6. Push: `git push && git push --tags`
