"""Tahbil data summary reporting — site coverage, gaps, and data quality."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from reef_tools.water_quality.tahbil import TahbilData


def generate_report(td: "TahbilData", **filter_kwargs) -> dict[str, pd.DataFrame]:
    """Generate a structured data quality report.

    Parameters
    ----------
    td : TahbilData
        A loaded TahbilData instance.
    **filter_kwargs
        Passed to ``td.load()`` for filtering before reporting.

    Returns
    -------
    dict of DataFrames
        Keys: "overview", "site_coverage", "analyte_matrix",
        "missing_periods", "region_summary".
    """
    df = td.load(**filter_kwargs)

    report = {
        "overview": _overview(df),
        "site_coverage": _site_coverage(df),
        "analyte_matrix": _analyte_matrix(df),
        "missing_periods": _missing_periods(df),
        "region_summary": _region_summary(df),
    }
    return report


def format_report(
    report: dict[str, pd.DataFrame],
    format: str = "markdown",
) -> str:
    """Format a report dict as a readable string.

    Parameters
    ----------
    report : dict
        Output from :func:`generate_report`.
    format : str
        Output format. Currently supports "markdown" and "text".

    Returns
    -------
    str
        Formatted report.
    """
    buf = StringIO()

    if format == "markdown":
        _write_markdown(report, buf)
    else:
        _write_text(report, buf)

    return buf.getvalue()


def save_report(
    report: dict[str, pd.DataFrame],
    path: str | Path,
    format: str | None = None,
) -> None:
    """Save a formatted report to file.

    Parameters
    ----------
    report : dict
        Output from :func:`generate_report`.
    path : str or Path
        Output file path. Format is inferred from extension if not specified.
    format : str, optional
        "markdown", "text", or "excel". Inferred from extension if None.
    """
    path = Path(path)

    if format is None:
        ext_map = {".md": "markdown", ".txt": "text", ".xlsx": "excel"}
        format = ext_map.get(path.suffix.lower(), "markdown")

    if format == "excel":
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for sheet_name, df in report.items():
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    else:
        text = format_report(report, format=format)
        path.write_text(text, encoding="utf-8")


# ------------------------------------------------------------------
# Report section builders
# ------------------------------------------------------------------


def _overview(df: pd.DataFrame) -> pd.DataFrame:
    """Single-row overview summary."""
    data = {
        "Total Records": len(df),
        "Sites": df["Site Code"].nunique(),
        "Regions": df["Region"].nunique(),
        "Basins": df["Basin"].nunique(),
        "Catchments": df["Catchment"].nunique(),
        "Analytes": df["Analyte"].nunique(),
        "Date Min": df["Date"].min().strftime("%Y-%m-%d"),
        "Date Max": df["Date"].max().strftime("%Y-%m-%d"),
        "Sampling Years": df["Sampling Year"].nunique(),
    }
    return pd.DataFrame([data])


def _site_coverage(df: pd.DataFrame) -> pd.DataFrame:
    """Per-site coverage summary with gap detection."""
    all_sampling_years = sorted(df["Sampling Year"].unique())

    site_groups = df.groupby(
        ["Region", "Basin", "Catchment", "Site Code", "Site Name"],
        observed=True,
    )

    rows = []
    for (region, basin, catchment, site_code, site_name), grp in site_groups:
        date_min = grp["Date"].min()
        date_max = grp["Date"].max()
        unique_dates = grp["Date"].dt.date.nunique()
        expected_days = (date_max - date_min).days + 1
        coverage_pct = unique_dates / expected_days * 100 if expected_days > 0 else 0

        # Which sampling years does this site have?
        site_years = set(grp["Sampling Year"].unique())
        missing_years = sorted(set(all_sampling_years) - site_years)

        rows.append({
            "Region": region,
            "Basin": basin,
            "Catchment": catchment,
            "Site Code": site_code,
            "Site Name": site_name,
            "Date Min": date_min.strftime("%Y-%m-%d"),
            "Date Max": date_max.strftime("%Y-%m-%d"),
            "Active Days": unique_dates,
            "Expected Days": expected_days,
            "Coverage (%)": round(coverage_pct, 1),
            "Sampling Years": ", ".join(site_years),
            "Missing Years": ", ".join(missing_years) if missing_years else "",
            "Has Gaps": coverage_pct < 100,
        })

    result = pd.DataFrame(rows)
    return result.sort_values(["Region", "Basin", "Site Code"]).reset_index(drop=True)


def _analyte_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Site × Analyte availability matrix (record counts)."""
    matrix = df.pivot_table(
        index=["Region", "Site Code", "Site Name"],
        columns="Analyte",
        values="Load (t)",
        aggfunc="count",
        fill_value=0,
        observed=True,
    ).reset_index()
    matrix.columns.name = None
    return matrix


