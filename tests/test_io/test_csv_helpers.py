"""Tests for reef_tools.io.csv_helpers."""

from pathlib import Path

import pandas as pd
import pytest

from reef_tools.io.csv_helpers import read_csv_smart


class TestReadCsvSmart:
    """Tests for read_csv_smart."""

    def test_reads_basic_csv(self, sample_csv_path: Path):
        """Should read a CSV and return a DataFrame."""
        df = read_csv_smart(sample_csv_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 100

    def test_error_on_missing_file(self):
        """Should raise FileNotFoundError for non-existent file."""
        with pytest.raises(FileNotFoundError, match="nonexistent"):
            read_csv_smart("nonexistent_file.csv")

    def test_metadata_extraction_three_parts(self, sample_csv_path: Path):
        """Filename like X_CCAM10_Tully.csv should add Model, Downscaling, Region."""
        # sample_csv_path has _CCAM10_Tully suffix
        df = read_csv_smart(sample_csv_path)

        # The auto-generated name is random, so we check that 3 metadata cols exist
        meta_cols = [c for c in df.columns if c in ("Model", "Downscaling", "Region")]
        assert len(meta_cols) == 3

    def test_metadata_extraction_two_parts(self, tmp_path: Path):
        """Filename with two parts should add Category, Subcategory."""
        csv_path = tmp_path / "TypeA_VariantB.csv"
        df = pd.DataFrame({"x": [1, 2, 3]})
        df.to_csv(csv_path, index=False)

        result = read_csv_smart(csv_path)
        assert "Category" in result.columns
        assert "Subcategory" in result.columns
        assert result["Category"].iloc[0] == "TypeA"
        assert result["Subcategory"].iloc[0] == "VariantB"

    def test_no_metadata_extraction_when_disabled(self, tmp_path: Path):
        """metadata_split=None should skip metadata extraction."""
        csv_path = tmp_path / "Model_Downscaling_Region.csv"
        df = pd.DataFrame({"x": [1, 2, 3]})
        df.to_csv(csv_path, index=False)

        result = read_csv_smart(csv_path, metadata_split=None)
        assert "Model" not in result.columns
        assert "Region" not in result.columns

    def test_date_parsing(self, sample_dataframe: pd.DataFrame, tmp_path: Path):
        """Date column should be parsed as datetime."""
        csv_path = tmp_path / "test.csv"
        sample_dataframe.to_csv(csv_path, index=False)

        result = read_csv_smart(csv_path)
        assert pd.api.types.is_datetime64_any_dtype(result["date"])

    def test_passthrough_kwargs(self, sample_csv_path: Path):
        """Additional kwargs should be passed to pd.read_csv."""
        df = read_csv_smart(sample_csv_path, nrows=10)
        assert len(df) == 10
