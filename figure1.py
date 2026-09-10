#!/usr/bin/env python3
"""
Figure 1: ISS carbon inventory.

Panels, in reading order:
  - make_figure_1_sankey     steady-state carbon throughput (Plotly; returns a PIL image, embedded as a raster in the otherwise vector figure)
  - make_figure_1_stackplot  cumulative terminal carbon waste over the mission
  - make_figure_1_doughnut   lifetime uplinked mass and carbon

Generators are named for what they draw.

The Sankey's flow table comes from `numbers.xlsx!Figure 1A`, so its labels cannot drift from the data. Node colours are seeded from `colors.xlsx`, but every canonical stream node is then overridden from the shared palette in `common.py`, and the four logistics categories from the slate ramp below; only Food Waste and Human Waste are taken from the workbook as-is. Only the node layout lives in this file. Run `python figure1.py`.
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from PIL import Image

import common as C
from common import figure_with_plot_area, FONT, KG_PER_TONNE, open_rgba, panel_title, read_sankey_flows, read_uplink_masses, read_terminal_waste, T_C, text_color, _trim_ink

SANKEY_CACHE: Path | None = None   # optional cached Sankey PNG; bypasses the Plotly render

# Type sizes (pt).
F1 = 9.9
F1_CENTRE = 18.0     # doughnut centre statistic: the ring's hole is empty, so the headline number is set well above the panel's other type
F1_WEDGE = 11.55      # doughnut wedge labels only: set above F1 so the per-segment mass and units stay readable after the composite downscale
# Doughnut mass-unit labels: all tonnes, but total / carbon / non-carbon distinguished by subscript index.
T_TOT = "t$_\\mathrm{tot}$"
T_NONC = "t$_\\mathrm{nc}$"
F1_STACK = 14.0      # the stackplot sits in a narrow box; its type is set larger so it survives the composite downscale

# Sankey. Values and colors come from the workbooks; only the layout lives here.
SANKEY_UNIT = "kg<sub>C</sub>/(person\u00b7yr)"
SANKEY_TITLE = "ISS Steady-State Carbon Throughput"
SANKEY_SUBTITLE = "<i>\u201cWhat goes up and where carbon goes\u201d</i>"   # Plotly has no italic font property; the tag is how
SANKEY_FONT = 24     # px in the Plotly layout space (width SANKEY_WIDTH); ~7.2 pt at 180 mm reproduction width
SANKEY_WIDTH, SANKEY_HEIGHT, SANKEY_SCALE, SANKEY_PAD = 1980, 800, 3, 24
SANKEY_NODES = [
    "Food", "Clothing", "Personal Supplies", "Packaging",
    "Food Waste", "Human Waste", "Exhaled CO2", "Wet Organics",
    "Cellulose", "Non-Biodegradable Plastic", "Biodegradable Plastic",
    "Scrubbed CO2", "Sabatier", "Waste CO2 (Vented)", "Waste Methane (Vented)", "Solid Carbon Waste",
]
# Node placement. A label is two lines deep, so nodes whose labels can meet - within a column, or across
# the last two columns where the terminal labels run leftward - are kept at least 0.12 of the height apart.
SANKEY_X = [0.01, 0.01, 0.01, 0.01, 0.20, 0.20, 0.20, 0.40, 0.20, 0.20, 0.20, 0.40, 0.62, 0.80, 0.80, 0.80]
SANKEY_Y = [0.25, 0.45, 0.65, 0.85, 0.28, 0.40, 0.15, 0.43, 0.53, 0.72, 0.90, 0.08, 0.20, 0.06, 0.34, 0.72]
# Display names for the Sankey. The workbook keys are left untouched, so the flow table still drives the
# figure; only the printed form is normalised here to one pattern, "<species> Waste (<disposal route>)".
SANKEY_DISPLAY = {
    "Exhaled CO2": "Exhaled CO<sub>2</sub>",
    "Scrubbed CO2": "Scrubbed CO<sub>2</sub>",
    "Waste CO2 (Vented)": "CO<sub>2</sub> Waste (Vented)",
    "Waste Methane (Vented)": "CH<sub>4</sub> Waste (Vented)",
    "Solid Carbon Waste": "Solid Carbon Waste (Incinerated)",
}
# Terminal nodes sit in the last column; their labels are set to the left of the node so they fall on the
# diagram rather than in a margin, which lets the Sankey itself use the full width.
SANKEY_TERMINAL = {"Waste CO2 (Vented)", "Waste Methane (Vented)", "Solid Carbon Waste"}
# Individual Y positions for every Sankey label.
# Larger values = higher on the figure.
# Smaller values = lower on the figure.
SANKEY_LABEL_Y = {
    "Food": 0.75,
    "Clothing": 0.55,
    "Personal Supplies": 0.35,
    "Packaging": 0.15,

    "Food Waste": 0.72,
    "Human Waste": 0.60,
    "Exhaled CO2": 0.85,
    "Wet Organics": 0.57,

    "Cellulose": 0.47,
    "Non-Biodegradable Plastic": 0.28,
    "Biodegradable Plastic": 0.10,

    "Scrubbed CO2": 0.92,
    "Sabatier": 0.8,

    "Waste CO2 (Vented)": 1.01,
    "Waste Methane (Vented)": 0.59,
    "Solid Carbon Waste": 0.085,
}


# Doughnut and stackplot layout.
CATEGORIES = ["Food", "Clothing", "Personal Supplies", "Packaging"]
PIE_PLOT_SIZE = (5.0, 5.0)
VARIANT_PLOT_SIZE = (3.0, 5.0)

# ISS operational eras. Fields: numeral, time-weighted mean crew, duration in days, and delivered
# logistics mass in tonnes. The mean crew is handover-adjusted rather than the nominal base crew, so
# the five eras sum to 132.50 person-years over 25.05 years (mean crew 5.29) and the logistics mass to
# 548 t; that person-year total is the basis Figures 1B and 1C in numbers.xlsx are reported on, and the
# two must stay in step. The stackplot resolves lifetime terminal waste by era on two drivers: the
# metabolic streams (respired CO2, Sabatier CH4, and the wet-organics fraction of solid waste) accrue
# with crew-time, while the logistics-derived fraction of solid waste (cellulose + plastics) accrues
# with delivered logistics mass, which fell in Era V (higher crew but tighter mass budgeting).
ISS_ERAS = [
    ("I", 3.12, 821, 36),      # Nov 2000 - Feb 2003, 3-crew base
    ("II", 2.08, 1246, 30),    # Feb 2003 - Jul 2006, 2-crew base
    ("III", 3.96, 1035, 55),   # Jul 2006 - May 2009, 3-crew base (Soyuz + Shuttle)
    ("IV", 6.12, 4202, 314),   # May 2009 - Nov 2020, 6-crew base
    ("V", 7.27, 1847, 113),    # Nov 2020 - Nov 2025, 7-crew base
]


def _rgba(hex_color: str, alpha: float = 0.35) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def autopct_with_mass(values, labels, threshold=4.0, show_percent=True, percentages=None):
    values = list(values)
    labels = list(labels)
    counter = {"index": 0}

    def fmt(pct):
        index = counter["index"]
        counter["index"] += 1

        if pct < threshold:
            return ""

        if show_percent:
            # ORIGINAL CALCULATION:
            # pct is the percentage of the entire donut.
            #
            # display_pct = pct

            # NEW CALCULATION:
            # percentage is calculated within each Carbon + Other pair.
            display_pct = pct if percentages is None else percentages[index]

            return f"{labels[index]}\n{values[index]:,.0f} t\n{display_pct:.0f}%"
        else:
            return f"{labels[index]}\n{values[index]:,.0f} t"

    return fmt


def make_figure_1_sankey(colors: dict[str, str]) -> Image.Image:
    """Sankey of steady-state carbon throughput, rasterized in memory. The only raster in the package: Plotly's SVG export nests badly, so this panel is embedded as a base64 PNG at ~1.5x the composited pixel width. Node labels are derived from the flow table, so they cannot drift from the data. Returns a PIL image rather than a matplotlib Figure; plotly and kaleido are imported lazily, and kaleido needs a headless Chrome (`plotly_get_chrome`). Pass --sankey-cache to composite a cached PNG instead."""
    if SANKEY_CACHE is not None:
        return open_rgba(SANKEY_CACHE)

    import plotly.graph_objects as go

    flows = read_sankey_flows()
    inflow: dict[str, float] = {node: 0.0 for node in SANKEY_NODES}
    outflow: dict[str, float] = {node: 0.0 for node in SANKEY_NODES}
    for source, target, value in flows:
        outflow[source] += value
        inflow[target] += value
    # Label value: outflow where the node emits, otherwise inflow. Terminal sinks have no outflow.
    values = {node: (outflow[node] if outflow[node] > 0 else inflow[node]) for node in SANKEY_NODES}
    index = {node: i for i, node in enumerate(SANKEY_NODES)}

    figure = go.Figure(
        go.Sankey(
            arrangement="fixed",
            node=dict(
                pad=100,
                thickness=35,
                line=dict(color="rgba(0,0,0,0)", width=0),
                label=[""] * len(SANKEY_NODES),  # built-in labels hidden; annotations are added below
                color=[colors[node] for node in SANKEY_NODES],
                x=SANKEY_X,
                y=SANKEY_Y,
            ),
            link=dict(
     source=[index[s] for s, _t, _v in flows],
     target=[index[t] for _s, t, _v in flows],
     value=[v for _s, _t, v in flows],
                color=[
    _rgba(colors["Waste CO2 (Vented)"])
    if s in ("Exhaled CO2", "Scrubbed CO2")
    else _rgba(colors["Waste CO2 (Vented)"])
    if s == "Sabatier" and t == "Waste CO2 (Vented)"
    else _rgba(colors["Waste Methane (Vented)"])
    if s == "Sabatier" and t == "Waste Methane (Vented)"
    else _rgba(colors["Food Waste"])
    if s == "Food Waste"
    else _rgba(colors["Human Waste"])
    if s == "Human Waste"
    else _rgba(colors["Wet Organics"])
    if s == "Wet Organics"
    else _rgba(colors["Cellulose"])
    if s == "Cellulose"
    else _rgba(colors["Biodegradable Plastic"])
    if s == "Biodegradable Plastic"
    else _rgba(colors["Non-Biodegradable Plastic"])
    if s == "Non-Biodegradable Plastic"
    else _rgba(colors[s])
    for s, t, _v in flows
],
 ),
        )
    )
    for node, xi, yi in zip(SANKEY_NODES, SANKEY_X, SANKEY_Y):
        terminal = node in SANKEY_TERMINAL
        figure.add_annotation(
            x=xi + 0.015 if terminal else xi + 0.01,
            y=SANKEY_LABEL_Y[node],
            xref="paper",
            yref="paper",
            text=f"{SANKEY_DISPLAY.get(node, node)}<br>{values[node]:.1f} {SANKEY_UNIT}",
            showarrow=False,
            xanchor="right" if terminal else "left",
            yanchor="middle",
            align="right" if terminal else "left",
            font=dict(family=FONT, size=SANKEY_FONT, color="black"),
            borderwidth=0,
            borderpad=6,
        )
    figure.update_layout(
        title=dict(
            text=f"<b>{SANKEY_TITLE}</b>",
            subtitle=dict(text=SANKEY_SUBTITLE, font=dict(family=FONT, size=SANKEY_FONT + 2, color="#48566A")),
            x=0.22,
            xanchor="center",
            font=dict(family=FONT, size=SANKEY_FONT + 8, color="black"),
        ),
        font=dict(family=FONT, size=SANKEY_FONT),
        width=SANKEY_WIDTH,
        height=SANKEY_HEIGHT,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=30, r=24, t=110, b=16),
    )
    png = figure.to_image(format="png", width=SANKEY_WIDTH, height=SANKEY_HEIGHT, scale=SANKEY_SCALE)
    return _trim_ink(Image.open(io.BytesIO(png)).convert("RGB"), SANKEY_PAD).convert("RGBA")


