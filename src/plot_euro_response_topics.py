#!/usr/bin/env python3

import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------- CONFIG ---------------- #

RESPONSE_COLS = [
    "Adaptation",
    "Disaster Risk Management",
    "Loss And Damage",
    "Mitigation"
]

COLORS = {
    "Adaptation": "#4daf4a",
    "Disaster Risk Management": "#377eb8",
    "Loss And Damage": "#e41a1c",
    "Mitigation": "#984ea3"
}

DATA_START_YEAR = 1963
PLOT_START_YEAR = 2000


# ---------------- PLOTTING FUNCTION ---------------- #

def plot_global_stackplot(annotation_df, panel_df, output_path):

    # ----------------------------
    # Harmonize ID columns
    # ----------------------------
    if "Doc ID" in annotation_df.columns:
        annotation_df = annotation_df.rename(columns={"Doc ID": "Document ID"})
    if "Doc ID" in panel_df.columns:
        panel_df = panel_df.rename(columns={"Doc ID": "Document ID"})

    # ----------------------------
    # Merge panel (creates stock structure)
    # ----------------------------
    df = annotation_df.merge(
        panel_df[["Document ID", "Year"]],
        on="Document ID",
        how="inner",
        suffixes=("_ann", "_panel")
    )

    # Use panel year
    df["Year"] = df["Year_panel"]
    df = df.drop(columns=["Year_ann", "Year_panel"], errors="ignore")

    # Ensure numeric year
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df.dropna(subset=["Year"])
    df["Year"] = df["Year"].astype(int)

    # ----------------------------
    # Keep only years >= 2000
    # ----------------------------
    df = df[df["Year"] >= PLOT_START_YEAR].copy()

    # ----------------------------
    # Only include health-relevant documents
    # ----------------------------
    df = df[df["Health relevance (1/0)"] >= 1].copy()

    # Drop rows with missing Response column (normalized)
    #df = df.dropna(subset=["Response"])

    # Keep ALL documents — even if Response is missing
    df["Response"] = df["Response"].fillna("")

    # Drop duplicates per document per year (normalized)
    df = df.drop_duplicates(subset=["Document ID", "Year"])

    # ----------------------------
    # Create response dummies (row level)
    # ----------------------------
    #df["Response"] = df["Response"].fillna("")

    for category in RESPONSE_COLS:
        df[category] = (
            df["Response"]
            .str.contains(category, case=False, regex=False)
            .astype(int)
        )

    # ----------------------------
    # Collapse to ONE row per Document ID per Year
    # ----------------------------
    doc_year = df.groupby(["Year", "Document ID"], as_index=False)[RESPONSE_COLS].max()

    # ----------------------------
    # Aggregate globally by year
    # ----------------------------
    gdata = (
        doc_year.groupby("Year", as_index=False)
        .agg({
            **{col: "sum" for col in RESPONSE_COLS},
            "Document ID": "nunique"
        })
        .rename(columns={"Document ID": "Total documents"})
        .sort_values("Year")
    )

    # Ensure integer types
    for col in RESPONSE_COLS + ["Total documents"]:
        gdata[col] = gdata[col].astype(int)

    # ----------------------------
    # Prepare X-axis
    # ----------------------------
    YEARS = sorted(gdata["Year"].unique())
    X = np.arange(len(YEARS))

    gdata = gdata.set_index("Year").reindex(YEARS, fill_value=0).reset_index()

    # ----------------------------
    # Y-axis scaling
    # ----------------------------
    gdata["StackSum"] = gdata[RESPONSE_COLS].sum(axis=1)
    GLOBAL_Y_MAX = max(gdata["StackSum"].max(), gdata["Total documents"].max()) * 1.15

    # ----------------------------
    # Plot
    # ----------------------------
    fig, ax = plt.subplots(figsize=(12, 6))

    stack_arrays = [gdata[col].values for col in RESPONSE_COLS]

    ax.stackplot(
        X,
        stack_arrays,
        colors=[COLORS[c] for c in RESPONSE_COLS],
        alpha=0.5,
        edgecolor='black',
        linewidth=0.3
    )

    # Total documents line
    line, = ax.plot(
        X,
        gdata["Total documents"],
        color="black",
        marker="o",
        linewidth=2.7,
        label="Total health-relevant documents"
    )

    # Numeric labels on total line
    for xi, val in zip(X, gdata["Total documents"]):
        if val > 0:
            ax.text(
                xi,
                val + 0.03 * GLOBAL_Y_MAX,
                str(int(val)),
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold"
            )

    # Paris Agreement marker (2015)
    if 2015 in YEARS:
        idx_2015 = YEARS.index(2015)
        ax.axvline(x=X[idx_2015], linestyle="--", linewidth=1.8, color="black")
        ax.text(X[idx_2015] + 0.2, 0.9 * GLOBAL_Y_MAX, "Paris Agreement", va="top", fontsize=10)

    # Labels & ticks
    ax.set_ylim(0, GLOBAL_Y_MAX)
    ax.set_ylabel("Legislative responses", fontsize=13)
    ax.set_title(
        "Active Climate-Health Legislative Documents Over Time in Europe (2000-2025)",
        fontsize=13, fontweight="bold", loc="left"
    )

    step = 5 if len(YEARS) > 20 else 2
    tick_years = YEARS[::step]
    tick_indices = [YEARS.index(y) for y in tick_years]
    ax.set_xticks(tick_indices)
    ax.set_xticklabels([str(int(y)) for y in tick_years])
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    # Legend
    bar_handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[c], alpha=0.5) for c in RESPONSE_COLS]
    fig.legend(
        handles=bar_handles + [line],
        labels=RESPONSE_COLS + ["Total health-relevant documents"],
        loc="upper left",
        bbox_to_anchor=(0.1, 0.88),
        frameon=True
    )

    fig.text(
        0.01, 0.01,
        f"Note: Data available since {DATA_START_YEAR}; analysis shown from {PLOT_START_YEAR} onward.",
        fontsize=11, style="italic"
    )

    plt.tight_layout(rect=[0.03, 0.04, 0.97, 0.95])
    plt.savefig(output_path, format="pdf", dpi=300)
    plt.close()


# ---------------- MAIN ---------------- #

def main():
    parser = argparse.ArgumentParser(
        description="Global stacked area plot using annotation + panel data"
    )
    parser.add_argument("--annotation", required=True, help="Annotation CSV")
    parser.add_argument("--panel", required=True, help="Expanded panel CSV")
    parser.add_argument("--output", required=True, help="Output PDF")

    args = parser.parse_args()

    annotation_df = pd.read_csv(args.annotation)
    panel_df = pd.read_csv(args.panel)

    plot_global_stackplot(annotation_df, panel_df, args.output)


if __name__ == "__main__":
    main()
