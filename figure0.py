#!/usr/bin/env python3
"""Figure 0: single authored panel (study design). Run `python figure0.py`."""

from __future__ import annotations

import argparse

import common as C


def build() -> None:
    C.check_inputs([C.FIG0], 0)
    # Single authored panel (aspect 1.659); canvas matches the artwork.
    canvas = C.Canvas(3600, 2210)
    C.place(canvas, C.render_svg(C.FIG0), (20, 20, 3560, 2170))
    C.save_figure(canvas, 0, width_mm=180)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    C.add_path_arguments(parser, "fig0")
    args = parser.parse_args()
    C.configure(FIG0=args.fig0, OUTPUTS=args.output_dir)
    C.apply_rcparams()
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())