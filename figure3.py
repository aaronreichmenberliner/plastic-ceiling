#!/usr/bin/env python3
"""
Figure 3: route-resolved throughput, reactor sizing, and volume burden.

Panels, in reading order:
  - Route-resolved carbon routed vs biomass output (Baseline | Aspirational); biomass is drawn as empirical (solid inner bar) within theoretical (outline), both overlaid from the baseline, so the two estimates are directly comparable and cases where empirical exceeds theoretical show.
  - Biomass output versus reactor volume, coloured by volumetric efficiency.
  - Reactor-volume burden by route.

A shared key runs along the bottom. The figure is authored at 180 mm (double column) and drawn at its printed size, so authored pt == printed pt; the type constants below are the printed sizes. All three panels use solid fills: every route carries its own labelled row, marker or key letter, so the organism/process hatch is not needed here. Run `python figure3.py`.
"""
from __future__ import annotations

import argparse

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

import common as C
from common import clean_common, display_formula, DPI, is_interconversion, KG_BIOMASS, KG_C, read_scenario_rows, substrate_legend_items

# Final-size geometry and type. At 180 mm the figure prints 1:1, so authored pt == printed pt; Nature
# caps body text at 7 pt (min 5).
FIG_W_IN = 180 / 25.4
FIG_H_IN = 7.4
F3_TITLE, F3_AXIS, F3_TICK, F3_ANNOT, F3_KEY = 7.35, 6.83, 6.3, 6.3, 5.78
# The key panel sets its own size, kept just under F3_TITLE. F3_KEY still drives the route letters printed on
# the efficiency scatter, where the markers are already close together and larger type would collide.
F3_KEYTEXT = 7.0
HATCH_LW = 0.4


# Canonical mechanism names for routes where the workbook's generic descriptor is replaced by the
# accepted functional-group name, keyed by (raw substrate, raw mechanism). Applied study-wide via route_display.
_CANONICAL_MECHANISM = {
    ("CO", "Lithoautotroph (anaerobic)"): "Acetogen",
    ("Wet_Organics", "Heterotroph (anaerobic)"): "Acidogenesis",
}


def route_display(row: dict[str, float | str]) -> str:
    substrate_raw = str(row["substrate"])
    mechanism = str(row["mechanism"]).strip()
    mechanism = _CANONICAL_MECHANISM.get((substrate_raw, mechanism), mechanism)
    substrate = display_formula(substrate_raw.replace("_", " "))
    return f"{substrate} | {mechanism}"


def _panel_routes(ax_left: plt.Axes, ax_right: plt.Axes, colors: dict[str, str]) -> None:
    # This panel plots carbon routed and biomass formed, and an interconversion has neither, so it would
    # occupy a labelled row with nothing drawn in it. The volume panel keeps them: their reactor volume is real.
    rows = [r for r in read_scenario_rows() if not is_interconversion(r)]
    y = np.arange(len(rows))
    outer_h, inner_h = 0.70, 0.40
    for title, prefix, ax in [("Baseline", "cons", ax_left), ("Aspirational", "aggr", ax_right)]:
        clean_common(ax, F3_TICK)
        ax.axvline(0, color="black", lw=0.7, zorder=2)
        max_left = max(float(r[f"{prefix}_carbon"]) for r in rows)
        max_right = max(max(float(r[f"{prefix}_biomass_t"]), float(r[f"{prefix}_biomass_e"])) for r in rows)
        max_x = max(max_left, max_right) * 1.12
        for yi, r in zip(y, rows):
            color = C.route_color(str(r["substrate"]), str(r["mechanism"]))
            carbon = float(r[f"{prefix}_carbon"])
            theo = float(r[f"{prefix}_biomass_t"])
            emp = float(r[f"{prefix}_biomass_e"])
            ax.barh(yi, -carbon, height=outer_h, color=color, edgecolor="white", linewidth=0.4, zorder=3)
            ax.barh(yi, theo, height=outer_h, facecolor="none", edgecolor=color, linewidth=0.9, zorder=4)
            ax.barh(yi, emp, height=inner_h, color=color, edgecolor="none", zorder=5)
        ax.set_title(title, fontsize=F3_ANNOT, fontweight="bold", pad=2)
        ax.set_xlim(-max_x, max_x)
        ax.set_ylim(len(rows) - 0.5, -0.7)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{abs(v):,.0f}"))
        ax.text(0.25, -0.135, f"Carbon routed\n({KG_C}/yr)", transform=ax.transAxes, ha="center", va="top", fontsize=F3_TICK)
        ax.text(0.75, -0.135, f"Biomass\n({KG_BIOMASS}/yr)", transform=ax.transAxes, ha="center", va="top", fontsize=F3_TICK)
    ax_left.set_yticks(y)
    ax_left.set_yticklabels([route_display(r) for r in rows], fontsize=F3_TICK)
    ax_right.tick_params(axis="y", labelleft=False)
    handles = [
        patches.Patch(facecolor="#777777", edgecolor="none", label="Carbon routed"),
        patches.Patch(facecolor="#777777", edgecolor="none", label="Biomass, empirical"),
        patches.Patch(facecolor="none", edgecolor="#777777", linewidth=0.9, label="Biomass, theoretical"),
    ]
    ax_right.legend(handles=handles, loc="lower right", frameon=False, fontsize=F3_ANNOT, handlelength=1.2, handletextpad=0.4, labelspacing=0.3)


