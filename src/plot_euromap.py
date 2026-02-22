import argparse
import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt


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

    print("Generating country-year statistics and aggregated totals...")

    # -----------------------------
    # LOAD DATA
    # -----------------------------
    annotations = pd.read_csv(args.input_csv)
    panel = pd.read_csv(args.panel_csv)

    # Ensure ID and Year columns
    if "Doc ID" in annotations.columns:
        annotations = annotations.rename(columns={"Doc ID": "Document ID"})
    if "year" in panel.columns:
        panel = panel.rename(columns={"year": "Year"})
    elif "Year" not in panel.columns:
        raise ValueError("Panel file must contain 'Year' or 'year' column.")

    df = annotations.merge(panel, on="Document ID", how="left")

    # -----------------------------
    # EXPAND EU DOCUMENTS
    # -----------------------------
    eu_docs = df[df["Country"] == "European Union"].copy()
    non_eu_docs = df[df["Country"] != "European Union"].copy()

    expanded_rows = []
    for _, row in eu_docs.iterrows():
        for country in ISO_MAP.keys():
            new_row = row.copy()
            new_row["Country"] = country
            expanded_rows.append(new_row)

    expanded_df = pd.DataFrame(expanded_rows)
    df = pd.concat([non_eu_docs, expanded_df], ignore_index=True)

    # -----------------------------
    # ADD ISO CODE
    # -----------------------------
    df["CNTR_CODE"] = df["Country"].map(ISO_MAP)

    # Drop anything not in mapping
    df = df[df["CNTR_CODE"].notna()]

    # -----------------------------
    # AGGREGATION (COUNTRY LEVEL)
    # -----------------------------
    aggregated = (
        df.groupby(["Country", "CNTR_CODE"])
        .agg({
            "Health relevance (1/0)": "sum",
            "Health adaptation mandate (1/0)": "sum",
            "Institutional health role (1/0)": "sum"
        })
        .reset_index()
    )

    # Rename for clarity
    aggregated = aggregated.rename(columns={
        "Health relevance (1/0)": "Health relevance",
        "Health adaptation mandate (1/0)": "Health adaptation mandate",
        "Institutional health role (1/0)": "Institutional health role"
    })

    # Save aggregated CSV
    aggregated_csv_path = args.output_csv.replace(".csv", "_aggregated.csv")
    aggregated.to_csv(aggregated_csv_path, index=False)
    print(f"Aggregated country-level CSV saved as: {aggregated_csv_path}")

    # -----------------------------
    # LOAD SHAPEFILE
    # -----------------------------
    print("Creating map (World Eckert III projection)...")

    shapefile_path = (
        "./shapefile/NUTS_RG_01M_2024_4326_with_UK_2021.shp"
        if args.resolution == "low"
        else "./shapefile/NUTS_RG_10M_2024_4326_with_UK_2021.shp"
    )

    gdf = gpd.read_file(shapefile_path)

    # Filter to requested NUTS level
    gdf = gdf[gdf["LEVL_CODE"] == args.nuts_level].copy()

    # Filter to EEA38+UK only
    gdf = gdf[gdf["CNTR_CODE"].isin(EEA_ISO_CODES)]

    # -----------------------------
    # MERGE USING ISO CODE
    # -----------------------------
    merged = gdf.merge(
        aggregated,
        on="CNTR_CODE",
        how="left"
    )

    # -----------------------------
    # PLOT MAP (Health relevance)
    # -----------------------------
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))

    merged.plot(
        column="Health relevance",
        cmap="OrRd",
        linewidth=0.5,
        edgecolor="black",
        legend=True,
        missing_kwds={
            "color": "lightgrey",
            "edgecolor": "black",
            "label": "No data"
        },
        ax=ax
    )

    ax.set_title("Health-Relevant Climate Policy Documents\n(EEA38 + UK)",
                 fontsize=14)
    ax.axis("off")

    plt.tight_layout()
    plt.savefig(args.output_png, dpi=300)
    plt.savefig(args.output_pdf)
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