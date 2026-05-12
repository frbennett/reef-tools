# Contributing

## Adding a New Module

Adding a new subpackage is straightforward:

1. **Create the directory** under `src/reef_tools/`:
   ```
   src/reef_tools/sediment/
   ```

2. **Add `__init__.py`** with a docstring and any public exports:
   ```python
   """Sediment transport utilities."""

   from reef_tools.sediment.transport import load_rating_curve

   __all__ = ["load_rating_curve"]
   ```

3. **Write your module** (e.g., `transport.py`) with Google-style docstrings.

4. **Add tests** in `tests/test_sediment/`.

5. **Optionally add docs** at `docs/modules/sediment.md` and update `mkdocs.yml`.

## Development Setup

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

## Building Documentation

```bash
mkdocs serve    # Live preview at http://localhost:8000
mkdocs build    # Static build to site/
```

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

## Release Process

1. Update version in `src/reef_tools/_version.py`
2. Update `docs/changelog.md`
3. Commit: `git commit -m "chore: bump to vX.Y.Z"`
4. Tag: `git tag vX.Y.Z`
5. Push: `git push && git push --tags`
