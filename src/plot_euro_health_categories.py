#!/usr/bin/env python3

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ----------------------------
# Health categories and colors
# ----------------------------
HEALTH_CATEGORIES = [
    "communicable_disease", "environmental_health", "food_waterborne",
    "general_health", "injury_trauma", "maternal_child_health",
    "mental_health", "mortality_morbidity", "non_communicable_disease",
    "nutrition", "pathogens_microbiology", "substance_use",
    "vector_borne_zoonotic"
]

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
# Main plotting function
# ----------------------------
def plot_health_stackplot(annotation_df, legis_df, output_path, plot_start_year=2000):
    # Harmonize columns
    if "Doc ID" in annotation_df.columns:
        annotation_df = annotation_df.rename(columns={"Doc ID": "Document ID"})
    annotation_df["Health keyword categories"] = annotation_df["Health keyword categories"].fillna("")

    # Keep health-relevant docs
    annotation_df = annotation_df[annotation_df["Health relevance (1/0)"] >= 1].copy()

    legis_df = legis_df[legis_df["Document ID"].isin(annotation_df["Document ID"])].copy()

    # Expand timeline events
    df = legis_df[[
        "Document ID",
        "Full timeline of events (types)",
        "Full timeline of events (dates)"
    ]].copy()
    df["event_types"] = df["Full timeline of events (types)"].str.split(";")
    df["event_dates"] = df["Full timeline of events (dates)"].str.split(";")
    df_long = df.explode(["event_types", "event_dates"])
    df_long["event_types"] = df_long["event_types"].astype(str).str.strip()
    df_long["event_dates"] = df_long["event_dates"].astype(str).str.strip()
    df_long["Year"] = df_long["event_dates"].str[:4]
    df_long = df_long[df_long["Year"].str.match(r"^\d{4}$", na=False)]
    df_long["Year"] = df_long["Year"].astype(int)

    # Define start & end events
    start_events = ["Passed/Approved", "Entered Into Force", "Set", "Net Zero Pledge"]
    end_events = ["Repealed/Replaced", "Closed", "Settled"]

    start_years = df_long[df_long["event_types"].isin(start_events)].groupby("Document ID")["Year"].min()
    end_years = df_long[df_long["event_types"].isin(end_events)].groupby("Document ID")["Year"].max()

    policy_years = pd.concat([start_years, end_years], axis=1)
    policy_years.columns = ["start_year", "end_year"]
    policy_years = policy_years.dropna(subset=["start_year"])

    # Merge health keyword info
    policy_years = policy_years.merge(
        annotation_df[["Document ID", "Health keyword categories"]],
        on="Document ID",
        how="left"
    )
    policy_years["Health keyword categories"] = policy_years["Health keyword categories"].fillna("")

    # Create health dummies
    for cat in HEALTH_CATEGORIES:
        policy_years[cat] = policy_years["Health keyword categories"].str.contains(cat, case=False, regex=False).astype(int)

    # Timeline-based stock logic
    max_year = df_long["Year"].max()
    YEARS = list(range(plot_start_year, max_year + 1))
    active_set = set()
    active_totals = []
    category_totals = {cat: [] for cat in HEALTH_CATEGORIES}

    for year in YEARS:
        new_docs = set(policy_years[policy_years["start_year"] == year]["Document ID"])
        dropped_docs = set(policy_years[policy_years["end_year"] == year]["Document ID"])

        active_set = active_set.union(new_docs)
        active_set = active_set.difference(dropped_docs)

        active_totals.append(len(active_set))
        active_df = policy_years[policy_years["Document ID"].isin(active_set)]

        for cat in HEALTH_CATEGORIES:
            category_totals[cat].append(active_df[cat].sum())

    # Build plotting dataframe
    gdata = pd.DataFrame({"Year": YEARS})
    for cat in HEALTH_CATEGORIES:
        gdata[cat] = category_totals[cat]
    gdata["Total documents"] = active_totals

    # Plot
    X = np.arange(len(YEARS))
    gdata["StackSum"] = gdata[HEALTH_CATEGORIES].sum(axis=1)
    GLOBAL_Y_MAX = max(gdata["StackSum"].max(), gdata["Total documents"].max()) * 1.15

    fig, ax = plt.subplots(figsize=(15, 7))
    stack_arrays = [gdata[col].values for col in HEALTH_CATEGORIES]
    ax.stackplot(X, stack_arrays, colors=[CATEGORY_COLORS[c] for c in HEALTH_CATEGORIES], alpha=0.5, edgecolor="black", linewidth=0.3)
    line, = ax.plot(X, gdata["Total documents"], color="black", marker="o", linewidth=2.7, label="Total health-relevant documents")

    # Add text
    for xi, val in zip(X, gdata["Total documents"]):
        if val > 0:
            ax.text(xi, val + 0.03 * GLOBAL_Y_MAX, str(int(val)), ha="center", va="bottom", fontsize=8, fontweight="bold")

    # Highlight Paris Agreement
    if 2015 in YEARS:
        idx_2015 = YEARS.index(2015)
        ax.axvline(x=X[idx_2015], linestyle="--", linewidth=1.8, color="black")
        ax.text(X[idx_2015]+0.2, 0.9*GLOBAL_Y_MAX, "Paris Agreement", va="top", fontsize=10)

    ax.set_ylim(0, GLOBAL_Y_MAX)
    ax.set_ylabel("Legislative documents", fontsize=13)
    ax.set_title("Active Health-Relevant Legislative Documents Over Time in Europe", fontsize=13, fontweight="bold", loc="left")

    step = 5 if len(YEARS) > 20 else 2
    tick_years = YEARS[::step]
    tick_indices = [YEARS.index(y) for y in tick_years]
    ax.set_xticks(tick_indices)
    ax.set_xticklabels([str(int(y)) for y in tick_years])
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    bar_handles = [plt.Rectangle((0,0),1,1,color=CATEGORY_COLORS[c],alpha=0.5) for c in HEALTH_CATEGORIES]
    fig.legend(handles=bar_handles+[line], labels=[CATEGORY_LABELS[c] for c in HEALTH_CATEGORIES]+["Total health-relevant documents"], loc="upper left", bbox_to_anchor=(0.1,0.88), frameon=True)

    fig.text(0.01, 0.01, "Note: Analysis shown from {} onward.".format(plot_start_year), fontsize=11, style="italic")
    plt.tight_layout(rect=[0.03, 0.04, 0.97, 0.95])
    plt.savefig(output_path, dpi=300)
    plt.close()

# ----------------------------
# CLI
# ----------------------------
def main():
    parser = argparse.ArgumentParser(description="Health categories stackplot with timeline-based active documents")
    parser.add_argument("--annotation", required=True, help="CSV with health keyword annotations")
    parser.add_argument("--legis", required=True, help="CSV with legislative panel info (start/end years)")
    parser.add_argument("--output", required=True, help="Output file (PDF/PNG)")
    args = parser.parse_args()

    annotation_df = pd.read_csv(args.annotation)
    panel_df = pd.read_csv(args.legis)

    plot_health_stackplot(annotation_df, panel_df, args.output)

if __name__ == "__main__":
    main()