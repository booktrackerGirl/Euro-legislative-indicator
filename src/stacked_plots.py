"""
Lancet Countdown indicator plots
Plot 3: 100% stacked bar — health category composition by period
Plot 6: Dual-axis line — absolute health-relevant docs vs % of total climate docs

Usage:
    python ./src/stacked_plots.py --input ./outputs/dataframes/health_counts.xlsx
    python ./src/stacked_plots.py --input ./outputs/dataframes/health_counts.xlsx --plot 3
    python ./src/stacked_plots.py --input ./outputs/dataframes/health_counts.xlsx --plot 6
    python ./src/stacked_plots.py --input ./outputs/dataframes/health_counts.xlsx --output ./outputs/figures/
"""

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd


# ── Lancet-style palette ────────────────────────────────────────────────────
LANCET_RED   = "#C0392B"
PERIOD_COLS  = ["#1A4A6E", "#2E7DBF"]   # pre-Paris deep, post-Paris mid blue

# Health category colours (14 categories, muted qualitative)
CAT_COLORS = [
    "#1A4A6E", "#2E7DBF", "#5BA3D9", "#A8C8E8",
    "#C0392B", "#E07060", "#F4A58A",
    "#2D6A4F", "#52B788", "#95D5B2",
    "#6B4E8F", "#B39DDB",
    "#E6A817", "#F5D680",
]

FONT_FAMILY = "DejaVu Sans"

# Categories to include (drop near-zero ones for readability)
CATS_ORDERED = [
    "General Health & Services",
    "Mental Health",
    "Communicable Diseases",
    "Injury & Trauma",
    "Mortality & Morbidity",
    "Environmental Health",
    "Food & Waterborne Illnesses",
    "Substance Use",
    "Nutrition",
    "Non-Communicable Diseases",
    "Pathogens & Microbiology",
    "Maternal & Child Health",
    "Vector-borne & Zoonotic Diseases",
    "Climate & Environment",
]

PERIODS = {
    "Pre-Paris\n(2000–2015)": (2000, 2015),
    "Post-Paris\n(2016–2025)": (2016, 2025),
}

# ── data loading ────────────────────────────────────────────────────────────

def load_data(path: str) -> pd.DataFrame:
    """Combine Europe (EEA+UK) and EU sheets — EU legislation is tracked separately."""
    df_eea = pd.read_excel(path, sheet_name="Europe (EEA+ UK)")
    df_eu  = pd.read_excel(path, sheet_name="EU")

    # Sum all columns except Year
    sum_cols = [c for c in df_eea.select_dtypes(include="number").columns if c != "Year"]
    df_combined = df_eea.copy()
    df_combined[sum_cols] = df_eea[sum_cols].values + df_eu[sum_cols].values
    df_combined["Year"] = df_eea["Year"].astype(int)
    return df_combined


# ── Plot 3 ──────────────────────────────────────────────────────────────────