def make_figure_1_doughnut(colors: dict[str, str]) -> plt.Figure:
    total_mass_kg, carbon_mass_kg, noncarbon_mass_kg = read_uplink_masses(CATEGORIES)
    category_colors = [colors[label] for label in CATEGORIES]
    carbon_colors = [colors[f"Carbon {label}"] for label in CATEGORIES]
    noncarbon_colors = [colors[f"Non-Carbon {label}"] for label in CATEGORIES]

    # Wedge geometry uses the kg arrays; only the printed labels are converted to metric tonnes.
    total_mass_t = total_mass_kg / KG_PER_TONNE
    carbon_mass_t = carbon_mass_kg / KG_PER_TONNE

    outer_values: list[float] = []
    outer_colors: list[str] = []
    outer_units: list[str] = []
    for carbon, noncarbon, carbon_color, noncarbon_color in zip(carbon_mass_kg, noncarbon_mass_kg, carbon_colors, noncarbon_colors):
        outer_values.extend([carbon, noncarbon])
        outer_colors.extend([carbon_color, noncarbon_color])
        outer_units.extend(["Carbon", "Other"])

    # NEW: calculate percentages within each input type.
    # Each Carbon + Other pair sums to 100%.
    #
    # This does NOT change the wedge sizes. The wedge sizes still use
    # outer_values, so they remain proportional to the actual masses.
    outer_percentages: list[float] = []
    for carbon, noncarbon in zip(carbon_mass_kg, noncarbon_mass_kg):
        pair_total = carbon + noncarbon
        outer_percentages.extend([
            (carbon / pair_total) * 100,
            (noncarbon / pair_total) * 100,
        ])

    fig, ax = figure_with_plot_area(*PIE_PLOT_SIZE, bottom=0.68, top=0.62)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.grid(False)
    panel_title(ax, "Lifetime Uplinked Mass and Carbon", "\u201cWhat ISS resupply brings aboard\u201d", F1, align="center")

    _ow, _ot, outer_autotexts = ax.pie(
        outer_values,
        radius=0.92,
        colors=outer_colors,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.24, "edgecolor": "white", "linewidth": 1.0},
        autopct=autopct_with_mass(
            [value / KG_PER_TONNE for value in outer_values],
            outer_units,
            threshold=1.0,
            percentages=outer_percentages,
        ),
        pctdistance=0.870,   # (0.92 - 0.24/2) / 0.92: the radial centre of the ring, so the label sits in the band rather than toward its inner edge
        textprops={"fontfamily": FONT, "fontsize": 10.7, "fontweight": "bold", "linespacing": 1.08},
    )

    for autotext, color in zip(outer_autotexts, outer_colors):
        autotext.set_color(text_color(color))
        autotext.set_fontfamily(FONT)
        autotext.set_fontweight("bold")
        outer_autotexts[2].set_color("black")  # Clothing
        outer_autotexts[7].set_color("black")
    # Manually position outer-donut labels.
    # Order:
    # 0 Food - Carbon
    # 1 Food - Non-Carbon
    # 2 Clothing - Carbon
    # 3 Clothing - Non-Carbon
    # 4 Personal Supplies - Carbon
    # 5 Personal Supplies - Non-Carbon
    # 6 Packaging - Carbon
    # 7 Packaging - Non-Carbon

    outer_autotexts[0].set_position((0.26, 0.751))
    #outer_autotexts[1].set_position((-0.55, 0.45))

    #outer_autotexts[2].set_position((0.55, 0.55))
    #outer_autotexts[3].set_position((0.75, 0.20))

    outer_autotexts[4].set_position((-0.477, -0.655))
    #outer_autotexts[5].set_position((0.30, -0.70))

    outer_autotexts[6].set_position((-0.643, 0.443))
    outer_autotexts[7].set_position((-0.16, 0.78))

    inner_labels = ["Food", "Clothing", "Personal\nSupplies", "Packaging"]

    _iw, _it, inner_autotexts = ax.pie(
        total_mass_kg,
        radius=0.65,
        colors=category_colors,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.34, "edgecolor": "white", "linewidth": 1.0},
        autopct=autopct_with_mass(total_mass_t, inner_labels, threshold=7.0),
        pctdistance=0.738,   # (0.65 - 0.34/2) / 0.65: likewise for the inner ring
        textprops={"fontfamily": FONT, "fontsize": 10.7, "fontweight": "bold", "linespacing": 1.08},
    )

    for autotext, color in zip(inner_autotexts, category_colors):
        autotext.set_color(text_color(color))
        autotext.set_fontfamily(FONT)
        autotext.set_fontweight("bold")
    inner_autotexts[1].set_color("black")  # Clothing

    inner_autotexts[0].set_position((.45, .07))
    inner_autotexts[1].set_position((-0.041, -0.53))
    inner_autotexts[2].set_position((-0.41, -0.28))
    inner_autotexts[3].set_position((-0.33, 0.31))

    # Tighten the data limits so the ring fills its axes instead of floating small and centered, which
    # otherwise leaves a large gap between the ring and the title above it.
    ax.set_xlim(-0.98, 0.98)
    ax.set_ylim(-0.98, 0.98)

    ax.text(
        0,
        0,
        f"Resupply:\n{total_mass_t.sum():,.1f} t",
        ha="center",
        va="center",
        fontsize=18,
        fontfamily=FONT,
        fontweight="bold",
        color="black",
        linespacing=1.25,
    )

    #category_handles = [Patch(facecolor=color, edgecolor="none", label=label) for label, color in zip(CATEGORIES, category_colors)]
    #ax.legend(
       # category_handles,
        #CATEGORIES,
        #loc="lower center",
        #bbox_to_anchor=(0.5, -0.10),
        #ncol=2,
        #frameon=False,
        #prop={"family": FONT, "size": F1},
        #handlelength=1.1,
        #handletextpad=0.45,
        #columnspacing=1.05,
    #)
    return fig


