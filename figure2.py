#!/usr/bin/env python3
"""
Figure 2: carbon routing.

Panels, in reading order:
  - Authored BPSF flowchart (SVG)
  - Annual carbon routed to bioprocessing, baseline vs aspirational

Run `python figure2.py`.
"""

from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches
from matplotlib.legend_handler import HandlerTuple
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
import common as C
from common import DPI, KG_C, organism_hatch, parse_route_label, process_legend_items, read_iss_input_carbon, read_scenario_carbon, substrate_legend_items

# Type sizes (pt) and panel canvas size (inches).
F2_TEXT, F2_TITLE, F2_SMALL = 9, 10, 8
F2_ROUTED_SIZE = (5.0, 4.0)

# Left-panel title. The authored flowchart fills its own viewBox edge to edge, so there is no room
# inside the artwork for a title; it is drawn onto the canvas instead, in canvas pixels. F2_TITLE_BAND
# is the strip reserved for it above the flowchart, and the right panel grows by the same amount so
# both columns still end level. F2_TITLE_SIZE is tuned to match the right panel's matplotlib title.
F2_LEFT_TITLE = "Carbon routing network"
F2_TITLE_BAND = 90
F2_TITLE_SIZE = 51.7
F2_TITLE_BASELINE = 99.0


def _f2_alluvial(ax, x0, x1, y0_low, y0_high, y1_low, y1_high, color) -> None:
    curve = 0.34 * (x1 - x0)
    verts = [
        (x0, y0_high),
        (x0 + curve, y0_high),
        (x1 - curve, y1_high),
        (x1, y1_high),
        (x1, y1_low),
        (x1 - curve, y1_low),
        (x0 + curve, y0_low),
        (x0, y0_low),
        (x0, y0_high),
    ]
    codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4, MplPath.LINETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4, MplPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=color, edgecolor=(1, 1, 1, 0.88), lw=0.35, alpha=0.48, zorder=1))

def _curly_brace(ax, x_arm: float, x_tip: float, y0: float, y1: float, color: str = "#48566A", lw: float = 1.0) -> None:
    """Curly brace spanning y0..y1 with its arms at x_arm and its tip at x_tip. Two cubic Beziers per half, both ends with horizontal tangents, so the shape reads as { or } depending on the sign of x_tip - x_arm."""
    dx = x_tip - x_arm
    mid = 0.5 * (y0 + y1)
    for y_end in (y0, y1):
        verts = [(x_arm, y_end), (x_arm + 0.55 * dx, y_end), (x_arm + 0.55 * dx, mid), (x_tip, mid)]
        codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4]
        ax.add_patch(PathPatch(MplPath(verts, codes), facecolor="none", edgecolor=color, lw=lw, clip_on=False, zorder=4))

