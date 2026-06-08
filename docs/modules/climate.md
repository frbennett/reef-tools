# Climate Module

Climate data retrieval and processing utilities.

## SILO Data Retrieval

The `SILOData` class downloads SILO climate data from the public S3 bucket
and computes area-weighted time series aggregated to shapefile polygons
(e.g., sub-catchments).

### Quick Start

```python
from reef_tools.climate import SILOData

silo = SILOData(output_dir="data/netcdf")

# Download and process in one call
df = silo.extract_timeseries(
    region="CY",
    variable="rain",
    start_year=2017,
    end_year=2025,
)
# → saves extracted_data/CY_rain.csv
```

### Two-Step Workflow

```python
# Step 1 — download NetCDF, subset to a region
silo.download("rain", years=[2020, 2021], subset_region={
    "lat": (-27.3, -10.3),
    "lon": (141.9, 153.3),
})

# Step 2 — aggregate to shapefile polygons
df = silo.aggregate_to_polygons(
    "GBR_Subcats/CY/CY.shp",
    variable="rain",
    years=[2020, 2021],
    attribute_name="SUBCAT",
    output_csv="CY_rain.csv",
)
```

### Supported Variables

| Variable | S3 path                         | NetCDF variable   |
|----------|---------------------------------|-------------------|
| `rain`   | `daily_rain/{year}.daily_rain.nc` | `daily_rain`    |
| `pet`    | `et_morton_wet/{year}.et_morton_wet.nc` | `et_morton_wet` |

### Installation

The climate extras require additional geospatial dependencies:

```bash
pip install reef-tools[climate]
```

### Calendar Conversion

The `insert_feb29_mean` utility converts no-leap (365-day) calendar time series
to Gregorian by interpolating Feb 29 as the mean of Feb 28 and Mar 1.

```python
from reef_tools.climate import insert_feb29_mean

df_gregorian = insert_feb29_mean(df_no_leap)
```

## Climate Model Utilities

*Coming soon — CMIP6 model registry helpers, downscaling variant labels.*
