#!/usr/bin/env python3
"""Supplementary figure: "Reactor volume distribution by bioprocess" as a single 2x2 matrix of pies.

Rows are the sizing model (Theoretical, Empirical) and columns the routing scenario (Baseline, Aspirational), so each row pairs the two scenarios for one model and each column pairs the two models for one scenario, under a single route key. Every pie is drawn on ONE global area scale: radius is proportional to sqrt(total reactor volume) measured against the largest of all four totals, so areas are comparable across the whole matrix rather than only within a model. Slices are coloured by substrate using the shared Figure 3 palette and carry their route letter (A-K, workbook row order), so mechanisms sharing a substrate colour stay distinguishable. Volumes are read as-is from the 'Scenarios' sheet of the bioprocess sizing workbook; this script only visualizes them.

Laid out in millimetres at 180 mm wide and drawn at its printed size, so the type constants below are the printed sizes. Run `python figure_si_reactor_volumes.py`.
"""
from __future__ import annotations

import argparse
import math

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from matplotlib.patches import Patch, Wedge

import common as C
from figure3 import route_display

MODELS = ["Theoretical", "Empirical"]
SCENARIO_ORDER = ["Baseline", "Aspirational"]
# Matrix orientation. "model" puts the two sizing models on separate rows, stacking the two figures this replaces; "scenario" transposes to models-as-columns, which is shorter and fills the 180 mm width better because it sets the two largest pies side by side instead of one above the other. Nothing else changes.
MATRIX_ROWS = "model"
# Scenarios-sheet reactor-volume columns per model (header rows 3-4 of that sheet).
VOLUME_COLUMNS = {
    "Theoretical": {"Baseline": "E", "Aspirational": "J"},
    "Empirical": {"Baseline": "F", "Aspirational": "K"},
}
DATA_ROWS = range(5, 16)  # A5:A15 hold the 11 mechanisms, one per row

# Layout, all in millimetres. The axes fills the whole figure at equal aspect with 1 data unit == 1 mm,
# so every constant below is a real printed dimension.
FIG_W_MM = 180.0
MARGIN = 7.0
R_MAX_MM = 39.0  # radius of the largest pie; every other radius follows from the global area scale
PIE_GAP = 24.0  # clear space between neighbouring pies, edge to edge; leader labels live in this gap
ROW_LABEL_W = 21.0  # gutter on the left holding the model names
COL_HEADER_H = 8.0
TOTAL_GAP = 3.2  # pie edge to its total annotation
TOTAL_H = 4.0
NOTE_BAND = 12.0  # band between the two rows of pies that carries the scale note

# Type sizes (pt).
HEADER, LEG, LEG_TITLE, NOTE_FS, TOTAL_FS = 9.0, 6.5, 7.0, 8.0, 7.0
PIE_LABEL_MAX, PIE_LABEL_MIN = 8.0, 6.0
PIE_LABEL_FLOOR = 5.0  # a label may shrink this far to fit its own wedge; 5 pt is the journal minimum

LEGEND_NCOL = 3
# Height reserved for the route key, from its own content: one row per wrapped group of entries plus the
# title and the frame. The trailing TOTAL_GAP keeps the key at least as far from the totals printed under
# the pies as those totals sit from the pies themselves.
ROUTE_LEGEND_H = (math.ceil(len(DATA_ROWS) / LEGEND_NCOL) * LEG * 1.62 + LEG_TITLE * 1.9) * 25.4 / 72.0 + 3.0 + TOTAL_GAP

LABEL_R = 0.66        # radial position of a label that sits inside its wedge, as a fraction of the radius
LEAD_OUT = 3.2        # clear distance from the rim to a leader label, mm
LEADER_ROOM = 10.0    # room a leader label needs beyond the rim, mm; reserved so the block still centres
# A wedge below this share is a sliver a reader cannot pick out even when it is pointed at, so it is left
# unlabelled rather than adding a leader to something invisible. Everything above it is labelled, inside the
# wedge where the arc is wide enough and on a leader where it is not.
MIN_VISIBLE_PCT = 0.3


