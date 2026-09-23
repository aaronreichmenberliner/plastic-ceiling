# The Plastic Ceiling: Opportunities and Limitations of Microbial Carbon Recovery in Crewed Spaceflight

## Abstract

Human spaceflight is entering a phase defined by long-duration missions beyond low Earth orbit (LEO), with sustained operations on the Moon and Mars within mission-architecture scope. The International Space Station (ISS) operates under an open-resource model: all consumables are delivered from Earth, used once, and disposed of through atmospheric re-entry or venting. While water and oxygen cycles are substantially closed, virtually all elemental carbon in food, clothing, and packaging is lost, a paradigm incompatible with the autonomy demands of deep-space operations as well as planetary protection protocols. The scale at stake is non-trivial: we estimate that across the ISS's operational history, logistics resupply has carried approx. 87 metric tons of carbon ($\mathrm{t_C}$) to LEO. Microbial biotechnology has repeatedly been proclaimed as a route to carbon-loop closure, both on Earth and in Space. However, the biological up-cycling potential and carbon-recovery capacity of resupply-derived waste streams has never been quantified. A comprehensive system-level carbon mass balance of ISS operations could also be used to size the required bioprocessing infrastructure and project microbial carbon-recovery capacities per crew and time. Here, we deliver an empirical carbon-accounting record that covers 25 years of stable ISS operations. The accompanying parameterizable and target-product-agnostic Bio-Process Sizing Framework (BPSF) converts user-defined operational inputs into projected carbon recovery capacities and required reactor volumes under the universal physical constraints of aqueous bioprocess design, while also supporting parameterization with chassis-specific empirical data, thereby cross-checking what physics permits against what extant biology delivers.

## Publication figure source package
## Publication figure source package

Self-contained source for the manuscript figures (Fig0-Fig5) and the supplementary figures (FigS1-FigS3). The package ships without build products: `python build_all.py` generates every figure into `outputs/`. One script per figure, plus `common.py` for the machinery they share. Each figure script is standalone: `python figure3.py` reads the workbooks it needs, draws its panels, composites them, and writes `outputs/Fig3.{png,pdf}`.

## Build

Python 3.10 or newer. From this directory:

```bash
python -m pip install -r requirements.txt
python build_all.py          # every figure, plus outputs/manifest.json
python figure3.py            # or just one, while iterating
```

`build_all.py` is a convenience driver and holds no figure logic. It imports each `figureN` module, calls its `build()`, and writes the checksum manifest. Running a figure script on its own does not touch the manifest.

### Vector output

