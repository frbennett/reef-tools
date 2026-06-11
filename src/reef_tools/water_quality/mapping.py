"""Interactive site mapping for Tahbil water quality data."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    import folium

    from reef_tools.water_quality.tahbil import TahbilData

# Region colour palette
REGION_COLOURS = {
    "Cape York": "darkgreen",
    "Wet Tropics": "green",
    "Burdekin": "orange",
    "Mackay Whitsunday": "blue",
    "Fitzroy": "purple",
    "Burnett Mary": "red",
}


def site_map(
    td: TahbilData,
    *,
    regions: str | Sequence[str] | None = None,
    basemap: str = "OpenStreetMap",
    width: str | int = "100%",
    height: str | int = 600,
    zoom_start: int | None = None,
) -> folium.Map:
    """Create an interactive map of monitoring sites.

    Parameters
    ----------
    td : TahbilData
        A loaded TahbilData instance.
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
    import folium

    # Get site data, optionally filtered
    if regions is not None:
        sites_df = td.sites()
        from reef_tools.water_quality.tahbil import REGION_MAP, _ensure_list

        regions_list = _ensure_list(regions)
        expanded = []
        for r in regions_list:
            if r.upper() in REGION_MAP:
                expanded.append(REGION_MAP[r.upper()])
            else:
                expanded.append(r)
        sites_df = sites_df[sites_df["Region"].isin(expanded)]
    else:
        sites_df = td.sites()

    if sites_df.empty:
        raise ValueError("No sites found for the specified filters.")

    # Calculate map centre and zoom
    lat_centre = sites_df["Latitude"].mean()
    lon_centre = sites_df["Longitude"].mean()

    if zoom_start is None:
        lat_range = sites_df["Latitude"].max() - sites_df["Latitude"].min()
        lon_range = sites_df["Longitude"].max() - sites_df["Longitude"].min()
        extent = max(lat_range, lon_range)
        if extent > 10:
            zoom_start = 5
        elif extent > 5:
            zoom_start = 6
        elif extent > 2:
            zoom_start = 7
        elif extent > 1:
            zoom_start = 8
        else:
            zoom_start = 9

    # Create map
    m = folium.Map(
        location=[lat_centre, lon_centre],
        zoom_start=zoom_start,
        width=width,
        height=height,
        tiles=None,
    )

    # Add base map layers
    _add_tile_layers(m, basemap)

    # Add site markers
    _add_site_markers(m, sites_df)

    # Add legend
    _add_legend(m, sites_df)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    return m


def _add_tile_layers(m: folium.Map, default: str) -> None:
    """Add multiple base map tile layers."""
    import folium

    tiles = {
        "OpenStreetMap": {
            "tiles": "OpenStreetMap",
            "name": "OpenStreetMap",
        },
        "Satellite": {
            "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "attr": "Esri",
            "name": "Satellite",
        },
        "Terrain": {
            "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
            "attr": "Esri",
            "name": "Terrain",
        },
        "CartoDB positron": {
            "tiles": "CartoDB positron",
            "name": "CartoDB Light",
        },
        "CartoDB dark_matter": {
            "tiles": "CartoDB dark_matter",
            "name": "CartoDB Dark",
        },
    }

    for name, kwargs in tiles.items():
        show = name == default
        folium.TileLayer(show=show, **kwargs).add_to(m)


def _add_site_markers(m: folium.Map, sites_df: pd.DataFrame) -> None:
    """Add coloured markers for each site with info popups."""
    import folium

    for _, row in sites_df.iterrows():
        region = row["Region"]
        colour = REGION_COLOURS.get(region, "gray")

        # Build popup HTML
        popup_html = (
            f"<b>{row['Site Name']}</b><br>"
            f"<b>Code:</b> {row['Site Code']}<br>"
            f"<b>Region:</b> {region}<br>"
            f"<b>Basin:</b> {row['Basin']}<br>"
            f"<b>Catchment:</b> {row['Catchment']}<br>"
            f"<b>Records:</b> {row['n_records']:,}<br>"
            f"<b>Period:</b> {row['date_min'].strftime('%Y-%m-%d')} to "
            f"{row['date_max'].strftime('%Y-%m-%d')}"
        )

        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=8,
            color=colour,
            fill=True,
            fill_color=colour,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['Site Code']} — {row['Site Name']}",
        ).add_to(m)


def _add_legend(m: folium.Map, sites_df: pd.DataFrame) -> None:
    """Add a colour legend for regions."""
    import folium

    regions_present = sorted(sites_df["Region"].unique())

    legend_html = """
    <div style="
        position: fixed;
        bottom: 30px;
        left: 30px;
        z-index: 1000;
        background-color: white;
        padding: 10px 14px;
        border-radius: 5px;
        border: 2px solid grey;
        font-size: 13px;
        font-family: Arial, sans-serif;
    ">
    <b>GBR NRM Regions</b><br>
    """
    for region in regions_present:
        colour = REGION_COLOURS.get(region, "gray")
        legend_html += (
            f'<i style="background:{colour}; width:12px; height:12px; '
            f'display:inline-block; border-radius:50%; margin-right:6px;"></i>'
            f"{region}<br>"
        )
    legend_html += "</div>"

    m.get_root().html.add_child(folium.Element(legend_html))
