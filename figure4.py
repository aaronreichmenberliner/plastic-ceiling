#!/usr/bin/env python3
"""
Figure 4: fate of ISS carbon.

Panels, in reading order:
  - Carbon fate by scenario (baseline vs aspirational), theoretical and empirical
  - Fate of recalcitrant plastics

Run `python figure4.py`.
"""

from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches
import common as C
from common import clean_common, display_formula, DPI, KG_C, read_fate_rows, read_fate_total, read_routing_rows, text_color

# Type sizes (pt) and panel canvas sizes (inches).
F4_TEXT, F4_TITLE, F4_SMALL = 9, 10, 8
F4_FATE_SIZE = (5.0, 4.0)
F4_PLASTICS_SIZE = (3.4, 4.0)


def color_or(colors: dict[str, str], key: str, fallback: str) -> str:
    value = colors.get(key, fallback)
    return value if value.startswith("#") else fallback

def hatch_or(patterns: dict[str, str], key: str) -> str:
    pattern = patterns.get(key, "solid")
    if "stripe" in pattern:
        return "///"
    if "dot" in pattern:
        return "..."
    if "cross" in pattern:
        return "xxx"
    return ""

def carbon_fate_colors(colors: dict[str, str]) -> dict[str, str]:
    return {
        "Biomass": "#4E9E4A",
        "CO₂e": C.substrate_color("CO2"),
        "Residual Solids": color_or(colors, "Residual Solids - Terminal", colors.get("Char", "#4D4D4D")),
        "Remaining Plastics": "#BDBDBD",
    }

def carbon_fate_hatches(patterns: dict[str, str]) -> dict[str, str]:
    return {
        "Biomass": hatch_or(patterns, "Biomass - Fixed"),
        "CO₂e": hatch_or(patterns, "CO2 - Recoverable"),
        "Residual Solids": hatch_or(patterns, "Residual Solids - Terminal"),
        "Remaining Plastics": hatch_or(patterns, "Remaining Plastics - Unconverted"),
    }

def plastic_fate_colors(colors: dict[str, str]) -> dict[str, str]:
    return {
        "CH$_4$": C.substrate_color("CH4"),
        "CO": C.substrate_color("CO"),
        "CO$_2$": C.substrate_color("CO2"),
        "Char": color_or(colors, "Char - Terminal", colors.get("Char", "#4D4D4D")),
        "Unrouted": color_or(colors, "Unrouted (incompatable / hazardous) - Unconverted", colors.get("Remaining Plastics", "#CCE3F0")),
    }

def plastic_fate_hatches(patterns: dict[str, str]) -> dict[str, str]:
    return {
        "CH$_4$": hatch_or(patterns, "CH4 (methanotroph feedstock)"),
        "CO": hatch_or(patterns, "CO (acetogen feedstock)"),
        "CO$_2$": hatch_or(patterns, "CO2 (autotroph / Sabatier pool)"),
        "Char": hatch_or(patterns, "Char - Terminal"),
        "Unrouted": hatch_or(patterns, "Unrouted (incompatable / hazardous) - Unconverted"),
    }

def add_percent_labels(ax, x, bottoms, values, total, color, threshold) -> None:
    for xi, bottom, value in zip(x, bottoms, values):
        pct = 100 * value / total
        if pct < threshold:
            continue
        ax.text(xi, bottom + value / 2, f"{pct:.1f}%", ha="center", va="center", fontsize=F4_SMALL, fontweight="bold", color=text_color(color))

