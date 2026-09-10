#!/usr/bin/env python3
"""Figure 5: single authored panel (bioprocess sizing framework). Run `python figure5.py`."""

from __future__ import annotations

import argparse

import common as C


def build() -> None:
    C.check_inputs([C.FIG5], 5)
    # Single authored schematic (aspect 1.320); canvas matches the artwork.
    canvas = C.Canvas(3200, 2420)
    C.place(canvas, C.render_svg(C.FIG5), (20, 20, 3160, 2380))
    C.save_figure(canvas, 5, width_mm=180)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    C.add_path_arguments(parser, "fig5")
    args = parser.parse_args()
    C.configure(FIG5=args.fig5, OUTPUTS=args.output_dir)
    C.apply_rcparams()
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())