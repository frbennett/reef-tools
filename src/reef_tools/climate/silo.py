"""SILO climate data retrieval — download, subset, and aggregate to shapefile polygons.

Provides the :class:`SILOData` class for downloading SILO NetCDF climate data from the
public S3 bucket, subsetting by geographic region, and computing area-weighted
time series aggregated to shapefile polygons (e.g., sub-catchments).

Also includes :func:`insert_feb29_mean` for converting no-leap calendar time series
to Gregorian by interpolating Feb 29 values.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Sequence


# ---------------------------------------------------------------------------
# Variable metadata
# ---------------------------------------------------------------------------

_SILO_VARIABLES: dict[str, dict[str, str]] = {
    "rain": {
        "s3_prefix": "daily_rain",
        "nc_variable": "daily_rain",
        "label": "Daily rainfall",
    },
    "pet": {
        "s3_prefix": "et_morton_wet",
        "nc_variable": "et_morton_wet",
        "label": "Morton wet areal potential evapotranspiration",
    },
}

_SILO_BUCKET = "silo-open-data"
_SILO_BASE = "Official/annual"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def insert_feb29_mean(df: pd.DataFrame) -> pd.DataFrame:
    """Insert Feb 29 into a daily time series that originally used a no-leap calendar.

    The Feb 29 value for each column is the mean of Feb 28 and Mar 1.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with a ``DatetimeIndex`` representing daily data.

    Returns
    -------
    pandas.DataFrame
        A new DataFrame with Feb 29 inserted for all Gregorian leap years
        where it was missing.

    Raises
    ------
    TypeError
        If the index is not a ``DatetimeIndex``.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("Index must be a pandas DatetimeIndex")

    years = df.index.year.unique()

    # Gregorian leap-year rule
    leap_years = [
        int(y)
        for y in years
        if (y % 4 == 0) and ((y % 100 != 0) or (y % 400 == 0))
    ]

    # Feb 29 timestamps for leap years missing from the index
    missing_feb29 = [
        pd.Timestamp(year=y, month=2, day=29)
        for y in leap_years
        if pd.Timestamp(year=y, month=2, day=29) not in df.index
    ]

    rows_to_add: dict[pd.Timestamp, pd.Series] = {}
    for ts in missing_feb29:
        prev_day = ts - pd.Timedelta(days=1)
        next_day = ts + pd.Timedelta(days=1)

        if prev_day not in df.index or next_day not in df.index:
            raise ValueError(
                f"Missing neighbours for {ts.date()}: "
                f"{prev_day.date()!r} or {next_day.date()!r} not in index"
            )

        rows_to_add[ts] = (df.loc[prev_day] + df.loc[next_day]) / 2  # type: ignore[assignment]

    if not rows_to_add:
        result: pd.DataFrame = df.copy()
        return result

    df_feb29 = pd.DataFrame.from_dict(rows_to_add, orient="index")
    df_feb29.index.name = df.index.name

    df_out: pd.DataFrame = pd.concat([df, df_feb29]).sort_index()  # type: ignore[assignment]
    return df_out


# ---------------------------------------------------------------------------
# S3 helpers (lazy imports to keep s3fs optional)
# ---------------------------------------------------------------------------


def _get_s3_client():
    """Create a persistent s3fs client with caching enabled.

    Returns
    -------
    s3fs.S3FileSystem
    """
    try:
        import s3fs
    except ImportError as exc:
        raise ImportError(
            "s3fs is required for SILO S3 access. Install with: "
            "pip install reef-tools[climate]"
        ) from exc

    return s3fs.S3FileSystem(
        anon=True,
        default_cache_type="readahead",
        default_fill_cache=True,
        use_listings_cache=True,
        listings_expiry_time=300,
        skip_instance_cache=False,
        config_kwargs={
            "max_pool_connections": 50,
            "retries": {"max_attempts": 3},
        },
    )


def _open_s3_dataset(url: str):
    """Open a NetCDF dataset from S3 via xarray with h5netcdf engine.

    Parameters
    ----------
    url : str
        Full S3 URL (e.g., ``s3://silo-open-data/...``).

    Returns
    -------
    xarray.Dataset
    """
    try:
        import xarray as xr
    except ImportError as exc:
        raise ImportError(
            "xarray is required for NetCDF access. Install with: "
            "pip install reef-tools[climate]"
        ) from exc

    return xr.open_dataset(
        url,
        engine="h5netcdf",
        backend_kwargs={"storage_options": {"anon": True}},
    )


# ---------------------------------------------------------------------------
# Grid-cell polygon creation
# ---------------------------------------------------------------------------


