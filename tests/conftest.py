"""Shared test fixtures for reef_tools."""

from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def sample_csv_path(tmp_path: Path) -> Path:
    """Create a CSV with known 3-part metadata filename: {Model}_{Downscaling}_{Region}.csv."""
    filename = tmp_path / "ACCESS-CM2_CCAM10_Tully.csv"
    data = {
        "time": pd.date_range("2000-01-01", periods=100, freq="YE"),
        "value": range(100),
    }
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    return filename


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Return a small sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=10, freq="ME"),
            "measurement": [1.0, 2.5, 3.0, 2.8, 4.0, 3.5, 5.0, 4.5, 6.0, 5.5],
        }
    )