def make_figure_2_routed_carbon(colors: dict[str, str]) -> plt.Figure:
    labels, conservative, aggressive = read_scenario_carbon()
    total_input = read_iss_input_carbon()
    fig, ax = plt.subplots(figsize=F2_ROUTED_SIZE, dpi=DPI, facecolor="none")
    ax.set_facecolor("none")
    ax.grid(False)

    x_left, x_right = 0.18, 1.18
    bar_width = 0.18
    left_bottom = right_bottom = 0.0
    segments = []
    for label, cons, aggr in zip(labels, conservative, aggressive):
        substrate, organism = parse_route_label(label)
        color = C.route_color(substrate, organism)
        hatch = organism_hatch(organism)
        segments.append((color, hatch, (left_bottom, left_bottom + cons), (right_bottom, right_bottom + aggr), cons, aggr))
        left_bottom += cons
        right_bottom += aggr

    for color, hatch, left_segment, right_segment, cons, aggr in segments:
        if cons > 0 or aggr > 0:
            _f2_alluvial(ax, x_left + bar_width / 2, x_right - bar_width / 2, left_segment[0], left_segment[1], right_segment[0], right_segment[1], color)

    for color, hatch, left_segment, right_segment, cons, aggr in segments:
        if cons > 0:
            ax.add_patch(patches.Rectangle((x_left - bar_width / 2, left_segment[0]), bar_width, cons, facecolor=color, edgecolor="white", lw=0.6, hatch=hatch, zorder=3))
        if aggr > 0:
            ax.add_patch(patches.Rectangle((x_right - bar_width / 2, right_segment[0]), bar_width, aggr, facecolor=color, edgecolor="white", lw=0.6, hatch=hatch, zorder=3))

    totals = np.array([left_bottom, right_bottom])
    ax.axhline(total_input, xmin=0.0, xmax=0.75, color="#48566A", lw=1.0, linestyle=(0, (3, 2)))
    # Sits on the rule rather than centred on it, so it clears the aspirational bar's total, which reaches close beneath.
    ax.text(0.02, total_input + 55, "Total ISS carbon input", ha="left", va="center", fontsize=F2_SMALL, color="#48566A")

    for xi, total in zip([x_left, x_right], totals):
        ax.text(xi, total + 110, f"{total:,.0f}\n{KG_C}/yr", ha="center", va="bottom", fontsize=F2_TEXT, fontweight="bold")

    # Braces span the full plotted stack (0 to the routed total), so they annotate the bar as a whole rather than pointing at one segment.
    left_pct = 100 * totals[0] / total_input
    right_pct = 100 * totals[1] / total_input
    _curly_brace(ax, x_left - bar_width / 2 - 0.02, x_left - 0.16, 0.0, totals[0])
    ax.text(x_left - 0.21, totals[0] * 0.5, f"{left_pct:.0f}%\nrouted", ha="right", va="center", fontsize=F2_TITLE, fontweight="bold", color="black")
    _curly_brace(ax, x_right + bar_width / 2 + 0.02, x_right + 0.16, 0.0, totals[1])
    ax.text(x_right + 0.21, totals[1] * 0.5, f"{right_pct:.0f}%\nrouted", ha="left", va="center", fontsize=F2_TITLE, fontweight="bold", color="black")

    ax.text(0.108, 1.075, "Annual carbon routed to bioprocessing", transform=ax.transAxes, ha="left", va="baseline", fontsize=F2_TITLE, fontweight="bold")
    ax.set_ylabel(f"Carbon routed ({KG_C}/yr)", fontsize=F2_TITLE)
    ax.set_xticks([x_left, x_right])
    ax.set_xticklabels(["Baseline\nrouting", "Aspirational\nrouting"], fontsize=F2_TEXT, fontweight="bold")
    ax.set_ylim(0, total_input * 1.18)
    ax.set_xlim(-0.52, 1.88)
    ax.tick_params(axis="y", labelsize=F2_TEXT)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#9A9A9A")
    ax.spines["bottom"].set_color("#9A9A9A")

    substrate_handles, substrate_labels = [], []
    for substrate, label in substrate_legend_items():
        substrate_labels.append(label)
        if substrate == "CO2":
            substrate_handles.append((patches.Patch(facecolor=C.CO2_LIGHT, edgecolor="none"), patches.Patch(facecolor=C.CO2_MEDIUM, edgecolor="none")))
        else:
            substrate_handles.append(patches.Patch(facecolor=C.substrate_color(substrate), edgecolor="none"))
    f2_process_legend = process_legend_items()
    organism_handles = [patches.Patch(facecolor="white", edgecolor="#48566A", hatch=hatch, label=label) for label, hatch in f2_process_legend]
    first_legend = ax.legend(handles=substrate_handles, labels=substrate_labels, title="Substrate", loc="upper left", bbox_to_anchor=(0.93, 1.04), frameon=False, fontsize=8, title_fontsize=8, handlelength=1.6, handleheight=1.2, handletextpad=0.5, handler_map={tuple: HandlerTuple(ndivide=None, pad=0.0)})
    first_legend.get_title().set_fontweight("semibold")
    ax.add_artist(first_legend)
    # Larger handles: at handlelength 1.0 the dotted photo/heterotroph fill could not fit enough dots to read as a pattern.
    second_legend = ax.legend(handles=organism_handles, title="Organism / Process", loc="upper left", bbox_to_anchor=(0.93, 0.50), frameon=False, fontsize=8, title_fontsize=8, handlelength=1.6, handleheight=1.2, handletextpad=0.5)
    second_legend.get_title().set_fontweight("semibold")
    return fig


def build() -> None:
    C.check_inputs([C.WORKBOOK, C.COLORS, C.FIG2], 2)
    colors = C.read_color_key(C.COLORS)
    # Two panels: the authored SVG (aspect 1.155) and the routed-carbon plot. The flowchart is inset from
    # the top by F2_TITLE_BAND to clear its canvas-drawn title; the routed-carbon panel carries its own
    # title inside the matplotlib figure, so it takes the band as extra height and the two end level.
    canvas = C.Canvas(3700, 1400 + F2_TITLE_BAND)
    left_box = (45, 40 + F2_TITLE_BAND, 1560, 1320)
    C.place(canvas, C.render_svg(C.FIG2), left_box)
    C.place(canvas, C.render(make_figure_2_routed_carbon(colors), 0.03), (1680, 40, 1960, 1320 + F2_TITLE_BAND))
    C.text(canvas, F2_LEFT_TITLE, (left_box[0] + left_box[2] / 2, F2_TITLE_BASELINE), F2_TITLE_SIZE, weight="bold")
    C.save_figure(canvas, 2, width_mm=180)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    C.add_path_arguments(parser, "workbook", "colors", "fig2")
    args = parser.parse_args()
    C.configure(WORKBOOK=args.workbook, COLORS=args.colors, FIG2=args.fig2, OUTPUTS=args.output_dir)
    C.apply_rcparams()
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())