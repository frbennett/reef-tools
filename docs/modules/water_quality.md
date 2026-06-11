# Water Quality Module

Tools for loading, processing, and reporting on water quality monitoring data
from the Queensland DES [Tahbil Water Data Portal](https://apps.des.qld.gov.au/water-data-portal/map).

## Tahbil Data Loader

The `TahbilData` class handles the full workflow for Tahbil portal CSV downloads:
loading, caching, filtering, aggregation, and reporting.

!!! info "No API available"
    The Tahbil portal does not expose a programmatic API. Data must be downloaded
    manually as CSV files (one per GBR NRM region). This module works with those
    downloads regardless of how they were filtered on the portal.

### Quick Start

```python
from reef_tools.water_quality import TahbilData

# Point at a directory containing Tahbil CSV downloads
td = TahbilData("path/to/tahbil_csvs/")

# Load all data (builds a Parquet cache on first call)
df = td.load()

# Filter by region, analyte, date range, site...
df = td.load(
    regions="BU",
    analytes="Dissolved inorganic nitrogen",
    date_from="2020-07-01",
    date_to="2021-06-30",
)
```

### Data Directory Layout

Place your downloaded CSVs in a single directory. The loader auto-detects
Tahbil-format files by checking column headers:

```
tahbil_data/
├── CY.csv          ← Cape York
├── BM.csv          ← Burnett Mary
├── BU.csv          ← Burdekin
├── FI.csv          ← Fitzroy
├── MW.csv          ← Mackay Whitsunday
├── WT.csv          ← Wet Tropics
└── _cache/         ← auto-generated Parquet cache
    └── tahbil_loads.parquet
```

File names don't matter — the loader validates column structure, so filtered
downloads with custom names work fine.

### Parquet Cache

On first load, raw CSVs are consolidated into a single Parquet file:

- **385 MB CSV → ~12 MB Parquet** (30× compression)
- First load: ~30 seconds | Subsequent loads: **< 1 second**
- Auto-rebuilds when any CSV is newer than the cache
- Force rebuild: `td.load(rebuild=True)` or `td.rebuild_cache()`
- Disable caching: `TahbilData("data/", cache_dir=None)`

### Filtering

All filter parameters accept a single string or a list of strings:

```python
# By region (codes or full names both work)
df = td.load(regions="BU")
df = td.load(regions=["Burdekin", "Wet Tropics"])

# By basin, catchment, or site
df = td.load(basins="Normanby")
df = td.load(catchments="Lower Burnett River")
df = td.load(sites="120001A")
df = td.load(sites="Burdekin River at Home Hill Inkerman Bridge")

# By analyte
df = td.load(analytes="Total suspended solids")
df = td.load(analytes=["Dissolved inorganic nitrogen", "Total nitrogen as N"])

# By date range
df = td.load(date_from="2021-01-01", date_to="2021-06-30")

# Combine any filters
df = td.load(regions="WT", analytes="Total suspended solids", date_from="2022-07-01")
```

### Region Codes

| Code | Region |
|------|--------|
| `CY` | Cape York |
| `BM` | Burnett Mary |
| `BU` | Burdekin |
| `FI` | Fitzroy |
| `MW` | Mackay Whitsunday |
| `WT` | Wet Tropics |

### Aggregation

```python
# Monthly loads (tonnes per month)
monthly = td.monthly_loads(by="Site Code", sites="120001A", analytes="Total suspended solids")

# Annual loads (tonnes per water year)
annual = td.annual_loads(by="Region", regions=["BU", "WT"])

# Pivot to wide format (one column per analyte)
wide = td.pivot_analytes(sites="120001A")
```

The `by` parameter controls grouping — use `"Site Code"`, `"Catchment"`,
`"Basin"`, or `"Region"` depending on the level of aggregation needed.

### Data Discovery

```python
# List available regions, analytes
td.regions()     # → ['Burdekin', 'Burnett Mary', 'Cape York', ...]
td.analytes()    # → ['Ammonium nitrogen as N', 'Dissolved inorganic nitrogen', ...]

# Site summary table (coordinates, date ranges, record counts)
td.sites()

# Check which analytes are available at specific sites
td.analytes_by_site(sites=["1200125", "120001A"])
# → Boolean matrix: True where an analyte is monitored at that site
```

!!! tip "Check availability before querying"
    Not all sites monitor all analytes. Use `analytes_by_site()` to verify
    data exists before running aggregations. For example, some smaller
    tributaries only report Total N, TKP, and TSS.

### Reporting

Generate a data quality summary covering sites, coverage, gaps, and analyte
availability:

```python
# Print markdown report
print(td.report())

# Plain text format
print(td.report(format="text"))

# Save to file (.md, .txt, or .xlsx)
td.report(save_to="tahbil_report.md")
td.report(save_to="tahbil_report.xlsx")

# Scoped report (e.g., just one region)
print(td.report(regions="BU"))

# Raw DataFrames for custom analysis
data = td.report(format=None)
data["overview"]          # single-row summary stats
data["region_summary"]    # per-region totals
data["site_coverage"]     # per-site dates, coverage %, missing years
data["missing_periods"]   # internal date gaps (start, end, duration)
data["analyte_matrix"]    # site × analyte record counts
```

#### Report Sections

| Section | Content |
|---------|---------|
| **Overview** | Total records, sites, regions, date range, sampling years |
| **Region Summary** | Sites, basins, catchments per region with date coverage |
| **Site Coverage** | Active period, coverage %, missing sampling years per site |
| **Missing Periods** | Internal gaps where monitoring stopped mid-record |
| **Analyte Matrix** | Record counts per site × analyte combination |

### Available Analytes

The Tahbil portal provides daily loads (tonnes) for these water quality parameters:

| Analyte | Category |
|---------|----------|
| Ammonium nitrogen as N | Nitrogen |
| Oxidised nitrogen as N | Nitrogen |
| Dissolved inorganic nitrogen | Nitrogen (composite) |
| Dissolved organic nitrogen as N | Nitrogen |
| Particulate nitrogen as N | Nitrogen |
| Total nitrogen as N | Nitrogen (total) |
| Filterable Reactive phosphorus as P | Phosphorus |
| Dissolved organic phosphorus as P | Phosphorus |
| Particulate phosphorus as P | Phosphorus |
| Total Kjeldahl phosphorus as P | Phosphorus |
| Total suspended solids | Sediment |

## API Reference

::: reef_tools.water_quality.tahbil.TahbilData
    options:
      show_source: false
      members_order: source
      heading_level: 3

::: reef_tools.water_quality.reporting
    options:
      show_source: false
      members:
        - generate_report
        - format_report
        - save_report
      heading_level: 3