def plot3(df: pd.DataFrame, out_dir: Path):
    """100% stacked bar: health category composition across three periods."""

    # Compute period shares
    records = {}
    for label, (y1, y2) in PERIODS.items():
        sub = df[(df["Year"] >= y1) & (df["Year"] <= y2)]
        totals = {c: sub[c].sum() for c in CATS_ORDERED}
        grand = sum(totals.values())
        records[label] = {c: v / grand * 100 for c, v in totals.items()}

    period_labels = list(PERIODS.keys())
    bar_data = {c: [records[p][c] for p in period_labels] for c in CATS_ORDERED}

    # Drop categories that are < 0.8% across all periods (too small to label)
    n_periods = len(PERIODS)
    visible_cats = [c for c in CATS_ORDERED
                    if any(bar_data[c][i] >= 0.8 for i in range(n_periods))]

    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    x = np.arange(len(period_labels))
    bar_w = 0.52
    bottoms = np.zeros(len(period_labels))

    for idx, cat in enumerate(visible_cats):
        vals = np.array(bar_data[cat])
        color = CAT_COLORS[idx % len(CAT_COLORS)]
        bars = ax.bar(x, vals, bar_w, bottom=bottoms, color=color,
                      label=cat, zorder=3)

        # Label inside bar if segment ≥ 3%
        for xi, (v, b) in enumerate(zip(vals, bottoms)):
            if v >= 3.0:
                ax.text(xi, b + v / 2, f"{v:.0f}%",
                        ha="center", va="center",
                        fontsize=7.5, color="white", fontweight="bold",
                        fontfamily=FONT_FAMILY)
        bottoms += vals

    # Axes formatting
    ax.set_xticks(x)
    ax.set_xticklabels(period_labels, fontsize=11, fontfamily=FONT_FAMILY)
    ax.set_ylabel("Share of health-relevant legislation (%)",
                  fontsize=10, fontfamily=FONT_FAMILY)
    ax.set_ylim(0, 105)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.tick_params(axis="y", labelsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#CCCCCC")
    ax.yaxis.grid(True, color="#EEEEEE", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    # Title & note
    ax.set_title(
        "Health category composition of climate-related legislation\nacross Europe, by period (2000–2025)",
        fontsize=12, fontweight="bold", fontfamily=FONT_FAMILY,
        loc="left", pad=12,
    )
    fig.text(0.01, -0.02,
             "Source: Climate Change Laws of the World dataset. Filtered to include EEA38+UK+EU legislative documents.",
             fontsize=7.5, color="#888888", fontfamily=FONT_FAMILY)

    # Legend outside
    legend = ax.legend(
        loc="upper left", bbox_to_anchor=(1.02, 1),
        fontsize=8, frameon=False,
        title="Health category", title_fontsize=8.5,
    )

    plt.tight_layout()
    out_path = out_dir / "health_category_composition.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ Saved: {out_path}")
    return out_path


# ── Plot 6 ──────────────────────────────────────────────────────────────────

def plot6(df: pd.DataFrame, out_dir: Path):
    """Dual-axis line: absolute health-relevant docs vs % of total climate docs."""

    years  = df["Year"].values
    total  = df["Total documents"].values
    health = df["Health-relevant documents"].values
    ratio  = health / total * 100

    fig, ax1 = plt.subplots(figsize=(10, 5.5))
    fig.patch.set_facecolor("white")
    ax1.set_facecolor("white")

    # Left axis — absolute count
    color_abs = "#1A4A6E"
    ax1.plot(years, health, color=color_abs, linewidth=2.2,
             marker="o", markersize=4, zorder=4, label="Health-relevant documents (n)")
    ax1.fill_between(years, health, alpha=0.10, color=color_abs, zorder=2)
    ax1.set_ylabel("Number of health-relevant documents",
                   fontsize=10, color=color_abs, fontfamily=FONT_FAMILY)
    ax1.tick_params(axis="y", labelcolor=color_abs, labelsize=9)
    ax1.set_ylim(0, max(health) * 1.25)

    # Right axis — ratio
    ax2 = ax1.twinx()
    color_ratio = LANCET_RED
    ax2.plot(years, ratio, color=color_ratio, linewidth=2.2, linestyle="--",
             marker="s", markersize=4, zorder=4, label="Health-relevant (% of total)")
    ax2.set_ylabel("Health-relevant as % of total climate documents",
                   fontsize=10, color=color_ratio, fontfamily=FONT_FAMILY)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax2.tick_params(axis="y", labelcolor=color_ratio, labelsize=9)
    ax2.set_ylim(0, max(ratio) * 1.35)

    # Annotate Paris Agreement (2016)
    ax1.axvline(2016, color="#888888", linewidth=1, linestyle=":", zorder=3)
    ax1.text(2016.3, max(health) * 1.15, "Paris Agreement\nin force (2016)",
             fontsize=7.5, color="#666666", fontfamily=FONT_FAMILY, va="top")

    # Shared x-axis
    ax1.set_xlim(years[0] - 0.5, years[-1] + 0.5)
    ax1.set_xticks(years[::2])
    ax1.tick_params(axis="x", labelsize=9)
    ax1.spines[["top"]].set_visible(False)
    ax2.spines[["top"]].set_visible(False)
    ax1.spines[["left", "bottom"]].set_color("#CCCCCC")
    ax2.spines[["right"]].set_color("#CCCCCC")
    ax1.yaxis.grid(True, color="#EEEEEE", linewidth=0.8, zorder=0)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               loc="upper left", fontsize=9, frameon=False)

    ax1.set_title(
        "Health mainstreaming in climate legislation across Europe (2000–2025)\n"
        "Absolute count and share of total climate-related legislative documents",
        fontsize=12, fontweight="bold", fontfamily=FONT_FAMILY,
        loc="left", pad=12,
    )
    fig.text(0.01, -0.02,
             "Source: Climate Change Laws of the World dataset. Filtered to include EEA38+UK+EU legislative documents.",
             fontsize=7.5, color="#888888", fontfamily=FONT_FAMILY)

    plt.tight_layout()
    out_path = out_dir / "health_ratio_over_time.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ Saved: {out_path}")
    return out_path


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate Lancet Countdown indicator plots (3 and/or 6).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to health_counts Excel file (.xlsx)",
    )
    parser.add_argument(
        "--plot", "-p", choices=["3", "6", "both"], default="both",
        help="Which plot to generate: 3, 6, or both (default: both)",
    )
    parser.add_argument(
        "--output", "-o", default=".",
        help="Output directory for saved figures (default: current directory)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from: {input_path}")
    df = load_data(str(input_path))
    print(f"  Years: {df['Year'].min()}–{df['Year'].max()}, rows: {len(df)}")

    generated = []
    if args.plot in ("3", "both"):
        print("\nGenerating Plot 3 — health category composition (100% stacked bar)…")
        generated.append(plot3(df, out_dir))

    if args.plot in ("6", "both"):
        print("\nGenerating Plot 6 — health ratio over time (dual-axis line)…")
        generated.append(plot6(df, out_dir))

    print(f"\nDone. {len(generated)} figure(s) saved to: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