def matrix_axes():
    """Return (row keys, column keys, cell lookup) for the chosen orientation. The cell lookup maps a (row, column) pair back to the (model, scenario) key the volumes are stored under."""
    if MATRIX_ROWS == "model":
        return MODELS, SCENARIO_ORDER, (lambda row, col: (row, col)), "Model", "Scenario"
    return SCENARIO_ORDER, MODELS, (lambda row, col: (col, row)), "Scenario", "Model"


def mechanism_colors():
    """Per-mechanism fill = its substrate colour (shared Figure 3 palette), in workbook row order."""
    return [C.route_color(str(r["substrate"]), str(r["mechanism"])) for r in C.read_scenario_rows()]


def read_all_volumes():
    """Read the 11 per-mechanism reactor volumes [L] for every model/scenario cell; non-numeric cells coerced to 0."""
    wb = openpyxl.load_workbook(C.WORKBOOK, data_only=True, read_only=True)
    ws = wb["Scenarios"]

    def col_values(col_letter):
        out = []
        for r in DATA_ROWS:
            v = ws[f"{col_letter}{r}"].value
            out.append(float(v) if isinstance(v, (int, float)) else 0.0)
        return np.array(out, dtype=float)

    return {(m, s): col_values(VOLUME_COLUMNS[m][s]) for m in MODELS for s in SCENARIO_ORDER}


LABEL_PAD_MM = 0.5    # clear space demanded around a label when testing whether it may sit inside its wedge


def label_width_mm(text: str, font_pt: float) -> float:
    """Printed width of the widest line of a label, in mm, from the body font's own advance widths."""
    longest = max(text.split("\n"), key=len)
    return C.text_advance_mm(longest, font_pt)


def draw_pie(ax, center, radius, values, colors, label_fs):
    """Draw one pie as explicit wedges, clockwise from twelve o'clock, and label every wedge that is large enough to see.

    The axes runs y downward so that the layout arithmetic reads top to bottom, which reverses both the sense
    and the origin of a matplotlib angle. Wedges are therefore built from an angle measured clockwise from
    twelve, converted once here, and labels are placed with the same conversion so that a label always lands
    in its own wedge. A wedge whose arc cannot hold its label is labelled outside the rim on a leader.
    """
    total = values.sum()
    cx, cy = center
    halo = [pe.withStroke(linewidth=1.1, foreground="white")]
    candidates = []
    cumulative = 0.0
    for idx, (value, color) in enumerate(zip(values, colors), start=1):
        if value <= 0:
            continue
        fraction = value / total
        phi0, phi1 = 360.0 * cumulative, 360.0 * (cumulative + fraction)
        ax.add_patch(Wedge(center, radius, phi0 - 90.0, phi1 - 90.0, facecolor=color, edgecolor="white", linewidth=0.7, joinstyle="miter"))
        percent = 100.0 * fraction
        text = f"{chr(64 + idx)}\n{percent:.1f}%" if percent < 1.0 else f"{chr(64 + idx)}\n{percent:.0f}%"
        candidates.append((fraction, np.deg2rad(0.5 * (phi0 + phi1)), text, percent))
        cumulative += fraction

    # Widest wedges get first claim on an interior label. A label is shrunk, within limits, until its corners
    # clear both the wedge's sides and the rim; the binding constraint is its inner corners, where the arc is
    # narrowest. Anything that still will not fit is moved out to a leader.
    inside, outside, taken = [], [], []
    for fraction, midpoint, text, percent in sorted(candidates, key=lambda item: -item[0]):
        half_angle = np.deg2rad(360.0 * fraction) / 2.0
        lx, ly = cx + LABEL_R * radius * np.sin(midpoint), cy - LABEL_R * radius * np.cos(midpoint)
        chosen = None
        size = label_fs
        while size >= PIE_LABEL_FLOOR - 1e-9:
            # Fit against the wedge on the label's true extent; the pad is clearance from other labels only.
            half_h = size * 25.4 / 72.0 * 1.35
            half_w = label_width_mm(text, size) / 2.0
            inner, outer = LABEL_R * radius - half_h, LABEL_R * radius + half_h
            box = (lx - half_w - LABEL_PAD_MM, ly - half_h - LABEL_PAD_MM, lx + half_w + LABEL_PAD_MM, ly + half_h + LABEL_PAD_MM)
            clear = not any(box[0] < b[2] and box[2] > b[0] and box[1] < b[3] and box[3] > b[1] for b in taken)
            if inner > 0 and np.arctan2(half_w, inner) <= half_angle and np.hypot(outer, half_w) <= radius and clear:
                chosen = (size, box)
                break
            size -= 0.25
        if chosen is not None:
            taken.append(chosen[1])
            inside.append((midpoint, text, chosen[0]))
        elif percent >= MIN_VISIBLE_PCT:
            outside.append((midpoint, text.replace("\n", " ")))

    for midpoint, text, size in inside:
        ax.text(cx + LABEL_R * radius * np.sin(midpoint), cy - LABEL_R * radius * np.cos(midpoint), text,
                ha="center", va="center", color="black", fontsize=size, fontweight="bold", linespacing=1.35, path_effects=halo)

    # Leader labels are stacked down each side of the pie so that neighbouring slivers cannot overprint.
    line_h = label_fs * 25.4 / 72.0 * 1.55
    for side in (+1, -1):
        group = [(m, t) for m, t in outside if (np.sin(m) >= 0) == (side > 0)]
        if not group:
            continue
        group.sort(key=lambda item: -np.cos(item[0]))
        ideal = [cy - radius * np.cos(m) for m, _ in group]
        placed = []
        for want in ideal:
            placed.append(want if not placed else max(want, placed[-1] + line_h))
        shift = sum(ideal) / len(ideal) - sum(placed) / len(placed)
        for (midpoint, text), ty in zip(group, [p + shift for p in placed]):
            tx = cx + side * (radius + LEAD_OUT)
            ax.plot([cx + radius * np.sin(midpoint) * 0.98, tx - side * 0.4], [cy - radius * np.cos(midpoint), ty],
                    color="#666666", linewidth=0.4, zorder=3, solid_capstyle="butt")
            ax.text(tx, ty, text, ha="left" if side > 0 else "right", va="center", color="black",
                    fontsize=label_fs * 0.92, fontweight="bold", path_effects=halo, zorder=4)
    return len(inside) + len(outside)


