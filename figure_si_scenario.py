#!/usr/bin/env python3
"""
Supplementary figure: scenario-level carbon routing and biomass output (the aggregate of the route panel in Figure 3).

Six stacked bars (Baseline and Aspirational, each: carbon routed, biomass theoretical, biomass empirical), stacked by substrate with the organism/process hatch retained and per-bar totals. This is the panel moved out of the main Figure 3; it keeps the numerical totals and the hatch pattern. Authored at 150 mm; the figure carries no title of its own, the caption naming it instead. Run `python figure_si_scenario.py`.
"""
from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches
from matplotlib.legend_handler import HandlerTuple

import common as C
from common import clean_common, KG_BIOMASS, KG_C, organism_hatch, process_legend_items, read_scenario_rows, substrate_legend_items

FIG_W_IN = 150 / 25.4
FIG_H_IN = 5.2
S_AXIS, S_TICK, S_ANNOT, S_KEY = 8.0, 7.5, 7.5, 6.5
HATCH_LW = 0.4


def _bars(ax: plt.Axes, colors: dict[str, str]) -> None:
    rows = read_scenario_rows()
    clean_common(ax, S_TICK)
    bars = [
        ("Carbon\nrouted", "cons_carbon"),
        ("Biomass\nTheoretical", "cons_biomass_t"),
        ("Biomass\nEmpirical", "cons_biomass_e"),
        ("Carbon\nrouted", "aggr_carbon"),
        ("Biomass\nTheoretical", "aggr_biomass_t"),
        ("Biomass\nEmpirical", "aggr_biomass_e"),
    ]
    # Carbon routed is a different quantity from the two biomass estimates, so it is set apart from them;
    # the gap between scenarios is wider again, giving three levels of spacing: pair, quantity, scenario.
    x = np.array([0.0, 1.00, 1.72, 3.30, 4.30, 5.02])
    bottoms = np.zeros(len(bars))
    for r in rows:
        color = C.route_color(str(r["substrate"]), str(r["mechanism"]))
        hatch = organism_hatch(str(r["mechanism"]))
        vals = np.array([float(r[key]) for _label, key in bars])
        ax.bar(x, vals, width=0.56, bottom=bottoms, color=color, edgecolor="white", linewidth=0.4, hatch=hatch)
        bottoms += vals
    top = float(bottoms.max())
    for xi, total in zip(x, bottoms):
        ax.text(xi, total + top * 0.014, f"{total:,.0f}", ha="center", va="bottom", fontsize=S_ANNOT, fontweight="bold")
    ax.axvline(2.51, color="#C6CCD8", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([label for label, _key in bars], fontsize=S_TICK)
    ax.set_ylabel(f"Annual Mass ({KG_BIOMASS}/yr; carbon as {KG_C}/yr)", fontsize=S_AXIS)
    ax.set_xlim(-0.55, 5.57)
    ax.set_ylim(0, top * 1.16)
    ax.text(float(np.mean(x[:3])), -top * 0.15, "Baseline", ha="center", va="top", fontsize=S_TICK, fontweight="bold", clip_on=False)
    ax.text(float(np.mean(x[3:])), -top * 0.15, "Aspirational", ha="center", va="top", fontsize=S_TICK, fontweight="bold", clip_on=False)


def _key(ax: plt.Axes, colors: dict[str, str]) -> tuple[plt.matplotlib.legend.Legend, plt.matplotlib.legend.Legend]:
    """Two keys stacked in their own axes, sharing one frame. Legends are used rather than hand-placed swatches so the entries pack to their own widths; at a fixed pitch the longest label sets the spacing and the row overruns as soon as the type grows. Neither legend draws its own frame: `frame_key` puts a single box around the pair once the layout has settled."""
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    substrate_handles, substrate_labels = [], []
    for substrate, label in substrate_legend_items():
        substrate_labels.append(label)
        if substrate == "CO2":
            substrate_handles.append((patches.Patch(facecolor=C.CO2_LIGHT, edgecolor="none"), patches.Patch(facecolor=C.CO2_MEDIUM, edgecolor="none")))
        else:
            substrate_handles.append(patches.Patch(facecolor=C.substrate_color(substrate), edgecolor="none"))
    upper = ax.legend(
        substrate_handles, substrate_labels, title="Substrate Colour", loc="lower center", bbox_to_anchor=(0.5, 0.52),
        ncol=len(substrate_labels), frameon=False, fontsize=S_KEY, title_fontsize=S_KEY, handlelength=1.6, handleheight=2.1,
        handletextpad=0.4, columnspacing=0.9, borderpad=0.5, borderaxespad=0.0,  # handleheight exceeds handlelength because matplotlib takes a descent off the handle box; these values render square handler_map={tuple: HandlerTuple(ndivide=None, pad=0.0)},
    )
    upper.get_title().set_fontweight("bold")
    ax.add_artist(upper)

    process = process_legend_items()
    lower = ax.legend(
        [patches.Patch(facecolor="white", edgecolor="#48566A", linewidth=0.7, hatch=hatch) for _label, hatch in process],
        [label for label, _hatch in process], title="Organism / Process Pattern", loc="upper center", bbox_to_anchor=(0.5, 0.48),
        ncol=len(process), frameon=False, fontsize=S_KEY, title_fontsize=S_KEY, handlelength=1.6, handleheight=2.1,
        handletextpad=0.4, columnspacing=0.9, borderpad=0.5, borderaxespad=0.0,  # handleheight exceeds handlelength because matplotlib takes a descent off the handle box; these values render square
    )
    lower.get_title().set_fontweight("bold")
    return upper, lower


def frame_key(ax: plt.Axes, legends, pad_mm: float = 1.0) -> None:
    """Draw one frame around both keys. Called after a first draw, so the legends have their final size; the box is expressed in axes fractions, which hold for the vector backends as well as the raster one."""
    from matplotlib.transforms import Bbox
    figure = ax.figure
    renderer = figure.canvas.get_renderer()
    union = Bbox.union([legend.get_window_extent(renderer) for legend in legends]).transformed(ax.transAxes.inverted())
    extent = ax.get_window_extent(renderer)
    px_per_mm = figure.get_size_inches()[0] * figure.dpi / (figure.get_size_inches()[0] * 25.4)
    pad_x = pad_mm * px_per_mm / extent.width
    pad_y = pad_mm * px_per_mm / extent.height
    frame = patches.FancyBboxPatch(
        (union.x0 - pad_x, union.y0 - pad_y), union.width + 2 * pad_x, union.height + 2 * pad_y,
        boxstyle="round,pad=0,rounding_size=0.012", transform=ax.transAxes,
        facecolor="white", edgecolor="#B0B0B0", linewidth=0.8, zorder=1,
    )
    frame.set_in_layout(False)
    ax.add_patch(frame)


def build() -> None:
    colors = C.read_color_key(C.COLORS)
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42
    plt.rcParams["hatch.linewidth"] = HATCH_LW
    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN), dpi=C.DPI, constrained_layout=True)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 0.24])
    ax_bars = fig.add_subplot(gs[0, 0])
    ax_key = fig.add_subplot(gs[1, 0])
    _bars(ax_bars, colors)
    legends = _key(ax_key, colors)
    fig.canvas.draw()
    frame_key(ax_key, legends)
    C.OUTPUTS.mkdir(parents=True, exist_ok=True)
    pdf_path = C.OUTPUTS / "FigS_scenario_aggregate.pdf"
    png_path = C.OUTPUTS / "FigS_scenario_aggregate.png"
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=C.DPI)
    plt.close(fig)
    print(f"Wrote {C.rel(png_path)} and {C.rel(pdf_path)}")


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