def make_figure_1_stackplot(colors: dict[str, str]) -> plt.Figure:
    _labels, waste_values_kg_c = read_terminal_waste()
    labels = ["Solid Carbon Waste", "CO$_2$ Waste", "CH$_4$ Waste"]
    endpoint_labels = ["Solid Waste", "CO$_2$", "CH$_4$"]
    waste_colors = [colors["Solid Carbon Waste"], colors["Waste CO2 (Vented)"], colors["Waste Methane (Vented)"]]

    waste_values_t_c = waste_values_kg_c / KG_PER_TONNE
    total = float(waste_values_t_c.sum())

    # Differentiate the lifetime terminal carbon by ISS operational era on two physical drivers.
    # Metabolic streams (respired CO2, Sabatier CH4, and the wet-organics fraction of solid waste)
    # scale with crew-time; the logistics-derived fraction of solid waste (cellulose + plastics)
    # scales with delivered logistics mass per era, which fell in Era V despite
    # its larger crew. Each stream accrues on its own cumulative-fraction curve, so the piecewise-
    # linear stack has an era-dependent slope while stream totals and the lifetime endpoint are
    # unchanged. The metabolic/logistics split of solid waste is read from the Sankey (Figure 1A).
    era_days = np.array([days for _n, _c, days, _m in ISS_ERAS], float)
    crew_time = np.array([crew * days for _n, crew, days, _m in ISS_ERAS], float)
    logistics = np.array([mass for _n, _c, _d, mass in ISS_ERAS], float)
    era_years = np.concatenate([[0.0], np.cumsum(era_days)]) / 365.0
    span = float(era_years[-1])
    cum_metabolic = np.concatenate([[0.0], np.cumsum(crew_time) / crew_time.sum()])
    cum_logistics = np.concatenate([[0.0], np.cumsum(logistics) / logistics.sum()])

    solid_flows = [(src, val) for src, tgt, val in read_sankey_flows() if tgt == "Solid Carbon Waste"]
    solid_metabolic = sum(val for src, val in solid_flows if src == "Wet Organics")
    solid_logistics = sum(val for src, val in solid_flows if src != "Wet Organics")
    solid_metabolic_frac = solid_metabolic / (solid_metabolic + solid_logistics)
    solid_t, co2_t, ch4_t = (float(v) for v in waste_values_t_c)
    cumulative = [
        solid_t * (solid_metabolic_frac * cum_metabolic + (1.0 - solid_metabolic_frac) * cum_logistics),
        co2_t * cum_metabolic,
        ch4_t * cum_metabolic,
    ]

    fig, ax = figure_with_plot_area(*VARIANT_PLOT_SIZE, left=1.05, right=1.30, bottom=0.72, top=0.86)
    
    for index in range(0, len(ISS_ERAS), 2):
        ax.axvspan(era_years[index], era_years[index + 1], color="#000000", alpha=0.03, linewidth=0, zorder=0)
    for boundary in era_years[1:-1]:
        ax.axvline(boundary, color="#8A8A8A", linewidth=0.8, linestyle=(0, (4, 3)), zorder=2)
    ax.stackplot(era_years, cumulative, colors=waste_colors, alpha=0.95, linewidth=0, zorder=1)
    ax.plot(era_years, np.sum(cumulative, axis=0), color="black", linewidth=1.0, zorder=3)
    # Era numeral and time-weighted mean crew at the top of each band.
    for (numeral, mean_crew, _d, _m), lo, hi in zip(ISS_ERAS, era_years[:-1], era_years[1:]):
        # Two texts so the numeral can be bold while the crew figure stays regular; the offset is in points, so the stacking is independent of the axes scale.
        xm = (lo + hi) / 2.0
        ax.text(xm, 0.968, numeral, transform=ax.get_xaxis_transform(), ha="center", va="top",
                fontsize=F1_STACK - 3, fontfamily=FONT, fontweight="bold", color="#3A3A3A")
        ax.annotate(f"{mean_crew:.1f}", xy=(xm, 0.968), xycoords=ax.get_xaxis_transform(),
                    xytext=(0, -(F1_STACK - 3) * 1.12), textcoords="offset points",
                    ha="center", va="top", fontsize=F1_STACK - 3, fontfamily=FONT, color="#3A3A3A")

    ax.set_xlim(0, span)
    ax.set_ylim(0, 90.0)
    ax.set_xticks([0, 5, 10, 15, 20, 25])
    ax.set_yticks([0, 20, 40, 60, 80])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.set_xlabel("Operational Year", fontfamily=FONT, fontsize=F1_STACK, labelpad=6)
    ax.set_ylabel(f"Cumulative Carbon ({T_C})", fontfamily=FONT, fontsize=F1_STACK, labelpad=6)
    #panel_title(ax, "Lifetime Terminal Carbon Waste", "\u201cWhat carbon ultimately becomes\u201d", F1_STACK)
    #panel_title(ax, "Lifetime Terminal Carbon Waste", "\u201cWhat carbon ultimately becomes\u201d", 12, align="center")
    ax.text(
    0.5, 1.12,
    "Lifetime Terminal Carbon Waste",
    transform=ax.transAxes,
    ha="center",
    va="bottom",
    fontfamily=FONT,
    fontsize=13.5,
    fontweight="bold",
    color="black",
)

    ax.text(
    0.5, 1.065,
    "\u201cWhat carbon ultimately becomes\u201d",
    transform=ax.transAxes,
    ha="center",
    va="bottom",
    fontfamily=FONT,
    fontsize=12,
    fontstyle="italic",
    color="#48566A",
)
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#9A9A9A")
    ax.spines["bottom"].set_color("#9A9A9A")
    ax.tick_params(labelsize=F1_STACK, colors="black")

    for text in ax.findobj(match=plt.Text):
        text.set_fontfamily(FONT)

    # Right-hand annotations are stacked rather than set on one line: the gutter drops from
    # 2.30 in to 1.30 in, and the width freed here goes to the doughnut in build().
    fig_width, _fig_height = fig.get_size_inches()
    label_x = (1.05 + VARIANT_PLOT_SIZE[0] + 0.30) / fig_width
    #fig.text(label_x, 0.250, "share of\nterminal\ncarbon", ha="left", va="top", fontsize=F1_STACK, fontfamily=FONT, color="black")
    #fig.text(label_x, 0.575, f"{total:,.0f} {T_C}", ha="left", va="center", fontsize=F1_STACK, fontfamily=FONT, fontweight="bold", color="black")
    fig.text(
    label_x,
    0.350,
    f"Total:\n{total:,.0f} {T_C}\nWaste",
    ha="left",
    va="center",
    fontsize=F1_STACK,
    fontfamily=FONT,
    fontweight="bold",
    color="black",
)
    label_y = {"CH$_4$": 0.840, "CO$_2$": 0.730, "Solid Waste": 0.610}
    for endpoint_label, value, _color in zip(endpoint_labels, waste_values_t_c, waste_colors):
        pct = (float(value) / total) * 100
        fig.text(
            label_x,
            label_y[endpoint_label],
            f"{pct:.0f}%\n{endpoint_label.replace('Solid Waste', 'Solid Carbon').replace(' ', chr(10))}",
            ha="left",
            va="center",
            fontsize=F1_STACK,
            fontfamily=FONT,
            fontweight="bold",
            color="black",
        )

    # The explanatory note on eras/bands/slope lives in the figure caption, not on the panel.

    legend_handles = [Patch(facecolor=color, edgecolor="none", label=label) for color, label in zip(waste_colors, labels)]
    ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(0.0, 0.87), frameon=False, prop={"family": FONT, "size": F1_STACK}, handlelength=1.1, handletextpad=0.45)
    return fig