def fmt_total(litres: float) -> str:
    return f"{litres / 1000.0:.1f}k L"


def compute_layout(totals):
    """Solve the matrix geometry from the four totals. Returns radii, pie centres, block extent and figure height, in mm."""
    rows, cols, cell, _rk, _ck = matrix_axes()
    v_max = max(totals.values())
    radii = {k: R_MAX_MM * np.sqrt(t / v_max) for k, t in totals.items()}
    r_of = lambda row, col: radii[cell(row, col)]

    # Column pitch must clear the widest neighbouring pair in any row, and likewise row pitch for any column.
    col_pitch = max(r_of(row, cols[0]) + r_of(row, cols[1]) for row in rows) + PIE_GAP
    row_pitch = max(r_of(rows[0], col) + r_of(rows[1], col) for col in cols) + PIE_GAP + NOTE_BAND

    # Leader labels sit outside the rim, so the outermost pies need that room reserved or the block centres wrongly.
    left_over = max(r_of(row, cols[0]) for row in rows) + LEADER_ROOM
    right_over = max(r_of(row, cols[1]) for row in rows) + LEADER_ROOM
    top_over = max(r_of(rows[0], col) for col in cols)
    bottom_over = max(r_of(rows[1], col) for col in cols)

    block_w = left_over + col_pitch + right_over
    block_h = top_over + row_pitch + bottom_over

    # Centre the row-label gutter plus the pie block horizontally.
    x0 = (FIG_W_MM - (ROW_LABEL_W + block_w)) / 2.0 + ROW_LABEL_W
    col_x = [x0 + left_over, x0 + left_over + col_pitch]

    block_top = MARGIN + COL_HEADER_H
    row_y = [block_top + top_over, block_top + top_over + row_pitch]

    # The note sits in the clear band between the rows, below the totals the upper row prints under its pies.
    note_y = 0.5 * ((row_y[0] + top_over + TOTAL_GAP + TOTAL_H) + (row_y[1] - bottom_over))
    fig_h = block_top + block_h + TOTAL_GAP + TOTAL_H + ROUTE_LEGEND_H + MARGIN
    return radii, col_x, row_y, (x0, block_top, block_w, block_h), note_y, fig_h