def make_figure_4_carbon_fate(colors: dict[str, str], patterns: dict[str, str]) -> plt.Figure:
    fate_rows = read_fate_rows()
    total = read_fate_total()
    fate_colors = carbon_fate_colors(colors)
    fate_hatches = carbon_fate_hatches(patterns)
    order = [
        ("Biomass", "Biomass", "Fixed"),
        ("CO₂e", "CO$_2$e", "Recoverable"),   # first element is the workbook row label, verbatim
        ("Residual Solids", "Residual solids", "Terminal"),
        ("Remaining Plastics", "Remaining plastics", "Unconverted"),
    ]
    # Primary contrast is Baseline vs Aspirational; Theoretical/Empirical is the inner split.
    keys = ["baseline_theoretical", "baseline_empirical", "aspirational_theoretical", "aspirational_empirical"]
    labels = ["Baseline\nTheoretical", "Baseline\nEmpirical", "Aspirational\nTheoretical", "Aspirational\nEmpirical"]
    x = np.array([0.0, 0.78, 1.92, 2.70])
    width = 0.52

    fig, ax = plt.subplots(figsize=F4_FATE_SIZE, dpi=DPI, facecolor="none")
    clean_common(ax, F4_SMALL)

    bottoms = np.zeros(len(keys))
    for source_label, _display_label, _fate in order:
        values = np.array([float(fate_rows[source_label][key]) for key in keys])
        color = fate_colors[source_label]
        ax.bar(x, values, width=width, bottom=bottoms, color=color, edgecolor="white", linewidth=0.65, hatch=fate_hatches[source_label])
        add_percent_labels(ax, x, bottoms, values, total, color, threshold=4.0)
        bottoms += values

    terminal_values = np.array([float(fate_rows["Residual Solids"][key]) + float(fate_rows["Remaining Plastics"][key]) for key in keys])
    recoverable_bottom = np.array([float(fate_rows["Biomass"][key]) + float(fate_rows["CO₂e"][key]) for key in keys])
    for i, (xi, base, terminal) in enumerate(zip(x, recoverable_bottom, terminal_values)):
        if i in (0, 2):  # left (Theoretical) bar of each pair; terminal fraction matches the Empirical bar, so the marker is drawn once per pair
            continue
        pct = 100 * terminal / total
        ax.plot([xi + width / 2 + 0.045, xi + width / 2 + 0.045], [base, base + terminal], color="#B22222", lw=1.4)
        ax.scatter([xi + width / 2 + 0.045, xi + width / 2 + 0.045], [base, base + terminal], s=10, color="#B22222", zorder=5)
        ax.text(xi + width / 2 + 0.080, base + terminal / 2, f"{pct:.1f}%\nterminal", ha="left", va="center", fontsize=F4_SMALL, fontweight="bold", color="#B22222")

    ax.axhline(total, color="#48566A", lw=1.0, linestyle=(0, (3, 2)))
    ax.axvline(1.35, color="#B8BEC8", lw=1.0)
    ax.text(np.mean(x[:2]), total * 1.065, "Baseline", ha="center", va="bottom", fontsize=F4_TEXT, fontweight="bold", color="#48566A")
    ax.text(np.mean(x[2:]), total * 1.065, "Aspirational", ha="center", va="bottom", fontsize=F4_TEXT, fontweight="bold", color="#48566A")

    ax.set_ylabel(f"Carbon Fate ({KG_C}/yr)", fontsize=F4_TEXT)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=F4_SMALL)
    ax.set_xlim(-0.45, 3.65)
    ax.set_ylim(0, total * 1.18)
    ax.set_title("Fate of ISS Carbon", fontsize=F4_TITLE, fontweight="bold", loc="center", pad=8)

    handles = [patches.Patch(facecolor=fate_colors[source_label], edgecolor="none", hatch=fate_hatches[source_label], label=f"{display_label} - {fate}") for source_label, display_label, fate in order]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, frameon=False, fontsize=F4_SMALL)
    return fig