def _create_cell_polygons(lon_vals: np.ndarray, lat_vals: np.ndarray) -> list:
    """Create vectorised grid-cell polygons for rectilinear or curvilinear grids.

    Parameters
    ----------
    lon_vals : np.ndarray
        Longitude values, 1D (rectilinear) or 2D (curvilinear).
    lat_vals : np.ndarray
        Latitude values, 1D (rectilinear) or 2D (curvilinear).

    Returns
    -------
    list of shapely.geometry.Polygon
    """
    from shapely.geometry import Polygon, box

    if lon_vals.ndim == 2:
        # Curvilinear — use cell corners directly
        ny, nx = lon_vals.shape
        polygons = []
        for j in range(ny - 1):
            for i in range(nx - 1):
                corners = [
                    (lon_vals[j, i], lat_vals[j, i]),
                    (lon_vals[j, i + 1], lat_vals[j, i + 1]),
                    (lon_vals[j + 1, i + 1], lat_vals[j + 1, i + 1]),
                    (lon_vals[j + 1, i], lat_vals[j + 1, i]),
                ]
                polygons.append(Polygon(corners))
        return polygons

    # Rectilinear — simple boxes from cell centres
    lons = lon_vals
    lats = lat_vals
    dx = abs(lons[1] - lons[0])
    dy = abs(lats[1] - lats[0])
    lon_corners = lons - dx / 2
    lat_corners = lats - dy / 2

    polygons = []
    for lat in lat_corners:
        for lon in lon_corners:
            polygons.append(box(lon, lat, lon + dx, lat + dy))
    return polygons


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class SILOData:
    """Download and process SILO climate data from the public S3 bucket.

    Handles daily rainfall (``rain``) and Morton wet potential
    evapotranspiration (``pet``).  Supports spatial subsetting by lat/lon
    bounding box and area-weighted aggregation to shapefile polygons.

    Parameters
    ----------
    output_dir : str or Path, optional
        Directory where downloaded NetCDF files are stored.
        Defaults to ``"netcdf_files"``.

    Examples
    --------
    >>> silo = SILOData(output_dir="data/netcdf")
    >>> silo.download("rain", years=[2020, 2021], subset_region={
    ...     "lat": (-27.3, -10.3),
    ...     "lon": (141.9, 153.3),
    ... })
    >>> df = silo.aggregate_to_polygons(
    ...     "GBR_Subcats/CY/CY.shp",
    ...     variable="rain",
    ...     years=[2020, 2021],
    ...     attribute_name="SUBCAT",
    ... )
    """

    # SILO variable metadata
    VARIABLES: dict[str, dict[str, str]] = _SILO_VARIABLES

    # Default GBR bounding box
    GBR_REGION: dict[str, tuple[float, float]] = {
        "lat": (-27.3, -10.3),
        "lon": (141.9, 153.3),
    }

    def __init__(self, output_dir: str | Path = "netcdf_files") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._fs = None

    @property
    def fs(self):
        """Lazy-initialised s3fs client (cached)."""
        if self._fs is None:
            self._fs = _get_s3_client()
        return self._fs

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def download(
        self,
        variable: str,
        years: Sequence[int | str],
        subset_region: dict[str, tuple[float, float]] | None = None,
    ) -> list[Path]:
        """Download NetCDF files from the SILO S3 bucket.

        Parameters
        ----------
        variable : str
            Climate variable: ``"rain"`` or ``"pet"``.
        years : sequence of int or str
            Years to download (e.g., ``[2020, 2021, 2022]``).
        subset_region : dict, optional
            Lat/lon bounding box ``{"lat": (min, max), "lon": (min, max)}``.
            When provided, only grid cells inside the box are kept.

        Returns
        -------
        list of Path
            Paths to the downloaded NetCDF files.

        Raises
        ------
        ValueError
            If *variable* is not one of the recognised SILO variables.
        """
        meta = _SILO_VARIABLES.get(variable)
        if meta is None:
            raise ValueError(
                f"Unknown variable {variable!r}. "
                f"Must be one of: {list(_SILO_VARIABLES)}"
            )

        prefix = meta["s3_prefix"]
        downloaded: list[Path] = []

        for year in years:
            year = int(year) if not isinstance(year, int) else year
            s3_url = (
                f"s3://{_SILO_BUCKET}/{_SILO_BASE}/{prefix}/{year}.{prefix}.nc"
            )
            out_path = self.output_dir / f"{variable}_{year}.nc"

            print(f"Retrieving {year} {variable} data")
            print(f"  Loading: {s3_url}")

            ds = _open_s3_dataset(s3_url)
            print(f"  Dataset: {dict(ds.sizes)}")

            if subset_region:
                lat_slice = slice(
                    subset_region["lat"][0], subset_region["lat"][1]
                )
                lon_slice = slice(
                    subset_region["lon"][0], subset_region["lon"][1]
                )
                ds = ds.sel(lat=lat_slice, lon=lon_slice)
                print(f"  Subset: {dict(ds.sizes)}")

            ds = ds.load()

            ds.to_netcdf(
                out_path,
                encoding={
                    var: {"zlib": True, "complevel": 4}
                    for var in ds.data_vars
                },
            )
            print(f"  Saved: {out_path}")
            downloaded.append(out_path)

        return downloaded

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def aggregate_to_polygons(
        self,
        shapefile_path: str | Path,
        variable: str,
        years: Sequence[int | str],
        *,
        variable_name: str | None = None,
        attribute_name: str = "SUBCAT",
        netcdf_dir: str | Path | None = None,
        output_csv: str | Path | None = None,
    ) -> pd.DataFrame:
        """Compute area-weighted time series for each polygon in a shapefile.

        Opens one NetCDF per year, computes the area of intersection between
        each polygon and the grid cells, and returns weighted-average time
        series with polygons as columns and time steps as rows.

        Parameters
        ----------
        shapefile_path : str or Path
            Path to the shapefile (e.g., ``"GBR_Subcats/CY/CY.shp"``).
        variable : str
            Climate variable: ``"rain"`` or ``"pet"``.
        years : sequence of int or str
            Years to process.
        variable_name : str, optional
            NetCDF variable name within the file.  Auto-detected from
            *variable* when omitted (``"daily_rain"`` for rain,
            ``"et_morton_wet"`` for pet).
        attribute_name : str, optional
            Shapefile attribute used to name columns (default ``"SUBCAT"``).
        netcdf_dir : str or Path, optional
            Directory containing the NetCDF files.  Defaults to
            ``self.output_dir``.
        output_csv : str or Path, optional
            If provided, save the combined DataFrame to this CSV path.

        Returns
        -------
        pandas.DataFrame
            Time series (rows = time steps, columns = polygons).
        """
        meta = _SILO_VARIABLES.get(variable)
        if meta is None:
            raise ValueError(
                f"Unknown variable {variable!r}. "
                f"Must be one of: {list(_SILO_VARIABLES)}"
            )

        if variable_name is None:
            variable_name = meta["nc_variable"]

        import xarray as xr

        try:
            import geopandas as gpd
        except ImportError as exc:
            raise ImportError(
                "geopandas is required for area-weighted aggregation. "
                "Install with: pip install reef-tools[climate]"
            ) from exc

        nc_dir = Path(netcdf_dir) if netcdf_dir else self.output_dir
        shapefile_path = Path(shapefile_path)

        # ------------------------------------------------------------------
        # Load shapefile
        # ------------------------------------------------------------------
        gdf = gpd.read_file(shapefile_path)
        projected_crs = "EPSG:3577"
        if gdf.crs != projected_crs:
            gdf = gdf.to_crs(projected_crs)
        gdf["geometry"] = gdf["geometry"].buffer(0)  # repair invalid geoms

        # Resolve polygon names
        polygon_names: list[str] = []
        for idx, row in gdf.iterrows():
            name = f"poly_{idx}"
            if attribute_name and attribute_name in gdf.columns:
                name = str(row[attribute_name])
            elif "name" in gdf.columns or "NAME" in gdf.columns:
                name = str(row.get("name", row.get("NAME", idx)))
            polygon_names.append(name)

        # ------------------------------------------------------------------
        # Process each year
        # ------------------------------------------------------------------
        df_combined = pd.DataFrame()

        for year in years:
            year = int(year) if not isinstance(year, int) else year
            nc_file = nc_dir / f"{variable}_{year}.nc"

            print(f"\nProcessing {year}...")
            print("  Loading dataset...")

            ds = xr.open_dataset(nc_file)
            ds.load()

            # Build grid-cell polygons (cached per-year since grid is fixed)
            print("  Building grid-cell polygons...")
            cell_polys = _create_cell_polygons(
                ds.lon.values, ds.lat.values
            )

            cell_gdf = gpd.GeoDataFrame(
                {"geometry": cell_polys}, crs="EPSG:4326"
            )
            cell_gdf = cell_gdf.to_crs(projected_crs)
            spatial_index = cell_gdf.sindex

            time_index = ds.time.to_pandas()

            results: dict[str, pd.Series] = {
                name: pd.Series(np.nan, index=time_index, name=name)
                for name in polygon_names
            }

            print("  Computing area-weighted aggregation...")
            try:
                from tqdm import tqdm as _tqdm

                polygon_iter = _tqdm(
                    gdf.iterrows(), total=len(gdf), desc=f"  {year}"
                )
            except ImportError:
                polygon_iter = gdf.iterrows()

            for idx, poly in polygon_iter:
                name = polygon_names[idx]

                # Find candidate cells via spatial index
                possible_idx = list(
                    spatial_index.intersection(poly.geometry.bounds)
                )
                if not possible_idx:
                    warnings.warn(f"No overlapping cells for {name}")
                    continue

                overlapping = cell_gdf.iloc[possible_idx]
                intersections = overlapping.intersection(poly.geometry)

                poly_area = poly.geometry.area
                if poly_area <= 0:
                    warnings.warn(f"Zero-area polygon for {name}")
                    continue

                intersection_areas = intersections.area
                weights = intersection_areas / poly_area

                # Filter to cells with non-negligible overlap (> 1 m²)
                mask = intersection_areas > 1
                valid_weights = weights[mask]
                valid_indices = list(np.array(possible_idx)[mask.values])

                if len(valid_weights) == 0:
                    continue

                covered = valid_weights.sum()
                if covered < 0.99:
                    warnings.warn(
                        f"Partial grid coverage for {name}: {covered:.2%}"
                    )

                # Map flat index → 2D array indices
                if ds.lat.ndim == 2:
                    ny, nx = ds.lat.shape
                    j_idx = np.array([i // (nx - 1) for i in valid_indices])
                    i_idx = np.array([i % (nx - 1) for i in valid_indices])
                    data = ds[variable_name].isel(
                        lat=xr.DataArray(j_idx, dims="cell"),
                        lon=xr.DataArray(i_idx, dims="cell"),
                    )
                else:
                    nx = len(ds.lon)
                    j_idx = np.array([i // nx for i in valid_indices])
                    i_idx = np.array([i % nx for i in valid_indices])
                    data = ds[variable_name].isel(
                        lat=xr.DataArray(j_idx, dims="cell"),
                        lon=xr.DataArray(i_idx, dims="cell"),
                    )

                # Weighted average
                weighted = (
                    data * xr.DataArray(valid_weights.values, dims="cell")
                ).sum(dim="cell")
                results[name] = weighted.to_pandas()

            df_year = pd.DataFrame(results)
            df_combined = pd.concat(
                [df_combined, df_year], axis=0, ignore_index=False
            )

        # Clean up index
        df_combined.index = pd.to_datetime(
            df_combined.index.astype(str)
        ).normalize()

        if output_csv:
            out = Path(output_csv)
            out.parent.mkdir(parents=True, exist_ok=True)
            df_combined.to_csv(out)
            print(f"\nSaved: {out}")

        return df_combined

    # ------------------------------------------------------------------
    # High-level convenience
    # ------------------------------------------------------------------

    def extract_timeseries(
        self,
        region: str,
        variable: str,
        start_year: int,
        end_year: int,
        *,
        shapefile_base: str | Path = "GBR_Subcats",
        subset_region: dict[str, tuple[float, float]] | None = None,
        attribute_name: str = "SUBCAT",
        output_dir: str | Path = "extracted_data",
    ) -> pd.DataFrame:
        """Run the full pipeline: download → aggregate → save CSV.

        Parameters
        ----------
        region : str
            Region code used to locate the shapefile
            (e.g., ``"CY"`` → ``GBR_Subcats/CY/CY.shp``).
        variable : str
            Climate variable: ``"rain"`` or ``"pet"``.
        start_year : int
            First year to retrieve (inclusive).
        end_year : int
            Last year to retrieve (inclusive).
        shapefile_base : str or Path, optional
            Base directory for shapefiles (default ``"GBR_Subcats"``).
        subset_region : dict, optional
            Lat/lon bounding box. If *None* and *variable* is ``"rain"`` or
            ``"pet"``, defaults to :attr:`GBR_REGION`.
        attribute_name : str, optional
            Shapefile column for polygon names (default ``"SUBCAT"``).
        output_dir : str or Path, optional
            Directory for the output CSV (default ``"extracted_data"``).

        Returns
        -------
        pandas.DataFrame
            Combined time series for all years.
        """
        years = list(range(start_year, end_year + 1))

        if subset_region is None:
            subset_region = self.GBR_REGION

        # Step 1 — download NetCDF files
        self.download(variable, years, subset_region=subset_region)

        # Step 2 — aggregate to polygons
        shapefile_path = (
            Path(shapefile_base) / region / f"{region}.shp"
        )
        output_csv = (
            Path(output_dir) / f"{region}_{variable}.csv"
        )

        df = self.aggregate_to_polygons(
            shapefile_path,
            variable,
            years,
            attribute_name=attribute_name,
            output_csv=output_csv,
        )

        return df
