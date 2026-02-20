#!/usr/bin/env python3

import pandas as pd
import argparse
import matplotlib.pyplot as plt
import numpy as np


def create_health_timeline_plot(legis_path, health_path, output_png):
    """
    Creates a stacked bar chart showing:
    - Active policies from previous years
    - Newly added policies
    - Dropped policies (negative values)

    Includes:
    - Paris Agreement vertical reference line (2015)
    - Horizontal year labels
    - X-axis ticks every 5 years
    """

    print("Reading legislative data...")
    data = pd.read_csv(legis_path)
    data = data[~data["Document Content URL"].isna()]

    print("Reading health annotations...")
    health = pd.read_csv(health_path)

    # Keep only health-relevant documents
    health_docs = health[health["Health relevance (1/0)"] == 1]["Doc ID"].unique()
    data = data[data["Document ID"].isin(health_docs)]

    # -----------------------------
    # Split timeline into long form
    # -----------------------------
    df = data[
        [
            "Document ID",
            "Full timeline of events (types)",
            "Full timeline of events (dates)",
        ]
    ].copy()

    df["event_types"] = df["Full timeline of events (types)"].str.split(";")
    df["event_dates"] = df["Full timeline of events (dates)"].str.split(";")

    df_long = df.explode(["event_types", "event_dates"])

    df_long["event_dates"] = df_long["event_dates"].astype(str).str.strip()
    df_long["year"] = df_long["event_dates"].str[:4]

    df_long = df_long[df_long["year"].str.match(r"^\d{4}$", na=False)]
    df_long["year"] = df_long["year"].astype(int)

    # -----------------------------
    # Define start and end events
    # -----------------------------
    start_events = [
        "Passed/Approved",
        "Entered Into Force",
        "Set",
        "Net Zero Pledge",
    ]

    end_events = [
        "Repealed/Replaced",
        "Closed",
        "Settled",
    ]

    # -----------------------------
    # Determine start years
    # Prefer "Passed/Approved" if available
    # -----------------------------
    df_starts = df_long[df_long["event_types"].isin(start_events)]

    passed_years = (
        df_starts[df_starts["event_types"] == "Passed/Approved"]
        .groupby("Document ID")["year"]
        .min()
    )

    other_years = (
        df_starts[df_starts["event_types"] != "Passed/Approved"]
        .groupby("Document ID")["year"]
        .min()
    )

    start_years = other_years.copy()
    start_years.update(passed_years)
    start_years = start_years.combine_first(passed_years)

    # -----------------------------
    # Determine end years
    # -----------------------------
    end_years = (
        df_long[df_long["event_types"].isin(end_events)]
        .groupby("Document ID")["year"]
        .max()
    )

    policy_years = pd.concat([start_years, end_years], axis=1)
    policy_years.columns = ["start_year", "end_year"]

    policy_years = policy_years[policy_years["start_year"].notna()]
    policy_years["start_year"] = policy_years["start_year"].astype(int)

    # -----------------------------
    # Build yearly counts
    # -----------------------------
    min_year = 2000
    max_year = df_long["year"].max()
    years = list(range(min_year, max_year + 1))

    active_prev = []
    newly_added = []
    dropped = []

    for year in years:
        new_docs = policy_years[policy_years["start_year"] == year]
        dropped_docs = policy_years[policy_years["end_year"] == year]

        active_docs = policy_years[
            (policy_years["start_year"] < year)
            & (
                (policy_years["end_year"].isna())
                | (policy_years["end_year"] >= year)
            )
        ]

        newly_added.append(len(new_docs))
        dropped.append(-len(dropped_docs))
        active_prev.append(len(active_docs))

    # -----------------------------
    # Plot
    # -----------------------------
    x = np.arange(len(years))
    width = 0.6

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.labelsize": 12,
        }
    )

    fig, ax = plt.subplots(figsize=(14, 8))

    # Stacked positive bars
    ax.bar(
        x,
        active_prev,
        width,
        label="Active from previous years",
        color="#4C72B0",
        alpha=0.9,
    )

    ax.bar(
        x,
        newly_added,
        width,
        bottom=active_prev,
        label="Newly added",
        color="#55A868",
        alpha=0.9,
    )

    # Negative bars
    ax.bar(
        x,
        dropped,
        width,
        label="Dropped off",
        color="#C44E52",
        alpha=0.9,
    )

    # -----------------------------
    # Add counts above/below bars
    # -----------------------------
    for i in range(len(years)):

        # --- Active from previous years ---
        if active_prev[i] > 0:
            ax.text(
                x[i],
                active_prev[i] / 2,   # vertically centered in blue bar
                str(active_prev[i]),
                ha="center",
                va="center",
                fontsize=8,
                color="white"  # better contrast on blue
            )

        # --- Newly added ---
        if newly_added[i] > 0:
            ax.text(
                x[i],
                active_prev[i] + newly_added[i] + 0.5,
                str(newly_added[i]),
                ha="center",
                va="bottom",
                fontsize=8
            )

        # --- Dropped ---
        if dropped[i] < 0:
            ax.text(
                x[i],
                dropped[i] - 0.5,
                str(abs(dropped[i])),
                ha="center",
                va="top",
                fontsize=8
            )


    # -----------------------------
    # Paris Agreement (2015)
    # -----------------------------
    if 2015 in years:
        idx_2015 = years.index(2015)

        ax.axvline(
            idx_2015,
            linestyle=":",
            linewidth=1.5,
            color="black",
        )

        ax.text(
            idx_2015 + 0.3,
            max(active_prev) * 0.9,
            "Paris Agreement",
            #rotation=90,
            fontsize=9,
        )

    # -----------------------------
    # Axis formatting
    # -----------------------------
    tick_positions = [
        years.index(y) for y in years if y % 5 == 0
    ]

    ax.set_xticks(tick_positions)
    ax.set_xticklabels(
        [years[i] for i in tick_positions],
        rotation=0,
    )

    ax.axhline(0, color="black", linewidth=0.8)

    ax.set_title(
        f"Health-Relevant Legislative Documents: Active, New, and Dropped (2000–{years[-1]})",
        fontweight="bold",
    )

    ax.set_ylabel("Number of documents")

    ax.legend(loc="upper left", frameon=False)

    plt.tight_layout()

    # Save outputs
    plt.savefig(output_png, dpi=300)
    plt.savefig(output_png.replace(".png", ".pdf"))

    print("Saved PNG and PDF.")


def main():
    parser = argparse.ArgumentParser(
        description="Create stacked bar plot for health-relevant policy timelines (from 2000)."
    )

    parser.add_argument(
        "--legislation",
        required=True,
        help="Path to legislative dataset CSV",
    )

    parser.add_argument(
        "--health",
        required=True,
        help="Path to health annotation CSV",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output PNG file",
    )

    args = parser.parse_args()

    create_health_timeline_plot(
        args.legislation,
        args.health,
        args.output,
    )


if __name__ == "__main__":
    main()
