#!/usr/bin/env python3

import argparse
import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------
# LOAD LEFT BLOCK OF EEA38 SUBREGION SHEET
# ---------------------------------------------------
def load_left_subregion_block(excel_path):

    raw = pd.read_excel(
        excel_path,
        sheet_name="EEA38 subregion",
        header=1
    )

    keep_cols = []
    for c in raw.columns:
        if str(c).startswith("Unnamed"):
            break
        keep_cols.append(c)

    df = raw[keep_cols].copy()
    df.columns = [str(c).strip() for c in df.columns]

    df = df[df["Year"].notna()]
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df[df["Year"].notna()]

    df = df[df["EEA_subregion"].astype(str).str.strip() != "Not EEA"]

    return df


# ---------------------------------------------------
# LOAD EU SHEET
# ---------------------------------------------------
def load_eu_sheet(excel_path):

    eu = pd.read_excel(excel_path, sheet_name="EU")
    eu.columns = [str(c).strip() for c in eu.columns]

    eu = eu[eu["Year"].notna()]
    eu["Year"] = pd.to_numeric(eu["Year"], errors="coerce")
    eu = eu[eu["Year"].notna()]

    return eu


# ---------------------------------------------------
# MAIN PLOT
# ---------------------------------------------------
def plot_subregion_health_trends(excel_path, output_png, output_pdf):

    print("Loading subregional trend data...")
    df = load_left_subregion_block(excel_path)
    eu_df = load_eu_sheet(excel_path)

    # ---------------------------------------------------
    # EUROPE-WIDE ACTIVE HEALTH STOCK PER YEAR
    # ---------------------------------------------------
    europe_total = (
        df.groupby("Year")["Health-relevant documents"]
        .sum()
        .reset_index(name="Europe_total_health")
    )

    df = df.merge(europe_total, on="Year", how="left")
    eu_df = eu_df.merge(europe_total, on="Year", how="left")

    # ---------------------------------------------------
    # REGIONAL SHARE OF EUROPE TOTAL
    # ---------------------------------------------------
    df["Health percent"] = (
        df["Health-relevant documents"] / df["Europe_total_health"] * 100
    )

    eu_df["Health percent"] = (
        eu_df["Health-relevant documents"] / eu_df["Europe_total_health"] * 100
    )

    regions = sorted(df["EEA_subregion"].dropna().unique())
    total_rows = len(regions) + 1   # + EU row

    global_count_max = max(
        df["Health-relevant documents"].max(),
        eu_df["Health-relevant documents"].max()
    ) * 1.15

    global_pct_max = max(
        df["Health percent"].max(),
        eu_df["Health percent"].max()
    ) * 1.15

    fig, axes = plt.subplots(
        total_rows,
        1,
        figsize=(13.5, 10.4),
        sharex=True
    )

    fig.subplots_adjust(hspace=0.20, top=0.91)

    if total_rows == 1:
        axes = [axes]

    legend_handles = None

    # ---------------------------------------------------
    # PLOT EACH EEA SUBREGION
    # ---------------------------------------------------
    for i, region in enumerate(regions):

        ax = axes[i]

        temp = df[df["EEA_subregion"] == region].copy()
        temp = temp.sort_values("Year")

        line1, = ax.plot(
            temp["Year"],
            temp["Health-relevant documents"],
            color="#C44E52",
            linewidth=2.6,
            marker="o",
            label="Health-relevant families"
        )

        ax.set_ylim(0, global_count_max)
        ax.set_ylabel("Count", fontsize=8.5)
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.margins(x=0.01)

        for x, y in zip(temp["Year"], temp["Health-relevant documents"]):
            ax.text(x, y + global_count_max*0.010, str(int(y)),
                    ha="center", fontsize=6.2, color="#C44E52")

        ax2 = ax.twinx()

        line2, = ax2.plot(
            temp["Year"],
            temp["Health percent"],
            color="#4C72B0",
            linewidth=2.0,
            linestyle="--",
            marker="s",
            label="Regional share of Europe (%)"
        )

        ax2.set_ylim(0, global_pct_max)
        ax2.set_ylabel("% Europe", fontsize=8.5)
        ax2.margins(x=0.01)

        for x, y in zip(temp["Year"], temp["Health percent"]):
            ax2.text(x, y + global_pct_max*0.010, f"{y:.1f}%",
                     ha="center", fontsize=5.8, color="#4C72B0")

        ax.set_title(region, fontsize=10.5, fontweight="bold", loc="left", pad=4)

        if 2016 in temp["Year"].values:
            ax.axvline(2016, linestyle=":", linewidth=1.1, color="black")
            ax.text(
                2016 + 0.15,
                global_count_max * 0.88,
                "Paris Agreement\nin force",
                fontsize=6.8,
                ha="left",
                va="top"
            )

        legend_handles = [line1, line2]

    # ---------------------------------------------------
    # PLOT EU ON BOTTOM ROW
    # ---------------------------------------------------
    ax = axes[-1]
    eu_df = eu_df.sort_values("Year")

    line1, = ax.plot(
        eu_df["Year"],
        eu_df["Health-relevant documents"],
        color="#C44E52",
        linewidth=2.6,
        marker="o"
    )

    ax.set_ylim(0, global_count_max)
    ax.set_ylabel("Count", fontsize=8.5)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.margins(x=0.01)

    for x, y in zip(eu_df["Year"], eu_df["Health-relevant documents"]):
        ax.text(x, y + global_count_max*0.010, str(int(y)),
                ha="center", fontsize=6.2, color="#C44E52")

    ax2 = ax.twinx()

    line2, = ax2.plot(
        eu_df["Year"],
        eu_df["Health percent"],
        color="#4C72B0",
        linewidth=2.0,
        linestyle="--",
        marker="s"
    )

    ax2.set_ylim(0, global_pct_max)
    ax2.set_ylabel("% Europe", fontsize=8.5)
    ax2.margins(x=0.01)

    for x, y in zip(eu_df["Year"], eu_df["Health percent"]):
        ax2.text(x, y + global_pct_max*0.010, f"{y:.1f}%",
                 ha="center", fontsize=5.8, color="#4C72B0")

    ax.set_title("European Union", fontsize=10.5, fontweight="bold", loc="left", pad=4)

    if 2016 in eu_df["Year"].values:
        ax.axvline(2016, linestyle=":", linewidth=1.1, color="black")
        ax.text(
            2016 + 0.15,
            global_count_max * 0.88,
            "Paris Agreement\nin force",
            fontsize=6.8,
            ha="left",
            va="top"
        )

    # ---------------------------------------------------
    # GLOBAL LABELS
    # ---------------------------------------------------
    axes[-1].set_xlabel("Year", fontsize=10)

    fig.legend(
        handles=legend_handles,
        labels=[
            "Health-relevant active families",
            "Share of Europe-wide active health stock (%)"
        ],
        loc="upper center",
        ncol=2,
        frameon=True,
        bbox_to_anchor=(0.5, 0.84),
        fontsize=9
    )

    fig.suptitle(
        "Regional and EU Trends in Active Health-Relevant Climate Legislative Families\nAbsolute Count and Share of Europe-Wide Active Health Stock",
        fontsize=12,
        fontweight="bold",
        y=0.885
    )

    plt.tight_layout(rect=[0, 0, 1, 0.89])

    plt.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.savefig(output_pdf, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output_png}")
    print(f"Saved: {output_pdf}")


# ---------------------------------------------------
# CLI
# ---------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--excel", required=True)
    parser.add_argument("--output_png", required=True)
    parser.add_argument("--output_pdf", required=True)

    args = parser.parse_args()

    plot_subregion_health_trends(
        args.excel,
        args.output_png,
        args.output_pdf
    )


if __name__ == "__main__":
    main()