def _panel_efficiency(ax: plt.Axes, fig: plt.Figure, colors: dict[str, str]) -> None:
    rows = read_scenario_rows()
    clean_common(ax, F3_TICK)
    scenarios = [
        ("cons_volume_t", "cons_biomass_t", "o", True),
        ("cons_volume_e", "cons_biomass_e", "o", False),
        ("aggr_volume_t", "aggr_biomass_t", "^", True),
        ("aggr_volume_e", "aggr_biomass_e", "^", False),
    ]
    eff, pts = [], []
    for idx, r in enumerate(rows, start=1):
        for vk, bk, mk, fill in scenarios:
            v = float(r[vk])
            b = float(r[bk])
            if v <= 0 or b <= 0:
                continue
            e = b / v
            eff.append(e)
            pts.append((idx, v, b, e, mk, fill))
    norm = LogNorm(vmin=min(eff), vmax=max(eff))
    cmap = LinearSegmentedColormap.from_list("eff_chartreuse_purple", ["#C4F015", "#EDC317", "#F5871A", "#E84C6A", "#A62D8E", "#3B0A46"])
    for idx, v, b, e, mk, fill in pts:
        col = cmap(norm(e))
        face = col if fill else "white"
        ax.scatter(v, b, s=44, marker=mk, facecolor=face, edgecolor=col, linewidth=0.9, zorder=3)
        ax.annotate(chr(64 + idx), (v, b), ha="center", va="center", fontsize=F3_KEY, fontweight="bold", color="black", zorder=4, path_effects=[pe.withStroke(linewidth=1.0, foreground="white")])
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Reactor Volume (L)", fontsize=F3_AXIS)
    ax.set_ylabel(f"Biomass Output ({KG_BIOMASS}/yr)", fontsize=F3_AXIS)
    ax.set_title("Biomass Output versus Reactor Volume", fontsize=F3_TITLE, fontweight="bold", loc="left", pad=3)
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cax = ax.inset_axes([1.02, 0.0, 0.045, 1.0])
    cbar = fig.colorbar(sm, cax=cax)
    cbar.set_label(f"Efficiency ({KG_BIOMASS}/L/yr)", fontsize=F3_AXIS)
    cbar.ax.tick_params(labelsize=F3_KEY)
    handles = [
        Line2D([0], [0], marker="o", linestyle="none", markerfacecolor="#777777", markeredgecolor="#777777", markersize=4, label="Baseline Theoretical"),
        Line2D([0], [0], marker="o", linestyle="none", markerfacecolor="white", markeredgecolor="#777777", markersize=4, label="Baseline Empirical"),
        Line2D([0], [0], marker="^", linestyle="none", markerfacecolor="#777777", markeredgecolor="#777777", markersize=4, label="Aspirational Theoretical"),
        Line2D([0], [0], marker="^", linestyle="none", markerfacecolor="white", markeredgecolor="#777777", markersize=4, label="Aspirational Empirical"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=F3_KEY, handletextpad=0.3, labelspacing=0.3)


def _panel_volume(ax: plt.Axes, colors: dict[str, str]) -> None:
    rows = read_scenario_rows()
    labels = ["Baseline\nTheoretical", "Baseline\nEmpirical", "Aspirational\nTheoretical", "Aspirational\nEmpirical"]
    keys = ["cons_volume_t", "cons_volume_e", "aggr_volume_t", "aggr_volume_e"]
    clean_common(ax, F3_TICK)
    x = np.arange(len(keys))
    bottoms = np.zeros(len(keys))
    for r in rows:
        vals = np.array([float(r[k]) for k in keys])
        color = C.route_color(str(r["substrate"]), str(r["mechanism"]))
        ax.bar(x, vals, bottom=bottoms, color=color, edgecolor="white", linewidth=0.5, width=0.66)
        bottoms += vals
    for xi, total in zip(x, bottoms):
        ax.text(xi, total * 1.02, f"{total / 1000:.1f}k L", ha="center", va="bottom", fontsize=F3_ANNOT, fontweight="bold")
    ax.set_ylabel("Reactor Volume (L)", fontsize=F3_AXIS)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=F3_TICK)
    ax.set_title("Reactor-Volume Burden by Route", fontsize=F3_TITLE, fontweight="bold", loc="left", pad=3)
    ax.set_ylim(0, max(bottoms) * 1.16)


