"""CSV I/O helpers — smart CSV reading with metadata extraction."""

from pathlib import Path
from typing import Any, cast

import pandas as pd


def read_csv_smart(
    path: str | Path,
    *,
    parse_dates: bool = True,
    metadata_split: str | None = "_",
    **kwargs: Any,
) -> pd.DataFrame:
    """Read a CSV file with automatic datetime parsing and metadata extraction.

    Args:
        path: Path to the CSV file.
        parse_dates: If True, attempt to parse the first column as dates.
        metadata_split: Separator used in filename metadata convention.
            Pass None to skip metadata extraction.
            Default is ``"_"`` (e.g., ``ACCESS-CM2_CCAM10_Tully.csv``).
        **kwargs: Additional arguments passed to ``pd.read_csv``.

    Returns:
        DataFrame with the CSV data. Metadata columns are added as the
        first columns if metadata_split is provided.

    Raises:
        FileNotFoundError: If the file does not exist.

    Example:
        >>> df = read_csv_smart("ACCESS-CM2_CCAM10_Tully.csv")
        >>> df.columns[:3]
        Index(['Model', 'Downscaling', 'Region'], dtype='object')
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    df = cast(pd.DataFrame, pd.read_csv(path, **kwargs))

    # Auto-detect date column in the first column
    if parse_dates and len(df.columns) > 0:
        first_col = df.columns[0]
        try:
            parsed = pd.to_datetime(df[first_col], errors="coerce")
            if parsed.notna().sum() > 0.5 * len(df):  # >50% parse success
                df[first_col] = parsed
        except (ValueError, TypeError):
            pass

    # Extract metadata from filename
    if metadata_split is not None:
        stem = path.stem  # filename without extension
        parts = stem.split(metadata_split)
        if len(parts) >= 2:
            # Try to separate: Model_Downscaling_Region (3 parts)
            if len(parts) == 3:
                df.insert(0, "Model", parts[0])
                df.insert(1, "Downscaling", parts[1])
                df.insert(2, "Region", parts[2])
            elif len(parts) == 2:
                df.insert(0, "Category", parts[0])
                df.insert(1, "Subcategory", parts[1])

    return df