Panels are emitted as SVG, composited as SVG, and written out by CairoSVG as both PNG (300 dpi) and PDF. The PDF is vector: curves stay curves, text stays text with subset-embedded fonts, and there is no resolution ceiling. Two rasters survive, by necessity rather than accident: the Figure 1a Sankey (Plotly; embedded as a base64 PNG at ~1.5x the composited pixel width) and the Figure 3c colourbar gradient (a continuous ramp, rasterized by matplotlib's SVG backend). Everything else is paths.

PyMuPDF must not be substituted for CairoSVG: its SVG parser discards `<marker>` arrowheads and `stroke-dasharray`, both of which `fig2a_BPSF_flowchart.svg` relies on.

### Fonts

`common.FONT` resolves the first installed family in `FONT_STACK` — Helvetica, then the metric-compatible clones TeX Gyre Heros and Nimbus Sans, then Liberation Sans, Arial, DejaVu Sans. This matters twice: matplotlib lays text out with that face, and the compositor names it in the SVG, so layout metrics and render metrics agree. Requesting a font that is not installed makes them disagree silently.

Formula subscripts are mathtext (`CO$_2$`), not Unicode `CO₂`: the Helvetica-metric faces have no SUBSCRIPT TWO glyph. Carbon and biomass units follow the same convention — `t_C`, `kg_C`, `kg_biomass` — via the `T_C`, `KG_C`, `KG_BIOMASS` constants in `common.py`.

Authored SVG artwork is not under that constraint, since it is not laid out by matplotlib, so `common.render_svg` repairs it instead: `_normalise_subscripts` rewrites Unicode subscript digits as shifted plain digits, and `_normalise_symbols` re-families any remaining character the body face has no glyph for — `→` in `fig5_bioprocess_sizing_framework.svg`, which Helvetica does not carry — onto the first family in `SYMBOL_STACK` that does. CairoSVG picks one family per run rather than falling back per glyph, so without this such a character renders as a notdef box however many families `FONT_CSS` lists after the first. `_advance` measures those characters from the same fallback face, so centred and right-aligned runs containing one stay centred.

Figure 1's Sankey is a generated panel like any other: `figure1.make_figure_1_sankey` draws it with Plotly and rasterizes it in memory. Kaleido drives a headless Chrome, installed once:

```bash
plotly_get_chrome
```

To build without plotly/kaleido/Chrome, cache the panel once on a machine that has them and pass it back in:

```bash
python -c "import common as C, figure1; C.apply_rcparams(); figure1.make_figure_1_sankey(C.read_color_key(C.COLORS)).save('sankey.png')"
python figure1.py --sankey-cache sankey.png
```

Inputs are validated before any panel is drawn: a figure fails immediately, naming the file it is missing, rather than part-way through compositing. Every input and the output directory can be overridden (no absolute paths are embedded); each script exposes only the flags it consumes:

```bash
python figure2.py --workbook data/bioprocess_sizing_framework.xlsx \
                  --colors data/colors.xlsx \
                  --fig2a assets/fig2a_BPSF_flowchart.svg \
                  --output-dir outputs
```

## Layout

```
common.py          paths + CLI overrides, rendering constants, font resolution,
                   workbook readers, the SVG Canvas and its compositing helpers,
                   manifest writer. Draws nothing.
figure0.py ...     one per figure: type sizes, panel geometry, panel generators,
figure5.py         canvas assembly, and a standalone CLI.
figure_plastics_recoverable.py, figure_si_scenario.py, figure_si_reactor_volumes.py
                   the supplementary figures FigS1, FigS2, FigS3
build_all.py       runs all nine and writes the manifest
requirements.txt   pinned minimum dependencies
data/              quantitative inputs (3 workbooks)
assets/            authored artwork (Fig 0 SVG, Fig 2a SVG, Fig 5 SVG)
outputs/           build products (git-ignored; created by the build, not shipped)
```

Each `figureN.py` follows the same shape: constants, then `make_figure_Nx` panel generators, then `build()` which checks inputs and places panels on the canvas, then `main()`. Panel geometry (canvas size, panel boxes, label positions) lives entirely in `build()`.

Stream colors and organism/process hatches resolve through `common` alone: `common.substrate_color` and `common.route_color` read the shared color key, and `common.organism_hatch` assigns the pattern. No figure defines its own palette or hatch list, so a stream cannot change color between figures. Route identifiers are likewise assigned in one place, from workbook row order, and shared by Figure 3 and the supplementary reactor-volume figure.

Every panel generator returns a matplotlib Figure except `figure1.make_figure_1_sankey`, which returns a PIL image because the Sankey is drawn with Plotly. `common.render` turns a Figure into SVG text; `common.place` accepts SVG text or a PIL image and fits either into a pixel box, preserving aspect and centering.

## Figure-to-source map

| Figure | Panels | Source |
|---|---|---|
| 0 | single | Authored SVG (`fig0_study_design.svg`) |
| 1 | a | `figure1.make_figure_1_sankey` (Plotly) + Figure 1 workbook |
| 1 | b | `figure1.make_figure_1_stackplot` (cumulative terminal waste) + Figure 1 workbook |
| 1 | c | `figure1.make_figure_1_doughnut` + Figure 1 workbook |
| 2 | a | Authored SVG (`fig2a_BPSF_flowchart.svg`) |
| 2 | b | `figure2.make_figure_2_routed_carbon` + sizing workbook |
| 3 | a-c | `figure3._panel_routes`, `_panel_efficiency`, `_panel_volume`, `_panel_key` (one native figure) + sizing workbook |
| 4 | a | `figure4.make_figure_4_carbon_fate` + sizing workbook |
| 4 | b | `figure4.make_figure_4_plastic_fate` + sizing workbook |
| 5 | single | Authored SVG (`fig5_bioprocess_sizing_framework.svg`) |
| S1 | single | `figure_si_scenario` (scenario-level carbon routing and biomass output) + sizing workbook |
| S2 | 2x2 | `figure_si_reactor_volumes` (reactor volume distribution, model x scenario) + sizing workbook |
| S3 | single | `figure_plastics_recoverable` (recoverable vs non-recoverable plastic carbon) + sizing workbook |

No figure carries a panel letter. Where a panel has a title it names itself; elsewhere, and for both supplementary figures, the caption carries the identification. The letters in the table above are reading order only. Generators are named for what they draw rather than for the position they occupy, so a panel can be moved without renaming it. Authored SVG artwork is normalised on the way in by `common.render_svg`, in three steps. Sans-serif `font-family` declarations are repointed at the package stack, so a family that happens not to be installed cannot pull a panel into different letterforms from the rest. Unicode subscript digits are rewritten as plain digits in a shifted `tspan`, because the Helvetica-metric faces carry no subscript glyphs and would otherwise fall back to another family for those characters alone. Centred and right-aligned text that is split across `tspan`s is re-expressed as left-aligned text at an equivalent x, computed from the font's own advance widths: CairoSVG loses part of the advance at a `tspan` boundary when the element is centred, which closes up the words either side of a subscript. Elements whose `tspan`s carry their own absolute position are stacks of separately anchored lines and are left alone.

## Provenance

- `data/numbers.xlsx` supplies the quantitative values for Figure 1 (sheets `Figure 1A`, `Figure 1B`, `Figure 1C`). Sheet names follow the panel letters: `Figure 1A` is the Sankey flow table, in kg_C per person-year and therefore independent of the mission basis; `Figure 1B` is the lifetime terminal carbon drawn as panel b; `Figure 1C` is the lifetime uplinked mass drawn as panel c. Figures 1B and 1C are reported on a mission basis of 132.50 person-years (time-weighted mean crew 5.29 over 25.05 years), which is also the basis of the `ISS_ERAS` table in `figure1.py` that sets the panel-b band shape; the two must stay in step. The Sankey's node labels are derived from the `Figure 1A` flow table and its node colors from `colors.xlsx`, so neither can drift from the data.
- `data/bioprocess_sizing_framework.xlsx` supplies the quantitative values for Figures 2-4 (sheets `Inputs`, `Scenarios`, `Routing`).
- `data/colors.xlsx` is the shared color and pattern key (sheet `Figure Color Key`). Its other three sheets are not read by any script but are kept: `Okabe-Ito palette` is the derivation every tint in the key comes from, and deleting it would destroy provenance that the hex codes alone do not carry.
- `assets/fig0_study_design.svg` is the authored Figure 0.
- `assets/fig2a_BPSF_flowchart.svg` is the authored Figure 2a.
- `assets/fig5_bioprocess_sizing_framework.svg` is the authored Figure 5.

The spreadsheets retain formulas and their cached results. Cached values are read with `openpyxl`; if formulas are changed, recalculate and save the workbook in Excel or LibreOffice before rebuilding.