def make_figure_4_plastic_fate(colors: dict[str, str], patterns: dict[str, str]) -> plt.Figure:
    routing = read_routing_rows()
    recalc_total = routing["RecPlastics_to_Pyrolysis"][0] + routing["RecPlastics_remaining"][0]
    fate_colors = plastic_fate_colors(colors)
    fate_hatches = plastic_fate_hatches(patterns)
    order = [
        ("Char_C", "Char", "Terminal"),
        ("CH4_from_Pyro", "CH$_4$", "methanotroph feedstock"),
        ("CO_from_Pyro", "CO", "acetogen feedstock"),
        ("CO2_from_Pyro", "CO$_2$", "autotroph / Sabatier pool"),
        ("RecPlastics_remaining", "Unrouted", "Unconverted"),
    ]
    x = np.array([0.0, 0.82])
    width = 0.52
    fig, ax = plt.subplots(figsize=F4_PLASTICS_SIZE, dpi=DPI, facecolor="none")
    clean_common(ax, F4_SMALL)

    bottoms = np.zeros(2)
    for row_key, display_label, _fate in order:
        values = np.array(routing[row_key])
        color = fate_colors[display_label]
        ax.bar(x, values, width=width, bottom=bottoms, color=color, edgecolor="white", linewidth=0.65, hatch=fate_hatches[display_label])
        add_percent_labels(ax, x, bottoms, values, recalc_total, color, threshold=4.0)
        bottoms += values

    # Baseline pyrolysis/char segments are too thin to label in place; fan their percentages out to the left.
    seg_bottom = 0.0
    fan = []
    for row_key, display_label, _fate in order:
        val = float(routing[row_key][0])
        pct = 100 * val / recalc_total
        if display_label != "Unrouted" and pct < 4.0:
            fan.append((seg_bottom + val / 2, pct, fate_colors[display_label]))
        seg_bottom += val
    if fan:
        fan.sort()
        fan_ys = np.linspace(recalc_total * 0.05, recalc_total * 0.38, len(fan))
        for (cy, pct, col), fy in zip(fan, fan_ys):
            ax.annotate(f"{pct:.1f}%", xy=(x[0] - width / 2, cy), xytext=(x[0] - 0.55, fy), ha="right", va="center", fontsize=F4_SMALL, fontweight="bold", color=col, annotation_clip=False, arrowprops=dict(arrowstyle="-", color="#9A9A9A", lw=0.6, shrinkA=1, shrinkB=1))

    routed = np.array(routing["RecPlastics_to_Pyrolysis"])
    routed_pct = 100 * routed / recalc_total
    for xi, total_height, pct in zip(x, bottoms, routed_pct):
        ax.text(xi, total_height + recalc_total * 0.025, f"{pct:.0f}% routed\nto pyrolysis", ha="center", va="bottom", fontsize=F4_SMALL, fontweight="bold", color="#48566A", linespacing=1.05)

    ax.axhline(recalc_total, color="#48566A", lw=1.0, linestyle=(0, (3, 2)))

    ax.set_ylabel(f"Recalcitrant-Plastic Carbon ({KG_C}/yr)", fontsize=F4_TEXT)
    ax.set_xticks(x)
    ax.set_xticklabels(["Baseline", "Aspirational"], fontsize=F4_TEXT)
    ax.set_xlim(-0.85, 1.67)
    ax.set_ylim(0, recalc_total * 1.18)
    ax.set_title("Fate of Recalcitrant Plastics", fontsize=F4_TITLE, fontweight="bold", loc="center", pad=8)

    fate_of = {dl: fate for _rk, dl, fate in order}
    legend_order = ["CO$_2$", "Char", "Unrouted", "CO", "CH$_4$"]  # legend fills column-first: col1 CO2/Char/Unrouted, col2 CO/CH4
    handles = [patches.Patch(facecolor=fate_colors[dl], edgecolor="none", hatch=fate_hatches[dl], label=f"{display_formula(dl)} - {fate_of[dl]}") for dl in legend_order]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, frameon=False, fontsize=F4_SMALL)
    return fig


def build() -> None:
    C.check_inputs([C.WORKBOOK, C.COLORS], 4)
    colors = C.read_color_key(C.COLORS)
    patterns = C.read_pattern_key(C.COLORS)
    canvas = C.Canvas(3000, 1800)
    left = C.render(make_figure_4_carbon_fate(colors, patterns), 0.03)
    right = C.render(make_figure_4_plastic_fate(colors, patterns), 0.03)
    # The two panels are given a common scale, by splitting the available width in proportion to what each
    # actually rendered to. Fixed boxes would scale each panel to its own box and the panels would then differ
    # by a few per cent, which is enough to throw their titles and their legends out of line with each other.
    x0, x1, gap, top, height = 45, 2950, 55, 40, 1700
    (w_left, _h_left), (w_right, _h_right) = C.svg_size(left), C.svg_size(right)
    scale = (x1 - x0 - gap) / (w_left + w_right)
    box_left = round(w_left * scale)
    C.place(canvas, left, (x0, top, box_left, height))
    C.place(canvas, right, (x0 + box_left + gap, top, round(w_right * scale), height))
    C.save_figure(canvas, 4, width_mm=180)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    C.add_path_arguments(parser, "workbook", "colors")
    args = parser.parse_args()
    C.configure(WORKBOOK=args.workbook, COLORS=args.colors, OUTPUTS=args.output_dir)
    C.apply_rcparams()
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())