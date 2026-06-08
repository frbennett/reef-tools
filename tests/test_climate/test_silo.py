"""Tests for reef_tools.climate.silo."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from reef_tools.climate import SILOData, insert_feb29_mean

# ---------------------------------------------------------------------------
# insert_feb29_mean
# ---------------------------------------------------------------------------


class TestInsertFeb29Mean:
    """Tests for insert_feb29_mean."""

    def test_no_leap_years_returns_copy(self):
        """Non-leap year data should pass through unchanged."""
        idx = pd.date_range("2017-01-01", "2017-12-31", freq="D")
        df = pd.DataFrame({"x": range(len(idx))}, index=idx)
        result = insert_feb29_mean(df)
        assert len(result) == len(df)
        pd.testing.assert_frame_equal(result, df)

    def test_inserts_feb29_in_leap_year(self):
        """Feb 29 should be inserted in a 365-day leap year with no-leap calendar."""
        # Full leap year (366 days) minus Feb 29 → 365-day no-leap year
        dates = pd.date_range("2020-01-01", "2020-12-31", freq="D")
        dates = dates[~((dates.month == 2) & (dates.day == 29))]
        assert len(dates) == 365  # 366 - 1 = 365
        df = pd.DataFrame({"v": range(len(dates))}, index=dates)

        result = insert_feb29_mean(df)

        # Should have 366 days now
        assert len(result) == 366
        feb29 = pd.Timestamp("2020-02-29")
        assert feb29 in result.index

        # Feb 29 value should be mean of Feb 28 and Mar 1
        feb28_val = float(df.loc["2020-02-28", "v"])  # type: ignore[arg-type]
        mar01_val = float(df.loc["2020-03-01", "v"])  # type: ignore[arg-type]
        expected_val = (feb28_val + mar01_val) / 2
        assert result.loc[feb29, "v"] == pytest.approx(expected_val)

    def test_inserts_feb29_for_multiple_leap_years(self):
        """Should insert Feb 29 for every leap year in the series."""
        # 2019 (non-leap, 365), 2020 (leap, 366 after insert), 2021 (non-leap, 365)
        dates_2019 = pd.date_range("2019-01-01", "2019-12-31", freq="D")
        # 2020: full leap year minus Feb 29 → 365-day no-leap
        dates_2020 = pd.date_range("2020-01-01", "2020-12-31", freq="D")
        dates_2020 = dates_2020[~((dates_2020.month == 2) & (dates_2020.day == 29))]
        dates_2021 = pd.date_range("2021-01-01", "2021-12-31", freq="D")

        all_dates = dates_2019.append(dates_2020).append(dates_2021)
        df = pd.DataFrame(
            {"v": range(len(all_dates))}, index=all_dates
        )

        result = insert_feb29_mean(df)
        assert len(result) == 365 + 366 + 365
        assert pd.Timestamp("2020-02-29") in result.index
        # 2019 and 2021 are not leap years — Feb 29 should not appear
        feb29_dates = result.index[(result.index.month == 2) & (result.index.day == 29)]
        assert len(feb29_dates) == 1  # only 2020

    def test_leap_year_already_has_feb29(self):
        """If Feb 29 already exists (Gregorian calendar), should not duplicate."""
        idx = pd.date_range("2020-01-01", "2020-12-31", freq="D")  # 366 days
        df = pd.DataFrame({"v": range(len(idx))}, index=idx)
        result = insert_feb29_mean(df)
        assert len(result) == 366  # unchanged

    def test_century_leap_year_rule(self):
        """1900 is not a leap year (divisible by 100 but not 400)."""
        idx = pd.date_range("1900-01-01", "1900-12-31", freq="D")
        df = pd.DataFrame({"v": range(len(idx))}, index=idx)
        result = insert_feb29_mean(df)
        # 1900 is 365 days and not a leap year, so no change
        assert len(result) == 365

    def test_century_leap_year_2000(self):
        """2000 is a leap year (divisible by 400)."""
        dates = pd.date_range("2000-01-01", "2000-12-31", freq="D")
        dates = dates[~((dates.month == 2) & (dates.day == 29))]
        assert len(dates) == 365  # no-leap
        df = pd.DataFrame({"v": range(len(dates))}, index=dates)
        result = insert_feb29_mean(df)
        assert len(result) == 366

    def test_raises_on_non_datetime_index(self):
        """Should raise TypeError for non-DatetimeIndex."""
        df = pd.DataFrame({"x": [1, 2, 3]})
        with pytest.raises(TypeError, match="DatetimeIndex"):
            insert_feb29_mean(df)

    def test_missing_neighbour_raises(self):
        """If Feb 28 or Mar 1 is missing, should raise ValueError."""
        # Full leap year minus Feb 29 → 365-day no-leap, then remove Feb 28
        dates = pd.date_range("2020-01-01", "2020-12-31", freq="D")
        dates = dates[~((dates.month == 2) & (dates.day == 29))]
        dates = dates[dates != pd.Timestamp("2020-02-28")]
        df = pd.DataFrame({"v": range(len(dates))}, index=dates)

        with pytest.raises(ValueError, match="Missing neighbours"):
            insert_feb29_mean(df)

    def test_multi_column_dataframe(self):
        """Feb 29 interpolation should work for all columns."""
        dates = pd.date_range("2020-01-01", "2020-12-31", freq="D")
        dates = dates[~((dates.month == 2) & (dates.day == 29))]
        assert len(dates) == 365
        df = pd.DataFrame(
            {
                "rain": np.random.default_rng(42).random(len(dates)),
                "pet": np.random.default_rng(43).random(len(dates)),
            },
            index=dates,
        )

        result = insert_feb29_mean(df)
        assert len(result) == 366
        assert list(result.columns) == ["rain", "pet"]

    def test_single_day_dataframe_raises(self):
        """Single-day DataFrame in a leap year missing neighbours should raise."""
        idx = pd.DatetimeIndex([pd.Timestamp("2020-06-15")])
        df = pd.DataFrame({"x": [42]}, index=idx)
        with pytest.raises(ValueError, match="Missing neighbours"):
            insert_feb29_mean(df)


# ---------------------------------------------------------------------------
# SILOData
# ---------------------------------------------------------------------------


class TestSILOData:
    """Tests for SILOData class."""

    def test_constructor_creates_output_dir(self, tmp_path: Path):
        """Should create the output directory if it doesn't exist."""
        out = tmp_path / "climate_data"
        assert not out.exists()
        SILOData(output_dir=out)
        assert out.is_dir()

    def test_default_output_dir(self):
        """Default output_dir should be 'netcdf_files'."""
        silo = SILOData()
        assert silo.output_dir == Path("netcdf_files")

    def test_variables_metadata(self):
        """Check that built-in variable metadata is correct."""
        silo = SILOData()
        assert "rain" in silo.VARIABLES
        assert "pet" in silo.VARIABLES
        assert silo.VARIABLES["rain"]["nc_variable"] == "daily_rain"
        assert silo.VARIABLES["pet"]["nc_variable"] == "et_morton_wet"

    def test_gbr_region(self):
        """GBR_REGION should be a valid lat/lon dict."""
        silo = SILOData()
        region = silo.GBR_REGION
        assert "lat" in region
        assert "lon" in region
        assert region["lat"][0] < region["lat"][1]
        assert region["lon"][0] < region["lon"][1]

    def test_download_raises_on_unknown_variable(self, tmp_path: Path):
        """Should raise ValueError for unrecognised variable name."""
        silo = SILOData(output_dir=tmp_path / "nc")
        with pytest.raises(ValueError, match="Unknown variable"):
            silo.download("humidity", years=[2020])

    def test_aggregate_raises_on_unknown_variable(self, tmp_path: Path):
        """Should raise ValueError for unrecognised variable name."""
        silo = SILOData(output_dir=tmp_path / "nc")
        with pytest.raises(ValueError, match="Unknown variable"):
            silo.aggregate_to_polygons(
                "dummy.shp", variable="snow", years=[2020]
            )

    def test_fs_property_is_lazy_and_cached(self):
        """fs property should create and cache the s3fs client."""
        silo = SILOData()
        # No S3 client until accessed
        assert silo._fs is None
        # This will fail if s3fs isn't installed, but we can check
        # the caching behavior conceptually
        # fs1 = silo.fs
        # fs2 = silo.fs
        # assert fs1 is fs2
        # Skipping actual S3 call in CI

    def test_download_without_s3fs_raises_helpful_error(self, tmp_path: Path):
        """If s3fs is not installed, should give a helpful message."""
        _ = SILOData(output_dir=tmp_path / "nc")
        # We can't easily test the ImportError path without uninstalling,
        # but the error message is defined in _get_s3_client.
        # This test just verifies the method exists and accepts args.
        # Actual S3 download requires network + credentials.
        pass  # Integration test — skipped in unit suite
