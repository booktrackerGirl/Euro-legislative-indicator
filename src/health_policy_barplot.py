#!/usr/bin/env python3

import pandas as pd
import argparse
import matplotlib.pyplot as plt
import numpy as np


def create_health_timeline_plot(legis_path, health_path, output_png):

    print("Reading legislative data...")
    data = pd.read_csv(legis_path)

    print("Reading health annotations...")
    health = pd.read_csv(health_path)

    # ---------------------------------------------------
    # Keep ONLY health-relevant documents
    # ---------------------------------------------------
    health_docs = health.loc[
        health["Health relevance (1/0)"] == 1,
        "Family ID"
    ].unique()

    data = data[data["Family ID"].isin(health_docs)].copy()

    # ---------------------------------------------------
    # Expand semicolon timelines
    # ---------------------------------------------------
    df = data[
        [
            "Family ID",
            "Full timeline of events (types)",
            "Full timeline of events (dates)",
        ]
    ].copy()

    df["event_types"] = df["Full timeline of events (types)"].str.split(";")
    df["event_dates"] = df["Full timeline of events (dates)"].str.split(";")

    df_long = df.explode(["event_types", "event_dates"])

    df_long["event_types"] = df_long["event_types"].astype(str).str.strip()
    df_long["event_dates"] = df_long["event_dates"].astype(str).str.strip()

    df_long["year"] = df_long["event_dates"].str[:4]
    df_long = df_long[df_long["year"].str.match(r"^\d{4}$", na=False)]
    df_long["year"] = df_long["year"].astype(int)

    # ---------------------------------------------------
    # Define start & end events
    # ---------------------------------------------------
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

    # ---------------------------------------------------
    # START YEAR
    # ---------------------------------------------------
    start_df = df_long[df_long["event_types"].isin(start_events)]

    start_years = (
        start_df.groupby("Family ID")["year"]
        .min()
    )

    # ---------------------------------------------------
    # END YEAR
    # ---------------------------------------------------
    end_df = df_long[df_long["event_types"].isin(end_events)]

    end_years = (
        end_df.groupby("Family ID")["year"]
        .max()
    )

    # ---------------------------------------------------
    # Combine into span table
    # ---------------------------------------------------
    policy_years = pd.concat([start_years, end_years], axis=1)
    policy_years.columns = ["start_year", "end_year"]

    policy_years = policy_years.dropna(subset=["start_year"])
    policy_years["start_year"] = policy_years["start_year"].astype(int)

    # ---------------------------------------------------
    # Build yearly stock
    # ---------------------------------------------------
    min_year = 2000
    max_year = df_long["year"].max()
    years = list(range(min_year, max_year + 1))

    active_running = 0
    active_prev = []
    newly_added = []
    dropped = []

    for year in years:

        new_count = (policy_years["start_year"] == year).sum()
        drop_count = (policy_years["end_year"] == year).sum()

        active_prev.append(active_running)
        newly_added.append(new_count)
        dropped.append(-drop_count)

        active_running = active_running + new_count - drop_count

    # ---------------------------------------------------
    # Plot
    # ---------------------------------------------------
    x = np.arange(len(years))
    width = 0.6

    fig, ax = plt.subplots(figsize=(14, 8))

    bars_active = ax.bar(
        x,
        active_prev,
        width,
        label="Active from previous years",
        color="#4C72B0",
    )

    bars_new = ax.bar(
        x,
        newly_added,
        width,
        bottom=active_prev,
        label="Newly added",
        color="#55A868",
    )

    bars_drop = ax.bar(
        x,
        dropped,
        width,
        label="Dropped off",
        color="#C44E52",
    )

    # ---------------------------------------------------
    # Add numeric labels
    # ---------------------------------------------------
    for i in range(len(years)):

        if active_prev[i] > 0:
            ax.text(
                x[i],
                active_prev[i] / 2,
                str(active_prev[i]),
                ha="center",
                va="center",
                fontsize=8,
                color="white",
            )

        if newly_added[i] > 0:
            ax.text(
                x[i],
                active_prev[i] + newly_added[i] + 0.5,
                str(newly_added[i]),
                ha="center",
                va="bottom",
                fontsize=8,
            )

        if dropped[i] < 0:
            ax.text(
                x[i],
                dropped[i] - 0.5,
                str(abs(dropped[i])),
                ha="center",
                va="top",
                fontsize=8,
            )

    # ---------------------------------------------------
    # Paris Agreement marker
    # ---------------------------------------------------
    if 2015 in years:
        idx_2015 = years.index(2015)
        ax.axvline(idx_2015, linestyle=":", linewidth=1.5, color="black")
        ax.text(
            idx_2015 + 0.3,
            max(active_prev) * 0.9,
            "Paris Agreement",
            fontsize=9,
        )

    tick_positions = [years.index(y) for y in years if y % 5 == 0]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels([years[i] for i in tick_positions])

    ax.axhline(0, color="black", linewidth=0.8)

    ax.set_title(
        f"Health-Relevant Legislative Documents: Active, New, and Dropped (2000–{years[-1]})",
        fontweight="bold",
    )

    ax.set_ylabel("Number of documents")
    ax.legend(loc="upper left", frameon=False)

    plt.tight_layout()
    plt.savefig(output_png, dpi=300)
    plt.savefig(output_png.replace(".png", ".pdf"))

    print("Saved PNG and PDF.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--legislation", required=True)
    parser.add_argument("--health", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    create_health_timeline_plot(
        args.legislation,
        args.health,
        args.output,
    )


if __name__ == "__main__":
    main()