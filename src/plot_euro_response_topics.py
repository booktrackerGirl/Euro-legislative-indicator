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
PLOT_END_YEAR   = 2025


# ---------------- PLOTTING FUNCTION ---------------- #

def plot_global_stackplot(annotation_df, legis_df, output_path):

    # ----------------------------
    # Keep health relevant only
    # ----------------------------
    annotation_df = annotation_df[
        annotation_df["Health relevance (1/0)"] >= 1
    ].copy()

    annotation_df["Response"] = annotation_df["Response"].fillna("")

    # Keep only health-relevant documents in legislation
    legis_df = legis_df[
        legis_df["Family ID"].isin(annotation_df["Family ID"])
    ].copy()

    # ----------------------------
    # Expand timeline (semicolon format)
    # ----------------------------
    df = legis_df[
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

    df_long["Year"] = df_long["event_dates"].str[:4]
    df_long = df_long[df_long["Year"].str.match(r"^\d{4}$", na=False)]
    df_long["Year"] = df_long["Year"].astype(int)

    # FIX 2: cap events at PLOT_END_YEAR to avoid future-dated events
    # extending the plot or affecting the active stock
    df_long = df_long[df_long["Year"] <= PLOT_END_YEAR]

    # ----------------------------
    # Define start & end events
    # ----------------------------
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

    # Earliest valid start
    start_years = (
        df_long[df_long["event_types"].isin(start_events)]
        .groupby("Family ID")["Year"]
        .min()
    )

    # Latest removal
    end_years = (
        df_long[df_long["event_types"].isin(end_events)]
        .groupby("Family ID")["Year"]
        .max()
    )

    policy_years = pd.concat([start_years, end_years], axis=1)
    policy_years.columns = ["start_year", "end_year"]
    policy_years = policy_years.dropna(subset=["start_year"])

    # FIX 3: cap end_year at PLOT_END_YEAR (consistent with build_health_counts)
    policy_years["end_year"] = policy_years["end_year"].apply(
        lambda x: min(x, PLOT_END_YEAR) if pd.notnull(x) else x
    )

    # Merge response info
    policy_years = policy_years.merge(
        annotation_df[["Family ID", "Response"]],
        on="Family ID",
        how="left"
    )

    policy_years["Response"] = policy_years["Response"].fillna("")

    # Create response dummies (document-level)
    for category in RESPONSE_COLS:
        policy_years[category] = (
            policy_years["Response"]
            .str.contains(category, case=False, regex=False)
            .astype(int)
        )

    # ----------------------------
    # STOCK LOGIC (timeline-based)
    # ----------------------------
    # FIX 2: use fixed PLOT_END_YEAR instead of max year from data
    YEARS = list(range(PLOT_START_YEAR, PLOT_END_YEAR + 1))

    # FIX 1: seed active_set with pre-2000 policies that are still active
    # at PLOT_START_YEAR, so they are not silently excluded from the count
    pre_start = policy_years[policy_years["start_year"] < PLOT_START_YEAR]
    pre_active = pre_start[
        pre_start["end_year"].isna() | (pre_start["end_year"] >= PLOT_START_YEAR)
    ]["Family ID"]
    active_set = set(pre_active)

    active_totals = []
    category_totals = {col: [] for col in RESPONSE_COLS}

    for year in YEARS:

        new_docs = set(
            policy_years.loc[
                policy_years["start_year"] == year,
                "Family ID"
            ]
        )

        dropped_docs = set(
            policy_years.loc[
                policy_years["end_year"] == year,
                "Family ID"
            ]
        )

        active_set = active_set.union(new_docs)
        active_set = active_set.difference(dropped_docs)

        active_totals.append(len(active_set))

        active_df = policy_years[
            policy_years["Family ID"].isin(active_set)
        ]

        for col in RESPONSE_COLS:
            category_totals[col].append(active_df[col].sum())

    # ----------------------------
    # Build plotting dataframe
    # ----------------------------
    gdata = pd.DataFrame({"Year": YEARS})

    for col in RESPONSE_COLS:
        gdata[col] = category_totals[col]

    gdata["Total documents"] = active_totals

    # Ensure integers
    for col in RESPONSE_COLS + ["Total documents"]:
        gdata[col] = gdata[col].astype(int)

    # ----------------------------
    # Plot
    # ----------------------------
    X = np.arange(len(YEARS))

    gdata["StackSum"] = gdata[RESPONSE_COLS].sum(axis=1)
    GLOBAL_Y_MAX = max(
        gdata["StackSum"].max(),
        gdata["Total documents"].max()
    ) * 1.15

    fig, ax = plt.subplots(figsize=(12, 6))

    stack_arrays = [gdata[col].values for col in RESPONSE_COLS]

    ax.stackplot(
        X,
        stack_arrays,
        colors=[COLORS[c] for c in RESPONSE_COLS],
        alpha=0.5,
        edgecolor="black",
        linewidth=0.3
    )

    line, = ax.plot(
        X,
        gdata["Total documents"],
        color="black",
        marker="o",
        linewidth=2.7,
        label="Total health-relevant documents"
    )

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

    if 2016 in YEARS:
        idx_2016 = YEARS.index(2016)
        ax.axvline(x=X[idx_2016], linestyle="--", linewidth=1.8, color="black")
        ax.text(
            X[idx_2016] + 0.2,
            0.9 * GLOBAL_Y_MAX,
            "Paris Agreement in force",
            va="top",
            fontsize=10
        )

    ax.set_ylim(0, GLOBAL_Y_MAX)
    ax.set_ylabel("Legislative responses", fontsize=13)
    ax.set_title(
        "Active Climate-Health Legislative Documents Over Time in Europe",
        fontsize=13,
        fontweight="bold",
        loc="left"
    )

    step = 5 if len(YEARS) > 20 else 2
    tick_years = YEARS[::step]
    tick_indices = [YEARS.index(y) for y in tick_years]
    ax.set_xticks(tick_indices)
    ax.set_xticklabels([str(int(y)) for y in tick_years])
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    bar_handles = [
        plt.Rectangle((0, 0), 1, 1, color=COLORS[c], alpha=0.5)
        for c in RESPONSE_COLS
    ]

    fig.legend(
        handles=bar_handles + [line],
        labels=RESPONSE_COLS + ["Total health-relevant documents"],
        loc="upper left",
        bbox_to_anchor=(0.1, 0.88),
        frameon=True
    )

    fig.text(
        0.01,
        0.01,
        f"Note: Data available since {DATA_START_YEAR}; analysis shown from {PLOT_START_YEAR} onward.",
        fontsize=11,
        style="italic"
    )

    plt.tight_layout(rect=[0.03, 0.04, 0.97, 0.95])
    plt.savefig(output_path, format="pdf", dpi=300)
    plt.close()


# ---------------- MAIN ---------------- #

def main():
    parser = argparse.ArgumentParser(
        description="Europe stacked area plot using timeline-based stock logic"
    )
    parser.add_argument("--annotation", required=True)
    parser.add_argument("--legis", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    annotation_df = pd.read_csv(args.annotation)
    legis_df = pd.read_csv(args.legis)

    plot_global_stackplot(annotation_df, legis_df, args.output)


if __name__ == "__main__":
    main()