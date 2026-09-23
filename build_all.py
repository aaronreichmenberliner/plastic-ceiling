#!/usr/bin/env python3
"""
Convenience driver: run every figure script in-process and write the checksum manifest.

Holds no figure logic. Each figureN.py is standalone and can be run on its own; this only saves the separate invocations and produces outputs/manifest.json, which a single-figure run does not.

    python build_all.py            # the six main figures and both supplementary figures
    python build_all.py --only 3 4 # a subset, while iterating
"""

from __future__ import annotations

import argparse
import importlib

import common as C

FIGURES = [0, 1, 2, 3, 4, 5]
# Listed in SI order, so the modules build in the sequence their outputs are numbered:
# FigS1 plastics, FigS2 scenario aggregate, FigS3 reactor volumes.
SI_FIGURES = ["figure_plastics_recoverable", "figure_si_scenario", "figure_si_reactor_volumes"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", type=int, nargs="+", choices=FIGURES, help="Rebuild only these figures.")
    args = parser.parse_args()

    C.configure()
    C.apply_rcparams()
    selected = sorted(set(args.only) if args.only else FIGURES)
    for number in selected:
        importlib.import_module(f"figure{number}").build()
    if not args.only:
        for mod in SI_FIGURES:
            importlib.import_module(mod).build()

    sources = [C.NUMBERS, C.WORKBOOK, C.COLORS, C.FIG0, C.FIG2, C.FIG5, C.ROOT / "common.py"]
    sources += [C.ROOT / f"figure{n}.py" for n in FIGURES]
    sources += [C.ROOT / f"{m}.py" for m in SI_FIGURES]
    C.write_manifest(sources)
    built = ", ".join(f"Fig{n}" for n in selected)
    if not args.only:
        built += ", FigS1, FigS2, FigS3"
    print(f"Build complete: {C.rel(C.OUTPUTS)} contains {built} (PNG + PDF)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())