"""Tahbil Water Data Portal — loader and processing for daily stream loads.

The Queensland DES Tahbil portal (https://apps.des.qld.gov.au/water-data-portal/map)
provides daily pollutant load data for GBR catchments. Since the portal has no API,
data must be downloaded manually as CSV files. This module provides a loader that:

- Reads one or more Tahbil-format CSVs from a directory
- Builds a consolidated Parquet cache for fast subsequent access
- Detects stale caches and rebuilds automatically
- Supports filtering by region, basin, catchment, site, analyte, and date range

Example:
    >>> from reef_tools.water_quality import TahbilData
    >>> td = TahbilData("path/to/tahbil_csvs/")
    >>> df = td.load()  # first call builds cache; subsequent calls are instant
    >>> df = td.load(regions=["Burdekin"], analytes=["Total suspended solids"])
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Expected columns in a Tahbil CSV download
TAHBIL_COLUMNS = [
    "Data Source",
    "Region",
    "Basin",
    "Catchment",
    "Site Code",
    "Site Name",
    "Latitude",
    "Longitude",
    "Datum",
    "Sampling Year",
    "Date",
    "Analyte",
    "Load (t)",
    "Calculation Method",
]

# GBR NRM region codes and full names
REGION_MAP = {
    "CY": "Cape York",
    "BM": "Burnett Mary",
    "BU": "Burdekin",
    "FI": "Fitzroy",
    "MW": "Mackay Whitsunday",
    "WT": "Wet Tropics",
}


class TahbilData:
    """Loader and processor for Tahbil portal daily stream load data.

    Parameters
    ----------
    data_dir : str or Path
        Directory containing one or more Tahbil-format CSV files.
    cache_dir : str, Path, or None
        Directory for the Parquet cache. Defaults to ``data_dir/_cache/``.
        Set to None to disable caching (always read from CSV).

    Attributes
    ----------
    data_dir : Path
        Resolved path to the raw CSV directory.
    cache_dir : Path or None
        Resolved path to the Parquet cache directory.
    """

    def __init__(
        self,
        data_dir: str | Path,
        cache_dir: str | Path | None = "auto",
    ) -> None:
        self.data_dir = Path(data_dir).resolve()
        if not self.data_dir.is_dir():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

        if cache_dir == "auto":
            self.cache_dir: Path | None = self.data_dir / "_cache"
        elif cache_dir is None:
            self.cache_dir = None
        else:
            self.cache_dir = Path(cache_dir).resolve()

        self._df: pd.DataFrame | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(
        self,
        *,
        regions: str | Sequence[str] | None = None,
        basins: str | Sequence[str] | None = None,
        catchments: str | Sequence[str] | None = None,
        sites: str | Sequence[str] | None = None,
        analytes: str | Sequence[str] | None = None,
        date_from: str | pd.Timestamp | None = None,
        date_to: str | pd.Timestamp | None = None,
        rebuild: bool = False,
    ) -> pd.DataFrame:
        """Load Tahbil data with optional filtering.

        Parameters
        ----------
        regions : str or list of str, optional
            Filter by Region name (e.g., "Burdekin", "Cape York").
            Also accepts region codes: "BU", "CY", etc.
        basins : str or list of str, optional
            Filter by Basin name.
        catchments : str or list of str, optional
            Filter by Catchment name.
        sites : str or list of str, optional
            Filter by Site Code or Site Name.
        analytes : str or list of str, optional
            Filter by Analyte name (e.g., "Total suspended solids").
        date_from : str or Timestamp, optional
            Start date (inclusive).
        date_to : str or Timestamp, optional
            End date (inclusive).
        rebuild : bool
            Force rebuild of the Parquet cache.

        Returns
        -------
        pd.DataFrame
            Filtered DataFrame with columns matching TAHBIL_COLUMNS.
        """
        df = self._get_dataframe(rebuild=rebuild)

        # Apply filters
        if regions is not None:
            regions_list = _ensure_list(regions)
            # Allow region codes (BU, CY) or full names
            expanded = []
            for r in regions_list:
                if r.upper() in REGION_MAP:
                    expanded.append(REGION_MAP[r.upper()])
                else:
                    expanded.append(r)
            df = df[df["Region"].isin(expanded)]

        if basins is not None:
            df = df[df["Basin"].isin(_ensure_list(basins))]

        if catchments is not None:
            df = df[df["Catchment"].isin(_ensure_list(catchments))]

        if sites is not None:
            sites_list = _ensure_list(sites)
            df = df[
                df["Site Code"].isin(sites_list) | df["Site Name"].isin(sites_list)
            ]

        if analytes is not None:
            df = df[df["Analyte"].isin(_ensure_list(analytes))]

        if date_from is not None:
            df = df[df["Date"] >= pd.Timestamp(date_from)]

        if date_to is not None:
            df = df[df["Date"] <= pd.Timestamp(date_to)]

        return df.reset_index(drop=True)

    def annual_loads(
        self,
        *,
        by: str | Sequence[str] = "Site Code",
        **filter_kwargs,
    ) -> pd.DataFrame:
        """Aggregate daily loads to annual totals.

        Parameters
        ----------
        by : str or list of str
            Grouping columns. Default groups by Site Code.
            Common choices: "Site Code", "Catchment", "Basin", "Region".
        **filter_kwargs
            Passed to :meth:`load` for filtering before aggregation.

        Returns
        -------
        pd.DataFrame
            Annual loads in tonnes with columns:
            [*by, "Analyte", "Sampling Year", "Annual Load (t)"]
        """
        df = self.load(**filter_kwargs)
        by_cols = _ensure_list(by)

        group_cols = by_cols + ["Analyte", "Sampling Year"]
        result = (
            df.groupby(group_cols, as_index=False, observed=True)
            .agg(**{"Annual Load (t)": ("Load (t)", "sum")})
        )
        return result

    def monthly_loads(
        self,
        *,
        by: str | Sequence[str] = "Site Code",
        **filter_kwargs,
    ) -> pd.DataFrame:
        """Aggregate daily loads to monthly totals.

        Parameters
        ----------
        by : str or list of str
            Grouping columns. Default groups by Site Code.
        **filter_kwargs
            Passed to :meth:`load` for filtering before aggregation.

        Returns
        -------
        pd.DataFrame
            Monthly loads with columns:
            [*by, "Analyte", "Year", "Month", "Monthly Load (t)"]
        """
        df = self.load(**filter_kwargs)
        by_cols = _ensure_list(by)

        df = df.copy()
        df["Year"] = df["Date"].dt.year
        df["Month"] = df["Date"].dt.month

        group_cols = by_cols + ["Analyte", "Year", "Month"]
        result = (
            df.groupby(group_cols, as_index=False, observed=True)
            .agg(**{"Monthly Load (t)": ("Load (t)", "sum")})
        )
        return result

    def pivot_analytes(self, **filter_kwargs) -> pd.DataFrame:
        """Pivot from long to wide format — one column per analyte.

        Parameters
        ----------
        **filter_kwargs
            Passed to :meth:`load` for filtering.

        Returns
        -------
        pd.DataFrame
            Wide DataFrame with one column per analyte showing daily
            loads in tonnes.
        """
        df = self.load(**filter_kwargs)

        index_cols = [
            c for c in ["Region", "Basin", "Catchment", "Site Code", "Site Name", "Date"]
            if c in df.columns
        ]
        result = df.pivot_table(
            index=index_cols,
            columns="Analyte",
            values="Load (t)",
            aggfunc="sum",
        ).reset_index()
        result.columns.name = None
        return result

    def sites(self) -> pd.DataFrame:
        """Return a summary of all monitoring sites.

        Returns
        -------
        pd.DataFrame
            One row per site with Region, Basin, Catchment, Site Code,
            Site Name, Latitude, Longitude, date range, and record count.
        """
        df = self._get_dataframe()
        site_cols = [
            "Region", "Basin", "Catchment", "Site Code",
            "Site Name", "Latitude", "Longitude",
        ]
        sites_df = (
            df.groupby(site_cols, as_index=False, observed=True)
            .agg(
                n_records=("Date", "count"),
                date_min=("Date", "min"),
                date_max=("Date", "max"),
            )
        )
        return sites_df.sort_values(["Region", "Basin", "Site Code"]).reset_index(drop=True)

    def analytes(self) -> list[str]:
        """Return a sorted list of unique analyte names."""
        df = self._get_dataframe()
        return sorted(df["Analyte"].unique().tolist())

    def analytes_by_site(
        self,
        sites: str | Sequence[str] | None = None,
    ) -> pd.DataFrame:
        """Show which analytes are available at each site.

        Parameters
        ----------
        sites : str or list of str, optional
            Filter to specific site codes or names. If None, shows all sites.

        Returns
        -------
        pd.DataFrame
            Boolean matrix with Site Code as rows and Analyte as columns.
            True indicates the analyte is available at that site.
        """
        df = self._get_dataframe()

        if sites is not None:
            sites_list = _ensure_list(sites)
            df = df[
                df["Site Code"].isin(sites_list) | df["Site Name"].isin(sites_list)
            ]

        matrix = (
            df.groupby(["Site Code", "Site Name", "Analyte"], observed=True)
            .size()
            .unstack(fill_value=0)
            .gt(0)
            .reset_index()
        )
        matrix.columns.name = None
        return matrix

    def regions(self) -> list[str]:
        """Return a sorted list of unique region names."""
        df = self._get_dataframe()
        return sorted(df["Region"].unique().tolist())

    def map(
        self,
        *,
        regions: str | Sequence[str] | None = None,
        basemap: str = "OpenStreetMap",
        width: str | int = "100%",
        height: str | int = 600,
        zoom_start: int | None = None,
    ):
        """Create an interactive map of monitoring sites.

        Requires ``folium`` to be installed (``pip install folium``).

        Parameters
        ----------
        regions : str or list of str, optional
            Filter to specific regions. Accepts codes (BU, WT) or full names.
        basemap : str
            Base tile layer. Options: "OpenStreetMap", "Satellite", "Terrain",
            "CartoDB positron", "CartoDB dark_matter".
        width : str or int
            Map width (CSS value or pixels).
        height : str or int
            Map height (CSS value or pixels).
        zoom_start : int, optional
            Initial zoom level. Auto-calculated from data extent if None.

        Returns
        -------
        folium.Map
            Interactive Leaflet map. Renders inline in Jupyter notebooks.
        """
        from reef_tools.water_quality.mapping import site_map

        return site_map(
            self,
            regions=regions,
            basemap=basemap,
            width=width,
            height=height,
            zoom_start=zoom_start,
        )

    def report(
        self,
        *,
        format: str | None = "markdown",
        save_to: str | Path | None = None,
        **filter_kwargs,
    ) -> dict[str, pd.DataFrame] | str:
        """Generate a data quality summary report.

        Parameters
        ----------
        format : str or None
            If "markdown" or "text", returns a formatted string.
            If None, returns the raw dict of DataFrames.
        save_to : str or Path, optional
            Save the report to a file. Supports .md, .txt, .xlsx.
        **filter_kwargs
            Passed to :meth:`load` for filtering before reporting.

        Returns
        -------
        dict or str
            Raw report DataFrames (format=None) or formatted string.
        """
        from reef_tools.water_quality.reporting import (
            format_report,
            generate_report,
            save_report,
        )

        report_data = generate_report(self, **filter_kwargs)

        if save_to is not None:
            save_report(report_data, save_to, format=format)

        if format is None:
            return report_data
        return format_report(report_data, format=format)

    def rebuild_cache(self) -> None:
        """Force rebuild of the Parquet cache from raw CSVs."""
        self._df = None
        self._get_dataframe(rebuild=True)

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _get_dataframe(self, rebuild: bool = False) -> pd.DataFrame:
        """Load data from cache or CSV, rebuilding cache if needed."""
        # Return in-memory copy if already loaded
        if self._df is not None and not rebuild:
            return self._df

        cache_path = self._cache_path()

        # Check if cache is valid
        if not rebuild and cache_path is not None and cache_path.exists():
            if not self._cache_is_stale(cache_path):
                logger.info("Loading from Parquet cache: %s", cache_path)
                self._df = pd.read_parquet(cache_path)
                return self._df
            else:
                logger.info("Cache is stale, rebuilding...")

        # Read all CSVs
        df = self._read_all_csvs()
        self._df = df

        # Write cache
        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(cache_path, index=False, engine="pyarrow")
            logger.info(
                "Cache written: %s (%.1f MB)",
                cache_path, cache_path.stat().st_size / 1e6,
            )

        return self._df

    def _read_all_csvs(self) -> pd.DataFrame:
        """Read and concatenate all Tahbil-format CSVs in data_dir."""
        csv_files = self._find_csv_files()
        if not csv_files:
            raise FileNotFoundError(
                f"No Tahbil-format CSV files found in {self.data_dir}"
            )

        frames = []
        for f in csv_files:
            logger.info("Reading %s...", f.name)
            df = self._read_single_csv(f)
            frames.append(df)

        result = pd.concat(frames, ignore_index=True)
        logger.info(
            "Loaded %d records from %d files (%d sites, %d analytes)",
            len(result), len(csv_files),
            result["Site Code"].nunique(), result["Analyte"].nunique(),
        )
        return result

    def _read_single_csv(self, path: Path) -> pd.DataFrame:
        """Read a single Tahbil CSV with correct dtypes and date parsing."""
        df = pd.read_csv(
            path,
            dtype={
                "Data Source": "category",
                "Region": "category",
                "Basin": "category",
                "Catchment": "category",
                "Site Code": str,
                "Site Name": "category",
                "Latitude": np.float64,
                "Longitude": np.float64,
                "Datum": "category",
                "Sampling Year": "category",
                "Analyte": "category",
                "Load (t)": np.float64,
                "Calculation Method": "category",
            },
            parse_dates=["Date"],
            dayfirst=True,
        )

        # Validate columns
        missing = set(TAHBIL_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(
                f"File {path.name} is missing expected columns: {missing}. "
                f"Is this a Tahbil portal download?"
            )

        return df

    def _find_csv_files(self) -> list[Path]:
        """Find CSV files in data_dir that match Tahbil format."""
        csv_files = sorted(self.data_dir.glob("*.csv"))

        # Validate each file has the expected header
        valid = []
        for f in csv_files:
            try:
                header = pd.read_csv(f, nrows=0).columns.tolist()
                if set(TAHBIL_COLUMNS).issubset(set(header)):
                    valid.append(f)
                else:
                    logger.debug(
                        "Skipping %s — columns don't match Tahbil format", f.name
                    )
            except Exception:
                logger.debug("Skipping %s — could not read header", f.name)

        return valid

    def _cache_path(self) -> Path | None:
        """Return the path to the Parquet cache file."""
        if self.cache_dir is None:
            return None
        return self.cache_dir / "tahbil_loads.parquet"

    def _cache_is_stale(self, cache_path: Path) -> bool:
        """Check if any CSV is newer than the cache."""
        cache_mtime = cache_path.stat().st_mtime
        for f in self._find_csv_files():
            if f.stat().st_mtime > cache_mtime:
                return True
        return False

    def __repr__(self) -> str:
        n_files = len(self._find_csv_files())
        cache_path = self._cache_path()
        cached = "cached" if cache_path is not None and cache_path.exists() else "no cache"
        return f"TahbilData(data_dir='{self.data_dir}', files={n_files}, {cached})"


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------


def _ensure_list(x: str | Sequence[str]) -> list[str]:
    """Coerce a string or sequence to a list of strings."""
    if isinstance(x, str):
        return [x]
    return list(x)
