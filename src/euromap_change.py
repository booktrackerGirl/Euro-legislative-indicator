#!/usr/bin/env python3

import argparse
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np


# -----------------------------
# ISO MAP (for shapefile only)
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
# COUNTRY NORMALISATION (CRITICAL FIX)
# -----------------------------
COUNTRY_ALIASES = {
    "UK": "United Kingdom",
    "United Kingdom of Great Britain and Northern Ireland": "United Kingdom",
    "Great Britain": "United Kingdom",
    "Turkey": "Türkiye",
    "Czech Republic": "Czechia"
}


# -----------------------------
# POLICY LIFECYCLE
# -----------------------------
def build_policy_years(legis):

    df = legis.copy()

    df["event_types"] = df["Full timeline of events (types)"].fillna("").astype(str).str.split(";")
    df["event_dates"] = df["Full timeline of events (dates)"].fillna("").astype(str).str.split(";")

    df = df.explode(["event_types", "event_dates"])

    df["event_types"] = df["event_types"].astype(str).str.strip()
    df["event_dates"] = df["event_dates"].astype(str).str.strip()

    df["Year"] = df["event_dates"].str[:4]
    df = df[df["Year"].str.match(r"^\d{4}$", na=False)]
    df["Year"] = df["Year"].astype(int)

    start_events = ["Passed/Approved", "Entered Into Force", "Set", "Net Zero Pledge"]
    end_events = ["Repealed/Replaced", "Closed", "Settled"]

    start_years = df[df["event_types"].isin(start_events)].groupby("Family ID")["Year"].min()
    end_years = df[df["event_types"].isin(end_events)].groupby("Family ID")["Year"].max()

    policy = pd.concat([start_years, end_years], axis=1)
    policy.columns = ["start_year", "end_year"]
    policy = policy.dropna(subset=["start_year"]).reset_index()

    return policy


# -----------------------------
# ACTIVE STOCK
# -----------------------------
def active_stock(policy, year):

    started = set(policy.loc[policy["start_year"] <= year, "Family ID"])

    ended = set(policy.loc[
        (policy["end_year"].notna()) &
        (policy["end_year"] < year),
        "Family ID"
    ])

    return started - ended


# -----------------------------
# MAIN
# -----------------------------
def main(args):

    print("Loading data...")

    annotations = pd.read_csv(args.input_csv)
    legis = pd.read_csv(args.legis)

    # -----------------------------
    # CLEAN COUNTRY FIELD (CRITICAL FIX)
    # -----------------------------
    legis["Country_clean"] = legis["Geographies"].astype(str).str.strip()
    legis["Country_clean"] = legis["Country_clean"].replace(COUNTRY_ALIASES)

    # -----------------------------
    # FILTER HEALTH FAMILIES
    # -----------------------------
    annotations["Health relevance (1/0)"] = annotations["Health relevance (1/0)"].fillna(0).astype(int)

    health_families = annotations.loc[
        annotations["Health relevance (1/0)"] == 1,
        "Family ID"
    ].unique()

    legis = legis[legis["Family ID"].isin(health_families)].copy()

    # -----------------------------
    # BUILD LIFECYCLE
    # -----------------------------
    policy = build_policy_years(legis)

    YEARS = [2000, 2025]

    results = []

    # -----------------------------
    # CHANGE CALCULATION
    # -----------------------------
    for country in ISO_MAP.keys():

        fams = legis[legis["Country_clean"] == country]["Family ID"].unique()
        sub = policy[policy["Family ID"].isin(fams)]

        if len(sub) == 0:
            change = np.nan
        else:
            a2000 = len(active_stock(sub, 2000))
            a2025 = len(active_stock(sub, 2025))

            change = np.nan if a2000 == 0 else ((a2025 - a2000) / a2000) * 100

        results.append((country, change))

    result_df = pd.DataFrame(results, columns=["Country", "Change"])
    result_df["CNTR_CODE"] = result_df["Country"].map(ISO_MAP)

    result_df.to_csv(args.output_csv, index=False)

    # -----------------------------
    # LOAD SHAPEFILE
    # -----------------------------
    shp = (
        "./shapefile/NUTS_RG_01M_2024_4326_with_UK_2021.shp"
        if args.resolution == "low"
        else "./shapefile/NUTS_RG_10M_2024_4326_with_UK_2021.shp"
    )

    gdf = gpd.read_file(shp)
    gdf = gdf[gdf["LEVL_CODE"] == args.nuts_level].to_crs("+proj=eck3")

    merged = gdf.merge(result_df, on="CNTR_CODE", how="left")

    data = merged[merged["Change"].notna()]
    grey = merged[merged["Change"].isna()]

    # -----------------------------
    # COLOR SCALE (stable %)
    # -----------------------------
    vals = result_df["Change"].dropna()

    vmax = np.nanpercentile(np.abs(vals), 95)
    if np.isnan(vmax) or vmax == 0:
        vmax = 100

    norm = mpl.colors.TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)

    # -----------------------------
    # PLOT
    # -----------------------------
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_facecolor("#dceaf6")

    grey.plot(
        ax=ax,
        color="#d9d9d9",
        edgecolor="black",
        linewidth=0.7
    )

    data.plot(
        column="Change",
        cmap="coolwarm",
        norm=norm,
        edgecolor="black",
        linewidth=0.7,
        legend=True,
        legend_kwds={
            "label": "% change in active legislative stock (2000 → 2025)",
            "shrink": 0.55
        },
        ax=ax
    )

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(
        "Change in Active Health-Related Legislative Stock (2000–2025)\nEEA38+UK",
        fontsize=13
    )

    plt.tight_layout()

    plt.savefig(args.output_png, dpi=300, bbox_inches="tight")
    plt.savefig(args.output_pdf, bbox_inches="tight")
    plt.close()

    print("Done.")


# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--input_csv", required=True)
    parser.add_argument("--legis", required=True)
    parser.add_argument("--output_csv", required=True)
    parser.add_argument("--output_png", required=True)
    parser.add_argument("--output_pdf", required=True)
    parser.add_argument("--resolution", choices=["low", "high"], default="low")
    parser.add_argument("--nuts_level", type=int, choices=[0, 1, 2, 3], default=0)

    args = parser.parse_args()
    main(args)