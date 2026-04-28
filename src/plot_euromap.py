#!/usr/bin/env python3

import argparse
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl


# -----------------------------
# ISO COUNTRY MAPPING
# -----------------------------
ISO_MAP = {
    'Albania': 'AL',
    'Austria': 'AT',
    'Belgium': 'BE',
    'Bosnia and Herzegovina': 'BA',
    'Bulgaria': 'BG',
    'Croatia': 'HR',
    'Cyprus': 'CY',
    'Czechia': 'CZ',
    'Denmark': 'DK',
    'Estonia': 'EE',
    'Finland': 'FI',
    'France': 'FR',
    'Germany': 'DE',
    'Greece': 'EL',
    'Hungary': 'HU',
    'Iceland': 'IS',
    'Ireland': 'IE',
    'Italy': 'IT',
    'Kosovo': 'XK',
    'Latvia': 'LV',
    'Liechtenstein': 'LI',
    'Lithuania': 'LT',
    'Luxembourg': 'LU',
    'Malta': 'MT',
    'Montenegro': 'ME',
    'Netherlands': 'NL',
    'North Macedonia': 'MK',
    'Norway': 'NO',
    'Poland': 'PL',
    'Portugal': 'PT',
    'Romania': 'RO',
    'Serbia': 'RS',
    'Slovakia': 'SK',
    'Slovenia': 'SI',
    'Spain': 'ES',
    'Sweden': 'SE',
    'Switzerland': 'CH',
    'Türkiye': 'TR',
    'United Kingdom': 'UK'
}


# -----------------------------
# MAIN FUNCTION
# -----------------------------
def main(args):

    print("Generating aggregated country statistics...")

    # -----------------------------
    # LOAD DATA
    # -----------------------------
    annotations = pd.read_csv(args.input_csv)
    panel = pd.read_csv(args.panel)

    if "Year" not in panel.columns:
        raise ValueError("Panel file must contain 'Year' column.")

    if "Family ID" not in annotations.columns:
        raise ValueError("Annotations file must contain 'Family ID'.")

    # -----------------------------
    # MERGE PANEL
    # -----------------------------
    df = annotations.merge(
        panel,
        on="Family ID",
        how="left",
        suffixes=("", "_panel")
    )

    if "Year_panel" in df.columns:
        df["Year"] = df["Year_panel"]

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df[df["Year"].notna()]
    df = df[df["Year"] >= 2000]

    # -----------------------------
    # EXPAND EU FAMILIES
    # -----------------------------
    eu_docs = df[df["Country"] == "European Union"]
    non_eu_docs = df[df["Country"] != "European Union"]

    expanded_rows = []

    for _, row in eu_docs.iterrows():
        for country in ISO_MAP.keys():
            new_row = row.copy()
            new_row["Country"] = country
            expanded_rows.append(new_row)

    df = pd.concat([non_eu_docs, pd.DataFrame(expanded_rows)], ignore_index=True)

    # -----------------------------
    # MAP ISO
    # -----------------------------
    df["CNTR_CODE"] = df["Country"].map(ISO_MAP)
    df = df[df["CNTR_CODE"].notna()]

    # -----------------------------
    # FILTER HEALTH RELEVANT
    # -----------------------------
    df = df[df["Health relevance (1/0)"] == 1]

    # -----------------------------
    # UNIQUE FAMILY PER COUNTRY
    # -----------------------------
    df = df.drop_duplicates(subset=["Family ID", "CNTR_CODE"])

    # -----------------------------
    # AGGREGATE
    # -----------------------------
    aggregated = (
        df.groupby("CNTR_CODE")
        .size()
        .reset_index(name="Health relevance")
    )

    aggregated.to_csv(args.output_csv, index=False)
    print(f"Aggregated CSV saved: {args.output_csv}")

    # -----------------------------
    # LOAD SHAPEFILE
    # -----------------------------
    shapefile_path = (
        "./shapefile/NUTS_RG_01M_2024_4326_with_UK_2021.shp"
        if args.resolution == "low"
        else "./shapefile/NUTS_RG_10M_2024_4326_with_UK_2021.shp"
    )

    gdf = gpd.read_file(shapefile_path)
    gdf = gdf[gdf["LEVL_CODE"] == args.nuts_level]
    gdf = gdf.to_crs("+proj=eck3")

    merged = gdf.merge(aggregated, on="CNTR_CODE", how="left")

    # -----------------------------
    # SPLIT MAP DATA
    # -----------------------------
    data_countries = merged[merged["Health relevance"].notna()]
    surrounding = merged[merged["Health relevance"].isna()]

    # -----------------------------
    # FIXED INTEGER LEGEND SCALE
    # -----------------------------
    values = aggregated["Health relevance"]

    min_val = int(values.min())
    max_val = int(values.max())

    legend_min = max(0, min_val - 2)
    legend_max = max_val + 2

    norm = mpl.colors.Normalize(vmin=legend_min, vmax=legend_max)

    # -----------------------------
    # PLOT
    # -----------------------------
    fig, ax = plt.subplots(figsize=(9, 9))

    ax.set_facecolor("#dceaf6")

    surrounding.plot(
        ax=ax,
        color="#d9d9d9",
        edgecolor="black",
        linewidth=0.4
    )

    data_countries.plot(
        column="Health relevance",
        cmap="OrRd",
        linewidth=0.4,
        edgecolor="black",
        legend=True,
        norm=norm,
        legend_kwds={
            "shrink": 0.5,
            "aspect": 15,
            "pad": 0.02,
            "ticks": list(range(legend_min, legend_max + 1, 2)),
            "format": "%.0f"
        },
        ax=ax
    )

    # -----------------------------
    # FRAME SETTINGS
    # -----------------------------
    xmin, ymin, xmax, ymax = data_countries.total_bounds
    buffer = 1_200_000

    ax.set_xlim(xmin - buffer, xmax + buffer)
    ax.set_ylim(ymin - buffer, ymax + buffer)

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1)

    ax.set_xticks([])
    ax.set_yticks([])

    ax.set_title(
        "Health-Relevant Climate Legislative Families in EEA38+UK\n(2000–2025)",
        fontsize=13
    )

    plt.tight_layout()

    plt.savefig(args.output_png, dpi=300, bbox_inches="tight")
    plt.savefig(args.output_pdf, bbox_inches="tight")
    plt.close()

    print(f"Map saved: {args.output_png}, {args.output_pdf}")
    print("Done.")


# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--input_csv", required=True)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--output_csv", required=True)
    parser.add_argument("--output_png", required=True)
    parser.add_argument("--output_pdf", required=True)
    parser.add_argument("--resolution", choices=["low", "high"], default="low")
    parser.add_argument("--nuts_level", type=int, choices=[0, 1, 2, 3], default=0)

    args = parser.parse_args()
    main(args)