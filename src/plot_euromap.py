import argparse
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np


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

EEA_ISO_CODES = list(ISO_MAP.values())


# -----------------------------
# MAIN FUNCTION
# -----------------------------
def main(args):

    print("Generating aggregated country statistics...")

    # -----------------------------
    # LOAD DATA
    # -----------------------------
    annotations = pd.read_csv(args.input_csv)
    panel = pd.read_csv(args.panel_csv)

    if "Doc ID" in annotations.columns:
        annotations = annotations.rename(columns={"Doc ID": "Document ID"})

    if "year" in panel.columns:
        panel = panel.rename(columns={"year": "Year"})
    elif "Year" not in panel.columns:
        raise ValueError("Panel file must contain 'Year' column.")

    df = annotations.merge(panel, on="Document ID", how="left")

    # -----------------------------
    # EXPAND EU DOCUMENTS
    # -----------------------------
    eu_docs = df[df["Country"] == "European Union"]
    non_eu_docs = df[df["Country"] != "European Union"]

    expanded_rows = []

    for _, row in eu_docs.iterrows():
        for country in ISO_MAP.keys():
            new_row = row.copy()
            new_row["Country"] = country
            expanded_rows.append(new_row)

    expanded_df = pd.DataFrame(expanded_rows)
    df = pd.concat([non_eu_docs, expanded_df], ignore_index=True)

    # -----------------------------
    # MAP ISO
    # -----------------------------
    df["CNTR_CODE"] = df["Country"].map(ISO_MAP)
    df = df[df["CNTR_CODE"].notna()]

    # -----------------------------
    # AGGREGATE
    # -----------------------------
    aggregated = (
        df.groupby(["CNTR_CODE", "Country"])
        .agg({
            "Health relevance (1/0)": "sum",
            "Health adaptation mandate (1/0)": "sum",
            "Institutional health role (1/0)": "sum"
        })
        .reset_index()
    )

    aggregated = aggregated.rename(columns={
        "Health relevance (1/0)": "Health relevance",
        "Health adaptation mandate (1/0)": "Health adaptation mandate",
        "Institutional health role (1/0)": "Institutional health role"
    })

    aggregated.to_csv(args.output_csv, index=False)
    print(f"Aggregated CSV saved as: {args.output_csv}")

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
    #gdf = gdf[gdf["CNTR_CODE"].isin(EEA_ISO_CODES)]

    # Project to Eckert III
    gdf = gdf.to_crs("+proj=eck3")

    #merged = gdf.merge(aggregated, on="CNTR_CODE", how="left")
    merged = gdf.merge(
        aggregated[["CNTR_CODE", "Health relevance"]],
        on="CNTR_CODE",
        how="left"
    )

    # -----------------------------
    # PLOT
    # -----------------------------
    fig, ax = plt.subplots(figsize=(10, 9))

    # Light blue background (water)
    ax.set_facecolor("#dceaf6")

    # Plot countries
    merged.plot(
        column="Health relevance",
        cmap="OrRd",
        linewidth=0.5,
        edgecolor="black",
        legend=True,
        legend_kwds={
            "shrink": 0.5,
            "aspect": 20,
            "pad": 0.02
        },
        missing_kwds={
            "color": "#d9d9d9",
            "edgecolor": "black",
            "label": "No data"
        },
        ax=ax
    )

    # -----------------------------
    # ADD LAT/LON GRIDLINES
    # -----------------------------
    '''xmin, ymin, xmax, ymax = merged.total_bounds

    # Create evenly spaced gridlines
    x_ticks = np.linspace(xmin, xmax, 8)
    y_ticks = np.linspace(ymin, ymax, 8)

    for x in x_ticks:
        ax.axvline(x=x, color="gray", linestyle="--", linewidth=0.3, alpha=0.5)

    for y in y_ticks:
        ax.axhline(y=y, color="gray", linestyle="--", linewidth=0.3, alpha=0.5)
    '''
    # -----------------------------
    # FRAME
    # -----------------------------
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1)
        spine.set_edgecolor("black")

    ax.set_xticks([])
    ax.set_yticks([])

    ax.set_title(
        "Health-Relevant Climate Policy Documents\n(EEA38 + UK)",
        fontsize=13
    )

    plt.tight_layout()
    plt.savefig(args.output_png, dpi=300, bbox_inches="tight")
    plt.savefig(args.output_pdf, bbox_inches="tight")
    plt.close()

    print(f"Map saved as {args.output_png} and {args.output_pdf}")
    print("Done.")


# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--input_csv", required=True)
    parser.add_argument("--panel_csv", required=True)
    parser.add_argument("--output_csv", required=True)
    parser.add_argument("--output_png", required=True)
    parser.add_argument("--output_pdf", required=True)
    parser.add_argument("--resolution", choices=["low", "high"], default="low")
    parser.add_argument("--nuts_level", type=int, choices=[0, 1, 2, 3], default=0)

    args = parser.parse_args()

    main(args)