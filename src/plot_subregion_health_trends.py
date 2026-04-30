#!/usr/bin/env python3


import argparse
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RED  = "#C44E52"
BLUE = "#4C72B0"


def load_right_subregion_block(excel_path):
    raw = pd.read_excel(excel_path, sheet_name="EEA38 subregion", header=None)
    right_cols = [str(c).strip() for c in raw.iloc[1, 27:].tolist()]
    df = raw.iloc[2:, 27:].copy()
    df.columns = right_cols
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df[df["Year"].notna()].copy()
    for c in df.columns[2:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def load_not_eea(excel_path):
    raw = pd.read_excel(excel_path, sheet_name="EEA38 subregion", header=None)
    left_cols = [str(c).strip() for c in raw.iloc[1, :23].tolist()]
    df = raw.iloc[2:, :23].copy()
    df.columns = left_cols
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df[df["Year"].notna()].copy()
    for c in df.columns[2:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[df["EEA_subregion"] == "Not EEA"].copy()


def load_eu_sheet(excel_path):
    eu = pd.read_excel(excel_path, sheet_name="EU")
    eu.columns = [str(c).strip() for c in eu.columns]
    eu["Year"] = pd.to_numeric(eu["Year"], errors="coerce")
    return eu[eu["Year"].notna()].copy()


def plot_subregion_health_trends(excel_path, output_png, output_pdf):
    print("Loading data...")
    df       = load_right_subregion_block(excel_path)
    not_eea  = load_not_eea(excel_path)
    eu_df    = load_eu_sheet(excel_path)

    # Europe-wide total = right block (4 subregions) + Not EEA + EU
    sub_total   = df.groupby("Year")["Health-relevant documents"].sum().reset_index(name="sub")
    not_eea_tot = not_eea.groupby("Year")["Health-relevant documents"].sum().reset_index(name="not_eea")
    eu_annual   = eu_df[["Year","Health-relevant documents"]].rename(columns={"Health-relevant documents":"eu"})

    europe_total = sub_total.merge(not_eea_tot, on="Year").merge(eu_annual, on="Year")
    europe_total["Europe_total"] = europe_total["sub"] + europe_total["not_eea"] + europe_total["eu"]
    europe_total = europe_total[["Year","Europe_total"]]

    # Verify
    print("\nVerification (right + Not EEA + EU = combined EEA+UK+EU):")
    for yr in [2000, 2016, 2020, 2024, 2025]:
        tot = europe_total[europe_total["Year"]==yr]["Europe_total"].values[0]
        print(f"  {yr}: {tot}")

    df      = df.merge(europe_total, on="Year", how="left")
    not_eea = not_eea.merge(europe_total, on="Year", how="left")
    eu_df   = eu_df.merge(europe_total, on="Year", how="left")

    df["Health percent"]      = df["Health-relevant documents"]      / df["Europe_total"] * 100
    not_eea["Health percent"] = not_eea["Health-relevant documents"] / not_eea["Europe_total"] * 100
    eu_df["Health percent"]   = eu_df["Health-relevant documents"]   / eu_df["Europe_total"] * 100

    regions    = ["Eastern", "Northern", "Southern", "Western"]
    total_rows = len(regions) + 2   # 4 subregions + Not EEA + EU

    global_count_max = max(
        df["Health-relevant documents"].max(),
        not_eea["Health-relevant documents"].max(),
        eu_df["Health-relevant documents"].max(),
    ) * 1.15

    global_pct_max = max(
        df["Health percent"].max(),
        not_eea["Health percent"].max(),
        eu_df["Health percent"].max(),
    ) * 1.15

    fig, axes = plt.subplots(total_rows, 1, figsize=(13.5, 14.5), sharex=True)
    fig.subplots_adjust(hspace=0.20, top=0.91)

    legend_handles = []

    def draw_panel(ax, years, counts, pcts, title):
        nonlocal legend_handles
        line1, = ax.plot(years, counts, color=RED, linewidth=2.6,
                         marker="o", label="Health-relevant active families")
        ax.set_ylim(0, global_count_max)
        ax.set_ylabel("Count", fontsize=8.5)
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.margins(x=0.01)
        for x, y in zip(years, counts):
            ax.text(x, y + global_count_max * 0.010, str(int(y)),
                    ha="center", fontsize=6.2, color=RED)

        ax2 = ax.twinx()
        line2, = ax2.plot(years, pcts, color=BLUE, linewidth=2.0,
                          linestyle="--", marker="s",
                          label="Share of Europe-wide active health stock (%)")
        ax2.set_ylim(0, global_pct_max)
        ax2.set_ylabel("% Europe", fontsize=8.5)
        ax2.margins(x=0.01)
        for x, y in zip(years, pcts):
            ax2.text(x, y + global_pct_max * 0.010, f"{y:.1f}%",
                     ha="center", fontsize=5.8, color=BLUE)

        ax.set_title(title, fontsize=10.5, fontweight="bold", loc="left", pad=4)

        if 2016 in list(years):
            ax.axvline(2016, linestyle=":", linewidth=1.1, color="black")
            ax.text(2016 + 0.15, global_count_max * 0.88,
                    "Paris Agreement\nin force", fontsize=6.8,
                    ha="left", va="top")
        legend_handles = [line1, line2]

    # 4 EEA subregion panels
    for i, region in enumerate(regions):
        temp = df[df["EEA_subregion"] == region].sort_values("Year")
        draw_panel(axes[i],
                   temp["Year"].tolist(),
                   temp["Health-relevant documents"].tolist(),
                   temp["Health percent"].tolist(),
                   region)

    # Not EEA panel
    ne = not_eea.sort_values("Year")
    draw_panel(axes[-2],
               ne["Year"].tolist(),
               ne["Health-relevant documents"].tolist(),
               ne["Health percent"].tolist(),
               "Non-EEA Cooperating Countries")

    # EU panel
    eu_s = eu_df.sort_values("Year")
    draw_panel(axes[-1],
               eu_s["Year"].tolist(),
               eu_s["Health-relevant documents"].tolist(),
               eu_s["Health percent"].tolist(),
               "European Union")

    axes[-1].set_xlabel("Year", fontsize=10)

    fig.legend(
        handles=legend_handles,
        labels=[
            "Health-relevant active families",
            "Share of Europe-wide active health stock (%)",
        ],
        loc="upper center", ncol=2, frameon=True,
        bbox_to_anchor=(0.5, 0.945), fontsize=9,
    )

    fig.suptitle(
        "Regional and EU Trends in Active Health-Relevant Climate Legislative Families\n"
        "Absolute Count and Share of Europe-Wide Active Health Stock\n"
        "(Cooperating countries included within their respective EEA subregions)",
        fontsize=11, fontweight="bold", y=0.975,
    )

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.savefig(output_pdf, bbox_inches="tight")
    plt.close()
    print(f"\nSaved: {output_png}")
    print(f"Saved: {output_pdf}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--excel",      required=True)
    parser.add_argument("--output_png", required=True)
    parser.add_argument("--output_pdf", required=True)
    args = parser.parse_args()
    plot_subregion_health_trends(args.excel, args.output_png, args.output_pdf)


if __name__ == "__main__":
    main()