def _missing_periods(df: pd.DataFrame) -> pd.DataFrame:
    """Identify specific date gaps within each site's active period.

    Returns a DataFrame with one row per gap (start, end, duration).
    """
    all_rows = []

    for site_code, grp in df.groupby("Site Code", observed=True):
        site_name = grp["Site Name"].iloc[0]
        region = grp["Region"].iloc[0]

        # Get unique dates for this site
        dates = sorted(grp["Date"].dt.date.unique())
        if len(dates) < 2:
            continue

        # Find gaps > 1 day
        for i in range(1, len(dates)):
            gap_days = (dates[i] - dates[i - 1]).days
            if gap_days > 1:
                all_rows.append({
                    "Region": region,
                    "Site Code": site_code,
                    "Site Name": site_name,
                    "Gap Start": dates[i - 1] + pd.Timedelta(days=1),
                    "Gap End": dates[i] - pd.Timedelta(days=1),
                    "Gap Days": gap_days - 1,
                })

    if not all_rows:
        return pd.DataFrame(columns=[
            "Region", "Site Code", "Site Name", "Gap Start", "Gap End", "Gap Days"
        ])

    result = pd.DataFrame(all_rows)
    return result.sort_values(["Region", "Site Code", "Gap Start"]).reset_index(drop=True)


def _region_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-region summary statistics."""
    regions = df.groupby("Region", observed=True).agg(
        Sites=("Site Code", "nunique"),
        Basins=("Basin", "nunique"),
        Catchments=("Catchment", "nunique"),
        Records=("Load (t)", "count"),
        Date_Min=("Date", "min"),
        Date_Max=("Date", "max"),
        Analytes=("Analyte", "nunique"),
    ).reset_index()

    regions["Date_Min"] = regions["Date_Min"].dt.strftime("%Y-%m-%d")
    regions["Date_Max"] = regions["Date_Max"].dt.strftime("%Y-%m-%d")

    return regions


# ------------------------------------------------------------------
# Formatters
# ------------------------------------------------------------------


def _write_markdown(report: dict[str, pd.DataFrame], buf: StringIO) -> None:
    """Write report as markdown."""
    buf.write("# Tahbil Data Summary Report\n\n")

    # Overview
    buf.write("## Overview\n\n")
    ov = report["overview"].iloc[0]
    buf.write(f"| Metric | Value |\n|--------|-------|\n")
    for col, val in ov.items():
        buf.write(f"| {col} | {val:,} |\n" if isinstance(val, int) else f"| {col} | {val} |\n")
    buf.write("\n")

    # Region summary
    buf.write("## Region Summary\n\n")
    buf.write(report["region_summary"].to_markdown(index=False))
    buf.write("\n\n")

    # Site coverage
    buf.write("## Site Coverage\n\n")
    coverage = report["site_coverage"]
    display_cols = [
        "Region", "Basin", "Site Code", "Site Name",
        "Date Min", "Date Max", "Active Days", "Coverage (%)", "Missing Years",
    ]
    buf.write(coverage[display_cols].to_markdown(index=False))
    buf.write("\n\n")

    # Missing periods (gaps)
    gaps = report["missing_periods"]
    if len(gaps) > 0:
        buf.write("## Missing Date Ranges (Internal Gaps)\n\n")
        buf.write(f"**{len(gaps)} gap(s) found across {gaps['Site Code'].nunique()} site(s)**\n\n")
        buf.write(gaps.to_markdown(index=False))
        buf.write("\n\n")
    else:
        buf.write("## Missing Date Ranges (Internal Gaps)\n\n")
        buf.write("No internal gaps detected — all sites have continuous daily records.\n\n")

    # Analyte matrix
    buf.write("## Analyte Availability (record counts per site)\n\n")
    matrix = report["analyte_matrix"]
    buf.write(matrix.to_markdown(index=False))
    buf.write("\n")


def _write_text(report: dict[str, pd.DataFrame], buf: StringIO) -> None:
    """Write report as plain text."""
    buf.write("=" * 60 + "\n")
    buf.write("TAHBIL DATA SUMMARY REPORT\n")
    buf.write("=" * 60 + "\n\n")

    # Overview
    buf.write("OVERVIEW\n")
    buf.write("-" * 40 + "\n")
    ov = report["overview"].iloc[0]
    for col, val in ov.items():
        buf.write(f"  {col:20s}: {val:,}\n" if isinstance(val, int) else f"  {col:20s}: {val}\n")
    buf.write("\n")

    # Region summary
    buf.write("REGION SUMMARY\n")
    buf.write("-" * 40 + "\n")
    buf.write(report["region_summary"].to_string(index=False))
    buf.write("\n\n")

    # Site coverage
    buf.write("SITE COVERAGE\n")
    buf.write("-" * 40 + "\n")
    coverage = report["site_coverage"]
    display_cols = [
        "Region", "Site Code", "Date Min", "Date Max",
        "Active Days", "Coverage (%)", "Missing Years",
    ]
    buf.write(coverage[display_cols].to_string(index=False))
    buf.write("\n\n")

    # Missing periods
    gaps = report["missing_periods"]
    buf.write("MISSING DATE RANGES (INTERNAL GAPS)\n")
    buf.write("-" * 40 + "\n")
    if len(gaps) > 0:
        buf.write(f"{len(gaps)} gap(s) across {gaps['Site Code'].nunique()} site(s)\n\n")
        buf.write(gaps.to_string(index=False))
    else:
        buf.write("No internal gaps detected.\n")
    buf.write("\n")
