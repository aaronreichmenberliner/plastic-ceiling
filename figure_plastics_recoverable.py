#!/usr/bin/env python3
"""Supplementary figure: recoverable versus non-recoverable plastic carbon on the ISS. Degradable polyesters and polyamides carry hydrolysable linkages and are recoverable in principle; recalcitrant plastics are not. No conversion route is assumed and no downstream bioprocess is implied. Set SCALE to 1.0 to recover journal type sizing."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches

import common as C
from common import clean_common, KG_C, read_routing_rows, read_scenario_rows, text_color

PER_CREW_UNIT = f"{KG_C}/(person\u00b7yr)"

SIZE = (12.6, 6.2)   # wide, for a 16:9 slide
SCALE = 2.7
VALUE = 7.4 * SCALE   # segment values, total, axis label
LABEL = 8.2 * SCALE   # bracket captions
SHARE = 11.0 * SCALE  # the two shares carry the message, so they lead
TICK = 6.8 * SCALE
FOOT = 6.5 * SCALE

NOTE = "* none of it is currently recovered"
RECOVERABLE_LABEL = "Recoverable*"
ADDITIONAL_LABEL = "Not Recoverable"

RECALCITRANT = "#8A96A3"
BRACKET = "#48566A"


def read_crew_size() -> float:
    """Mean crew over the reporting period, from the workbook, so the per-crew basis stays in sync."""
    import openpyxl
    wb = openpyxl.load_workbook(C.WORKBOOK, data_only=True, read_only=True)
    ws = wb["Inputs"]
    for row in ws.iter_rows(values_only=True):
        if isinstance(row[0], str) and row[0].strip().lower() == "crew members":
            return float(row[1])
    raise ValueError("crew size not found in the Inputs sheet")


def collect():
    crew = read_crew_size()
    routing = read_routing_rows()
    routes = {str(r["substrate"]): float(r["cons_carbon"])
              for r in read_scenario_rows() if str(r["substrate"]) in ("Polyesters", "Polyamides")}
    recalcitrant = routing["RecPlastics_to_Pyrolysis"][0] + routing["RecPlastics_remaining"][0]
    return routes["Polyesters"] / crew, routes["Polyamides"] / crew, recalcitrant / crew


def bracket(ax, x0, x1, y, depth, color, label, share, label_frac=0.5, align="center"):
    ax.plot([x0, x0, x1, x1], [y, y - depth, y - depth, y], color=color, lw=2.2, clip_on=False)
    tx = x0 if align == "left" else x0 + label_frac * (x1 - x0)
    ax.text(tx, y - depth - 0.10, label, ha=align, va="top",
            fontsize=LABEL, fontweight="bold", color=color)
    ax.text(tx, y - depth - 0.30, f"{share:.1f}%", ha=align, va="top",
            fontsize=SHARE, fontweight="bold", color=color)


def _figure():
    polyesters, polyamides, recalcitrant = collect()
    recoverable = polyesters + polyamides
    total = recoverable + recalcitrant

    fig, ax = plt.subplots(figsize=SIZE, facecolor="white")
    clean_common(ax, TICK)
    y0, height = 0.42, 0.52

    # A single inventory read left to right. Solid fill is recoverable with current chemistry; the hatched
    # segment is not, and is what better polymer design would convert.
    segments = [
        (polyesters, C.SUBSTRATE_COLORS["Polyesters"], None, "Polyesters"),
        (polyamides, C.SUBSTRATE_COLORS["Polyamides"], None, "Polyamides"),
        (recalcitrant, RECALCITRANT, "//", "Recalcitrant Plastics"),
    ]
    left = 0.0
    for value, color, hatch, name in segments:
        ax.barh(y0, value, height=height, left=left, color=color, edgecolor="white", linewidth=1.2, hatch=hatch)
        centre = left + value / 2
        label = f"{name}\n{value:,.1f} {PER_CREW_UNIT}"
        if 100 * value / total >= 10.0:
            ax.text(centre, y0 + height / 2 + 0.14, label, ha="center", va="bottom",
                    fontsize=VALUE, fontweight="bold", color=color, linespacing=1.2)
        else:
            ax.annotate(label, xy=(centre, y0 + height / 2), xytext=(centre + total * 0.085, y0 + height / 2 + 0.52),
                        ha="center", va="bottom", fontsize=VALUE, fontweight="bold", color=color,
                        annotation_clip=False, linespacing=1.2,
                        arrowprops=dict(arrowstyle="-", color="#9A9A9A", lw=0.9, shrinkA=2, shrinkB=3))
        left += value

    bracket(ax, 0.0, recoverable, y0 - height / 2 - 0.12, 0.12, C.SUBSTRATE_COLORS["Polyesters"],
            RECOVERABLE_LABEL, 100 * recoverable / total, align="left")
    bracket(ax, recoverable, total, y0 - height / 2 - 0.12, 0.12, BRACKET,
            ADDITIONAL_LABEL, 100 * recalcitrant / total, label_frac=0.58)

    ax.axvline(total, color=BRACKET, lw=1.6, linestyle=(0, (5, 3)), ymin=0.05, ymax=0.95)
    ax.text(total - total * 0.012, 1.42, f"Total {total:,.1f} {PER_CREW_UNIT}",
            ha="right", va="bottom", fontsize=VALUE, color=BRACKET)

    ax.set_xlabel(f"Plastic Carbon [{PER_CREW_UNIT}]", fontsize=VALUE, labelpad=14)
    ax.set_xticks(np.arange(0, 401, 50))
    ax.set_xlim(0, 402)
    ax.set_ylim(-0.72, 1.74)
    ax.set_yticks([])
    ax.tick_params(axis="x", labelsize=TICK, pad=12)
    ax.spines["left"].set_visible(False)
    ax.text(0.0, -0.30, NOTE, transform=ax.transAxes, ha="left", va="top",
            fontsize=FOOT, fontstyle="italic", color=BRACKET)
    return fig


def build() -> None:
    """Write the figure into outputs/, matching the other supplementary figures."""
    C.configure()
    C.apply_rcparams()
    fig = _figure()
    C.OUTPUTS.mkdir(parents=True, exist_ok=True)
    png_path = C.OUTPUTS / "FigS_plastics_recoverable.png"
    pdf_path = C.OUTPUTS / "FigS_plastics_recoverable.pdf"
    fig.savefig(png_path, dpi=C.DPI, facecolor="white", bbox_inches="tight", pad_inches=0.08)
    fig.savefig(pdf_path, facecolor="white", bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    print(f"Wrote {C.rel(png_path)} and {C.rel(pdf_path)}")


def main() -> int:
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
