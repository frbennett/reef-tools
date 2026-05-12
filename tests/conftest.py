"""Shared test fixtures for reef_tools."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def sample_csv_path() -> Path:
    """Create a temporary CSV file following the {Model}_{Downscaling}_{Region}.csv convention."""
    data = {
        "time": pd.date_range("2000-01-01", periods=100, freq="YE"),
        "value": range(100),
    }
    df = pd.DataFrame(data)
    with tempfile.NamedTemporaryFile(
        suffix="_CCAM10_Tully.csv", delete=False, mode="w"
    ) as f:
        df.to_csv(f, index=False)
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Return a small sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=10, freq="ME"),
            "measurement": [1.0, 2.5, 3.0, 2.8, 4.0, 3.5, 5.0, 4.5, 6.0, 5.5],
        }
    )