def build() -> None:
    C.check_inputs([C.WORKBOOK, C.COLORS], "S (reactor volumes)")
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42

    vols = read_all_volumes()
    totals = {k: v.sum() for k, v in vols.items()}
    colors = mechanism_colors()
    radii, col_x, row_y, block, note_y, fig_h = compute_layout(totals)

    fig = plt.figure(figsize=(FIG_W_MM / 25.4, fig_h / 25.4))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, FIG_W_MM)
    ax.set_ylim(fig_h, 0.0)  # y increases downward, so the layout maths reads top to bottom
    ax.set_aspect("equal")
    ax.axis("off")


    rows, cols, cell, row_kind, col_kind = matrix_axes()
    header_y = block[1] - COL_HEADER_H * 0.42
    for x, col in zip(col_x, cols):
        ax.text(x, header_y, f"{col} {col_kind}", ha="center", va="center", fontsize=HEADER, fontweight="bold")
    for y, row in zip(row_y, rows):
        ax.text(block[0] - 2.5, y, f"{row}\n{row_kind}", ha="right", va="center", fontsize=HEADER, fontweight="bold", linespacing=1.4)

    diagnostics = []
    for row, y in zip(rows, row_y):
        for col, x in zip(cols, col_x):
            m, s = cell(row, col)
            r = radii[(m, s)]
            scale = r / R_MAX_MM
            fs = max(PIE_LABEL_MIN, PIE_LABEL_MAX * scale)
            n = draw_pie(ax, (x, y), r, vols[(m, s)], colors, fs)
            ax.text(x, y + r + TOTAL_GAP, fmt_total(totals[(m, s)]), ha="center", va="top", fontsize=TOTAL_FS, fontweight="bold")
            diagnostics.append((m, s, totals[(m, s)], r, fs, n))

    span = max(totals.values()) / min(totals.values())
    ax.text(FIG_W_MM / 2.0, note_y, f"Pie area is proportional to total reactor volume, on one scale across all four panels (largest / smallest = {span:.1f}\u00d7)", ha="center", va="center", fontsize=NOTE_FS, bbox=dict(boxstyle="round,pad=0.45", facecolor="#f0f0f0", edgecolor="gray", linewidth=0.6))

    # One key serves the whole matrix. A separate substrate key would repeat it: the routes are listed in
    # substrate order, each entry names its substrate, and each swatch is the fill the wedges carry, so the
    # grouping by substrate is already legible down the columns.
    labels = [f"{chr(64 + i)}. {route_display(r)}" for i, r in enumerate(C.read_scenario_rows(), start=1)]
    mech_handles = [Patch(facecolor=colors[i], edgecolor="none", label=labels[i]) for i in range(len(labels))]
    leg_bot = fig.legend(handles=mech_handles, title="Route (Fill Color Denotes the Substrate)", loc="lower center", bbox_to_anchor=(0.5, MARGIN / fig_h), ncol=LEGEND_NCOL, frameon=True, fontsize=LEG, title_fontsize=LEG_TITLE, handlelength=1.1, handletextpad=0.4, columnspacing=1.4)
    leg_bot.get_title().set_fontweight("bold")

    C.OUTPUTS.mkdir(parents=True, exist_ok=True)
    pdf_path = C.OUTPUTS / "FigS3.pdf"
    png_path = C.OUTPUTS / "FigS3.png"
    fig.savefig(pdf_path, facecolor="white")
    fig.savefig(png_path, dpi=C.DPI, facecolor="white")
    plt.close(fig)
    print(f"Wrote {C.rel(png_path)} and {C.rel(pdf_path)}  |  {FIG_W_MM:.0f} x {fig_h:.1f} mm, span {span:.1f}x")
    for m, s, t, r, fs, n in diagnostics:
        drawn = int((vols[(m, s)] > 0).sum())
        print(f"    {m:11s} {s:12s} {t:9,.0f} L   r={r:5.2f} mm   {n:2d} of {drawn:2d} wedges labelled   fs={fs:.1f} pt")


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