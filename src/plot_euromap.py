import argparse
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

    if "Doc ID" in annotations.columns:
        annotations = annotations.rename(columns={"Doc ID": "Document ID"})

    if "year" in panel.columns:
        panel = panel.rename(columns={"year": "Year"})

    if "Year" not in panel.columns:
        raise ValueError("Panel file must contain 'Year' column.")

    # -----------------------------
    # MERGE PANEL YEAR SAFELY
    # -----------------------------
    df = annotations.merge(
        panel,
        on="Document ID",
        how="left",
        suffixes=("", "_panel")
    )

    # Identify correct Year column
    if "Year_panel" in df.columns:
        df["Year"] = df["Year_panel"]
    elif "Year" not in df.columns:
        raise ValueError("No 'Year' column found after merging panel data.")

    # Ensure numeric
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")

    # Drop rows without year
    df = df[df["Year"].notna()]

    # Keep documents from 2000 onwards
    df = df[df["Year"] >= 2000]

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
    # MAP ISO CODES
    # -----------------------------
    df["CNTR_CODE"] = df["Country"].map(ISO_MAP)
    df = df[df["CNTR_CODE"].notna()]

    # -----------------------------
    # KEEP ONLY HEALTH RELEVANT DOCS
    # -----------------------------
    df = df[df["Health relevance (1/0)"] == 1]

    # -----------------------------
    # COUNT EACH DOCUMENT ONCE PER COUNTRY
    # -----------------------------
    df = df.drop_duplicates(subset=["Document ID", "CNTR_CODE"])

    # -----------------------------
    # AGGREGATE
    # -----------------------------
    aggregated = (
        df.groupby("CNTR_CODE")
        .size()
        .reset_index(name="Health relevance")
    )

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

    # Project to Eckert III
    gdf = gdf.to_crs("+proj=eck3")

    merged = gdf.merge(
        aggregated,
        on="CNTR_CODE",
        how="left"
    )

    # -----------------------------
    # SPLIT DATA / NON-DATA
    # -----------------------------
    data_countries = merged[merged["Health relevance"].notna()]
    surrounding = merged[merged["Health relevance"].isna()]

    # -----------------------------
    # CROP TO EUROPE EXTENT
    # -----------------------------
    xmin, ymin, xmax, ymax = data_countries.total_bounds
    buffer = 1_200_000

    ax_xlim = (xmin - buffer, xmax + buffer)
    ax_ylim = (ymin - buffer, ymax + buffer)

    # -----------------------------
    # PLOT
    # -----------------------------
    fig, ax = plt.subplots(figsize=(9, 9))

    # Light blue water
    ax.set_facecolor("#dceaf6")

    # Plot surrounding countries (grey)
    surrounding.plot(
        ax=ax,
        color="#d9d9d9",
        edgecolor="black",
        linewidth=0.4
    )

    # Plot data countries
    data_countries.plot(
        column="Health relevance",
        cmap="OrRd",
        linewidth=0.4,
        edgecolor="black",
        legend=True,
        legend_kwds={
            "shrink": 0.5,
            "aspect": 15,
            "pad": 0.02
        },
        ax=ax
    )

    # Apply cropping
    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)

    # Frame styling
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1)

    ax.set_xticks([])
    ax.set_yticks([])

    ax.set_title(
        "Health-Relevant Climate Legislative Documents in EEA38+UK\n(2000–2025)",
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
    parser.add_argument("--panel", required=True)
    parser.add_argument("--output_csv", required=True)
    parser.add_argument("--output_png", required=True)
    parser.add_argument("--output_pdf", required=True)
    parser.add_argument("--resolution", choices=["low", "high"], default="low")
    parser.add_argument("--nuts_level", type=int, choices=[0,1,2,3], default=0)

    args = parser.parse_args()
    main(args)