#!/usr/bin/env python3

import argparse
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from collections import Counter

# ============================================================
# GLOBALS
# ============================================================
WORLD_URL = "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"

EU_COUNTRIES = [
    'Albania','Austria','Belgium','Bosnia and Herzegovina','Bulgaria','Croatia',
    'Cyprus','Czechia','Denmark','Estonia','Finland','France','Germany','Greece',
    'Hungary','Iceland','Ireland','Italy','Kosovo','Latvia','Liechtenstein','Lithuania',
    'Luxembourg','Malta','Montenegro','Netherlands','North Macedonia','Norway','Poland',
    'Portugal','Romania','Serbia','Slovakia','Slovenia','Spain','Sweden','Switzerland',
    'Türkiye','United Kingdom'
]

FEATURE_COLS = [
    "Health relevance (1/0)",
    "Health adaptation mandate (1/0)",
    "Institutional health role (1/0)"
]

# ============================================================
# STEP 1: CREATE COUNTRY-YEAR HEALTH STATS
# ============================================================
def create_country_year_health_stats(input_csv, panel_csv, output_csv,
                                     multilabel_col="Response", year_col="Year"):
    df = pd.read_csv(input_csv)
    panel = pd.read_csv(panel_csv)

    # Remove failed extractions
    df = df[df['Notes'] != 'Extraction failed']

    # Ensure ID and Year columns
    if "Doc ID" in df.columns:
        df = df.rename(columns={"Doc ID": "Document ID"})
    if "year" in panel.columns:
        panel = panel.rename(columns={"year": "Year"})
    elif "Year" not in panel.columns:
        raise ValueError("Panel file must contain 'Year' or 'year' column.")

    df = df.drop(columns=["Year"], errors="ignore")
    panel = panel[["Document ID", "Year"]]

    # Merge with panel
    df = df.merge(panel.rename(columns={"Year": year_col}),
                  on="Document ID", how="inner")

    # Ensure binary features
    for c in FEATURE_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    # EU expansion
    df_eu = df[df["Country"] == "EU"].copy()
    df_non_eu = df[df["Country"] != "EU"].copy()
    df_eu_expanded = pd.concat([df_eu.assign(Country=c) for c in EU_COUNTRIES],
                               ignore_index=True)
    df_country = pd.concat([df_non_eu, df_eu_expanded], ignore_index=True)

    # Filter to health-relevant documents and deduplicate
    df_health = df_country[df_country["Health relevance (1/0)"] >= 1].copy()
    df_health = df_health.drop_duplicates(subset=["Document ID", "Country", year_col])

    # Country-year totals
    country_year_totals = (
        df_health.groupby(["Country", year_col])
        .size()
        .reset_index(name="Total documents")
    )

    # Sum binary features
    country_year_features = (
        df_health.groupby(["Country", year_col])[FEATURE_COLS]
        .sum().reset_index()
    )

    # Topic counts
    topic_records = []
    for (country, year), group in df_health.groupby(["Country", year_col]):
        all_topics = []
        for cell in group[multilabel_col].dropna():
            all_topics.extend([t.strip() for t in cell.split(";") if t.strip()])
        counts = Counter(all_topics)
        for topic, count in counts.items():
            topic_records.append({"Country": country, year_col: year, topic: count})
    country_year_topics = pd.DataFrame(topic_records)
    country_year_topics_wide = (
        country_year_topics.pivot_table(index=["Country", year_col], aggfunc="sum")
        .reset_index()
    )

    # Merge everything
    country_year_stats = (
        country_year_totals
        .merge(country_year_features, on=["Country", year_col], how="left")
        .merge(country_year_topics_wide, on=["Country", year_col], how="left")
    )

    country_year_stats.to_csv(output_csv, index=False)
    return country_year_stats

# ============================================================
# STEP 2: CREATE EUROPEAN MAP
# ============================================================
def harmonize_country_names(df):
    mapping = {
        "United States": "United States of America",
        "Russia": "Russian Federation",
        "Congo": "Republic of the Congo",
        "Congo, Dem. Rep.": "Democratic Republic of the Congo",
        "Ivory Coast": "Côte d'Ivoire",
        "South Korea": "Republic of Korea",
        "North Korea": "Democratic People's Republic of Korea",
        "EU": None,
        "Türkiye": "Turkey"  
    }
    df["Country"] = df["Country"].replace(mapping)
    return df


