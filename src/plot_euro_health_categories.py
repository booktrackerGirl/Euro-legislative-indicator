#!/usr/bin/env python3

import argparse
import pandas as pd
import matplotlib.pyplot as plt

# ----------------------------
# Fixed health categories
# ----------------------------
HEALTH_CATEGORIES = [
    "communicable_disease",
    "environmental_health",
    "food_waterborne",
    "general_health",
    "injury_trauma",
    "maternal_child_health",
    "mental_health",
    "mortality_morbidity",
    "non_communicable_disease",
    "nutrition",
    "pathogens_microbiology",
    "substance_use",
    "vector_borne_zoonotic"
]

# ----------------------------
# Colors
# ----------------------------
CATEGORY_COLORS = {
    "general_health": "#1f77b4",
    "communicable_disease": "#ff7f0e",
    "non_communicable_disease": "#2ca02c",
    "vector_borne_zoonotic": "#d62728",
    "food_waterborne": "#9467bd",
    "environmental_health": "#8c564b",
    "nutrition": "#e377c2",
    "maternal_child_health": "#7f7f7f",
    "mental_health": "#bcbd22",
    "injury_trauma": "#17becf",
    "mortality_morbidity": "#aec7e8",
    "pathogens_microbiology": "#ffbb78",
    "substance_use": "#98df8a"
}

# ----------------------------
# Human-readable labels
# ----------------------------
CATEGORY_LABELS = {
    "general_health": "General health",
    "communicable_disease": "Communicable disease",
    "non_communicable_disease": "Non-communicable disease",
    "vector_borne_zoonotic": "Vector-borne & zoonotic",
    "food_waterborne": "Food & waterborne",
    "environmental_health": "Environmental health",
    "nutrition": "Nutrition",
    "maternal_child_health": "Maternal & child health",
    "mental_health": "Mental health",
    "injury_trauma": "Injury & trauma",
    "mortality_morbidity": "Mortality & morbidity",
    "pathogens_microbiology": "Pathogens & microbiology",
    "substance_use": "Substance use"
}

# ----------------------------
# Main processing
# ----------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Plot cumulative trends in health keyword categories"
    )
    parser.add_argument("--input", required=True, help="Health keyword CSV file")
    parser.add_argument("--panel", required=True, help="Policy year panel CSV")
    parser.add_argument("--output", required=True, help="Output figure (PDF/PNG)")
    parser.add_argument("--start-year", type=int, default=2000, help="Start year for plot")
    args = parser.parse_args()

    # -------------------------------------------------
    # Load data
    # -------------------------------------------------
    df = pd.read_csv(args.input)
    panel = pd.read_csv(args.panel)

    # Harmonize ID columns
    if "Doc ID" in df.columns:
        df = df.rename(columns={"Doc ID": "Document ID"})
    if "year" in panel.columns:
        panel = panel.rename(columns={"year": "Year"})
    panel = panel[["Document ID", "Year"]]

    # Merge panel (creates cumulative structure)
    df = df.merge(
        panel[["Document ID", "Year"]],
        on="Document ID",
        how="inner",
        suffixes=("_ann", "_panel")
    )

    # Force panel year
    df["Year"] = df["Year_panel"]
    df = df.drop(columns=["Year_ann", "Year_panel"], errors="ignore")

    # Clean Year exactly like response script
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df.dropna(subset=["Year"])
    df["Year"] = df["Year"].astype(int)


    # Only include documents with Health relevance > 0
    df = df[df["Health relevance (1/0)"] >= 1].copy()

    # Drop rows missing the health keyword column
    df = df.dropna(subset=["Health keyword categories"])

    # Drop duplicates
    df = df.drop_duplicates(subset=["Document ID", "Year"])

    # -------------------------------------------------
    # Filter by start year 
    # -------------------------------------------------
    df = df[df["Year"] >= args.start_year].copy()

    # -------------------------------------------------
    # Create health dummies (row level)
    # -------------------------------------------------
    #df["Health keyword categories"] = df["Health keyword categories"].fillna("")


    for category in HEALTH_CATEGORIES:
        df[category] = (
            df["Health keyword categories"]
            .str.contains(category, case=False, regex=False)
            .astype(int)
        )

    # -------------------------------------------------
    # Collapse to ONE row per Document ID per Year
    # -------------------------------------------------
    doc_year = (
        df
        .groupby(["Year", "Document ID"], as_index=False)[HEALTH_CATEGORIES]
        .max()
    )


    # -------------------------------------------------
    # Aggregate globally by year (single source object)
    # -------------------------------------------------
    gdata = (
        doc_year
        .groupby("Year", as_index=False)
        .agg({
            **{col: "sum" for col in HEALTH_CATEGORIES},
            "Document ID": "nunique"
        })
        .rename(columns={"Document ID": "Total documents"})
        .sort_values("Year")
    )

    # Ensure integer types
    for col in HEALTH_CATEGORIES + ["Total documents"]:
        gdata[col] = gdata[col].astype(int)


    # -------------------------------------------------
    # Plot
    # -------------------------------------------------
    plt.figure(figsize=(15, 7))
    plt.stackplot(
        gdata["Year"],
        [gdata[col] for col in HEALTH_CATEGORIES],
        colors=[CATEGORY_COLORS[c] for c in HEALTH_CATEGORIES],
        labels=[CATEGORY_LABELS[c] for c in HEALTH_CATEGORIES],
        alpha=0.5,
        edgecolor="black",
        linewidth=0.3
    )
    plt.plot(
        gdata["Year"],
        gdata["Total documents"],
        color="#222222",
        linewidth=2.7,
        marker="o",
        label="Total health-relevant documents"
    )

    for year, val in zip(gdata["Year"], gdata["Total documents"]):
        if val > 0:
            plt.text(year, val + 0.03 * gdata["Year"].max(), str(int(val)),
                     ha="center", va="bottom", fontsize=9, fontweight="bold")

    plt.xlabel("Year", fontsize=13)
    plt.ylabel("Number of documents", fontsize=13)
    plt.title("Trends in Health-Related Categories in Climate Legislative Documents from Europe (2000-2025)",
              fontsize=13, fontweight="bold",  loc="left")
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    plt.legend(loc="upper left", fontsize=10, frameon=True)

    # Highlight Paris Agreement
    if 2015 in gdata["Year"].values:
        plt.axvline(x=2015, linestyle="--", linewidth=2, color="black", alpha=0.8)
        plt.text(2015 + 0.2, plt.ylim()[1] * 0.95, "Paris Agreement",
                 va="top", ha="left", fontsize=10, fontweight="bold")

    plt.tight_layout()
    plt.savefig(args.output)
    plt.close()


if __name__ == "__main__":
    main()