def build() -> None:
    C.check_inputs([C.NUMBERS, C.COLORS] + ([SANKEY_CACHE] if SANKEY_CACHE else []), 1)
    colors = C.read_color_key(C.COLORS)
    # Align every canonical stream node to the shared palette. Vented/exhaled/scrubbed CO2 are all CO2;
    # wet organics, cellulose and CH4 map to their stream colors; solid carbon takes a terminal-solids grey.
    for node in ("Waste CO2 (Vented)", "Exhaled CO2", "Scrubbed CO2"):
        colors[node] = C.SUBSTRATE_COLORS["CO2"]
    colors["Waste Methane (Vented)"] = C.SUBSTRATE_COLORS["CH4"]
    colors["Wet Organics"] = C.SUBSTRATE_COLORS["Wet_Organics"]
    colors["Cellulose"] = C.SUBSTRATE_COLORS["Cellulose"]
    colors["Solid Carbon Waste"] = "#6E6E6E"
    # Plastic streams take polymer-family colors; Sabatier is a process node -> neutral grey.
    colors["Biodegradable Plastic"] = C.SUBSTRATE_COLORS["Polyesters"]
    colors["Non-Biodegradable Plastic"] = C.SUBSTRATE_COLORS["Other"]
    colors["Sabatier"] = C.SUBSTRATE_COLORS["CO2"]
    # Logistics input categories: cool slate ramp graded by lightness. The vivid palette is reserved for the
    # carbon streams, so the inputs read as off-palette; hue ~215 deg is a lane no stream occupies. Within a
    # category the doughnut draws carbon at full tone and non-carbon lightened 72% toward white.
    _slate = {"Food": "#9FB200", "Clothing": "#758C00", "Personal Supplies": "#4E6500", "Packaging": "#2A3800"}

    def _lighten(hex_c: str, frac: float) -> str:
        r, g, b = (int(hex_c.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        return "#{:02X}{:02X}{:02X}".format(*(round(x + (255 - x) * frac) for x in (r, g, b)))
    _other_colors = {
        "Food": "#D0D0D0",
        "Clothing": "#D0D0D0",
        "Personal Supplies": "#D0D0D0",
        "Packaging": "#D0D0D0",
    }

    for _cat, _base in _slate.items():
        colors[_cat] = _base
        colors["Carbon " + _cat] = _base
        colors["Non-Carbon " + _cat] = _other_colors[_cat]
    canvas = C.Canvas(3000, 3170)
    C.place(canvas, make_figure_1_sankey(colors), (80, 40, 2840, 1330))
    #original C.place(canvas, C.render(make_figure_1_stackplot(colors), 0.02), (40, 1420, 1050, 1990))
    #original C.place(canvas, C.render(make_figure_1_doughnut(colors), 0.02), (1160, 1420, 1790, 1716))
    C.place(canvas, C.render(make_figure_1_stackplot(colors), 0.02), (1750, 1320, 1150, 1990))
    
    # The doughnut is given a shorter box than the stackplot so the two panels finish level: it is
    # height-limited in its box, so trimming the box height trims the panel in proportion.
    C.place(canvas, C.render(make_figure_1_doughnut(colors), 0.02), (-100, 1520, 1790, 1600))
    C.save_figure(canvas, 1, width_mm=180)


def main() -> int:
    global SANKEY_CACHE
    parser = argparse.ArgumentParser(description=__doc__)
    C.add_path_arguments(parser, "numbers", "colors")
    parser.add_argument("--sankey-cache", type=Path, default=None, help="Cached Sankey PNG. Omit to render it with plotly.")
    args = parser.parse_args()
    C.configure(NUMBERS=args.numbers, COLORS=args.colors, OUTPUTS=args.output_dir)
    SANKEY_CACHE = args.sankey_cache.expanduser().resolve() if args.sankey_cache else None
    C.apply_rcparams()
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