def create_euro_map(input_csv, output_png, output_pdf, european_countries, global_max=None):
    df = pd.read_csv(input_csv)
    df = df[df["Country"].isin(european_countries)].copy()
    df = df[(df["Year"] >= 2000) & (df["Year"] <= 2025)].copy()
    df = df[df["Health relevance (1/0)"] >= 1]

    country_counts = df.groupby("Country")["Total documents"].sum().reset_index()
    country_counts = harmonize_country_names(country_counts)

    world = gpd.read_file(WORLD_URL)
    world["NAME"] = world["NAME"].replace({"Turkey": "Türkiye", "United Kingdom of Great Britain and Northern Ireland": "United Kingdom"})
    world = world[world["NAME"].isin(european_countries)].copy()
    world_merged = world.merge(country_counts, how="left",
                               left_on="NAME", right_on="Country")
    world_merged["Total documents"] = world_merged["Total documents"].fillna(0)

    # ----------------------------
    # Use global max if provided, otherwise local max
    # ----------------------------
    europe_max = global_max if global_max is not None else world_merged["Total documents"].max()

    # Create bins (linear + gradient-based)
    low_bins = list(range(0, min(europe_max, 20) + 1))
    high_bins = list(range(21, int(europe_max) + 5, max(1, int(europe_max / 10))))
    bins = sorted(list(set(low_bins + high_bins)))

    grey = [0.8, 0.8, 0.8, 1]
    num_gradients = len(bins) - 1
    greens = plt.cm.Greens(np.linspace(0.2, 1, num_gradients))
    colors_list = np.vstack([grey, greens])
    cmap = ListedColormap(colors_list)
    norm = BoundaryNorm(bins, cmap.N)

    # ----------------------------
    # Plot
    # ----------------------------
    fig, ax = plt.subplots(figsize=(12, 10))
    world.boundary.plot(ax=ax, linewidth=0.7, color="black")
    world_merged.plot(column="Total documents", cmap=cmap, norm=norm,
                      ax=ax, edgecolor="none")
    
    # ---- ADD COUNTRY LABELS ----
    '''for idx, row in world_merged.iterrows():
        if pd.notnull(row["Total documents"]):
            point = row["geometry"].representative_point()
            ax.text(
                point.x,
                point.y,
                row["NAME"],
                fontsize=8,               # very small
                ha="center",
                va="center",
                color="#6A0DAD",
                alpha=0.85
            )

    '''

    ax.set_title("Cumulative Active Health-Related Legislative Documents in Europe (2000–2025)",
                 fontsize=15, fontweight="bold")
    # Zoom into Europe
    ax.set_xlim(-25, 45)
    ax.set_ylim(30, 75)

    ax.axis("off")

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    # Vertical colorbar on the right
    cbar = fig.colorbar(
        sm,
        ax=ax,
        orientation="vertical",
        fraction=0.035,   # width of colorbar
        pad=0.02          # spacing between map and colorbar
    )

    cbar.set_label("Total Documents", fontsize=12)

    num_ticks = 8
    tick_indices = np.linspace(0, len(bins) - 1, num_ticks, dtype=int)
    cbar.set_ticks([bins[i] for i in tick_indices])
    cbar.set_ticklabels([str(bins[i]) for i in tick_indices])

    plt.tight_layout()
    fig.savefig(output_png, dpi=300, bbox_inches="tight")
    fig.savefig(output_pdf, bbox_inches="tight")
    plt.close(fig)


# ============================================================
# MAIN CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Create European country-year health stats and map"
    )
    parser.add_argument("--annotations", required=True,
                        help="Path to combined annotation CSV")
    parser.add_argument("--panel", required=True,
                        help="Path to yearly panel CSV")
    parser.add_argument("--output_csv", required=True,
                        help="Path to output country-year CSV")
    parser.add_argument("--output_png", required=True,
                        help="Path to output PNG map")
    parser.add_argument("--output_pdf", required=True,
                        help="Path to output PDF map")
    args = parser.parse_args()

    print("✅ Generating country-year health stats...")
    create_country_year_health_stats(
        input_csv=args.annotations,
        panel_csv=args.panel,
        output_csv=args.output_csv
    )

    print("✅ Calculating global max for map color scaling...")
    df_stats = pd.read_csv(args.output_csv)
    # Only consider health-relevant documents
    global_max = df_stats[df_stats["Health relevance (1/0)"] >= 1]["Total documents"].max()
    if pd.isna(global_max) or global_max == 0:
        global_max = 1  # fallback to avoid division by zero

    print(f"   ➤ Global max Total documents: {global_max}")

    print("✅ Creating European map...")
    create_euro_map(
        input_csv=args.output_csv,
        output_png=args.output_png,
        output_pdf=args.output_pdf,
        european_countries=EU_COUNTRIES,
        global_max=global_max
    )

    print("✔ Done!")


if __name__ == "__main__":
    main()