def _panel_key(ax: plt.Axes, colors: dict[str, str]) -> None:
    rows = read_scenario_rows()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.0, 0.94, "Substrate Colour", fontsize=F3_KEYTEXT, fontweight="bold", va="top")
    x0, y0, dx = 0.0, 0.58, 0.122
    for i, (substrate, label) in enumerate(substrate_legend_items()):
        x = x0 + i * dx
        if substrate == "CO2":
            ax.add_patch(patches.Rectangle((x, y0), 0.010, 0.20, facecolor=C.CO2_LIGHT, edgecolor="none"))
            ax.add_patch(patches.Rectangle((x + 0.010, y0), 0.010, 0.20, facecolor=C.CO2_MEDIUM, edgecolor="none"))
        else:
            ax.add_patch(patches.Rectangle((x, y0), 0.020, 0.20, facecolor=C.substrate_color(substrate), edgecolor="none"))
        ax.text(x + 0.028, y0 + 0.10, label, fontsize=F3_KEYTEXT, va="center")
    ax.text(0.0, 0.36, "Route Letters", fontsize=F3_KEYTEXT, fontweight="bold", va="top")
    # Routes are lettered A-K study-wide (the efficiency scatter above and the SI reactor-volume pies share one identifier set).
    letters = [f"{chr(64 + i)}{'*' if is_interconversion(r) else ''}. {route_display(r)}" for i, r in enumerate(rows, start=1)]
    # Three columns of four rather than four of three: at 0.255 width the longest label (G, wet organics
    # mixotroph) overran its column and collided with J. At 0.34 each label has room.
    columns = [letters[0:4], letters[4:8], letters[8:]]
    for x, column in zip([0.0, 0.34, 0.68], columns):
        ax.text(x, 0.24, "\n".join(column), fontsize=F3_KEYTEXT, va="top", linespacing=1.3)


def build() -> None:
    C.check_inputs([C.WORKBOOK, C.COLORS], 3)
    colors = C.read_color_key(C.COLORS)
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42
    plt.rcParams["hatch.linewidth"] = HATCH_LW
    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN), dpi=DPI, constrained_layout=True)
    fig.get_layout_engine().set(rect=(0.0, 0.0, 1.0, 0.94), wspace=0.10)
    # Row 1 is an empty spacer, so the route panels stand clear of the two beneath them. Setting hspace
    # instead would open every row by the same proportion, including the gap above the key.
    gs = fig.add_gridspec(4, 2, height_ratios=[1.34, 0.04, 1.0, 0.50])
    gs_routes = gs[0, :].subgridspec(1, 2, wspace=0.06)
    ax_routes_base = fig.add_subplot(gs_routes[0, 0])
    ax_routes_asp = fig.add_subplot(gs_routes[0, 1], sharey=ax_routes_base)
    ax_efficiency = fig.add_subplot(gs[2, 0])
    ax_volume = fig.add_subplot(gs[2, 1])
    ax_key = fig.add_subplot(gs[3, :])
    _panel_routes(ax_routes_base, ax_routes_asp, colors)
    _panel_efficiency(ax_efficiency, fig, colors)
    _panel_volume(ax_volume, colors)
    _panel_key(ax_key, colors)
    fig.canvas.draw()
    fig.set_layout_engine("none")
    renderer = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    # Spanning title for the route panel, centred over its two scenario plots (above the Baseline/Aspirational labels).
    pos_base = ax_routes_base.get_position()
    pos_asp = ax_routes_asp.get_position()
    routes_bb = ax_routes_base.get_tightbbox(renderer)
    _x, routes_top = inv.transform((routes_bb.x0, routes_bb.y1))
    title_y = min(routes_top + 0.006, 0.960)
    fig.text((pos_base.x0 + pos_asp.x1) / 2.0, title_y, "Route-Resolved Carbon Routing and Biomass Output", ha="center", va="bottom", fontsize=F3_TITLE, fontweight="bold")
    C.OUTPUTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(C.OUTPUTS / "Fig3.pdf")
    fig.savefig(C.OUTPUTS / "Fig3.png", dpi=DPI)
    plt.close(fig)
    print(f"Wrote {C.rel(C.OUTPUTS / 'Fig3.png')} and {C.rel(C.OUTPUTS / 'Fig3.pdf')}")


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