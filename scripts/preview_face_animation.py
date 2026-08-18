#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image

from make_face_animation import (
    FRAME_COUNT,
    fit_frame,
    sample_frames,
    write_preview_gif,
    write_preview_sheet,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview the 8-frame OLED animation generated from an image.")
    parser.add_argument("input", help="source image file")
    parser.add_argument("--name", default="preview")
    parser.add_argument("--mode", choices=["auto", "gif", "strip", "static"], default="auto")
    parser.add_argument("--threshold", type=int, default=128)
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--open", action="store_true", help="open the generated GIF with the system opener")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_dir = root / "generated_previews"
    out_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(args.input)
    if args.mode == "static":
        frames = [img.convert("RGBA")] * FRAME_COUNT
    else:
        frames = sample_frames(img, args.mode)
    frames = [fit_frame(frame, args.invert, args.threshold) for frame in frames]

    gif_path = out_dir / f"{args.name}.gif"
    png_path = out_dir / f"{args.name}.png"
    write_preview_gif(gif_path, frames)
    write_preview_sheet(png_path, frames)

    print(gif_path)
    print(png_path)

    if args.open:
        opener = None
        if sys.platform == "darwin":
            opener = ["open", str(gif_path)]
        elif sys.platform.startswith("linux"):
            opener = ["xdg-open", str(gif_path)]
        if opener:
            subprocess.Popen(opener)


if __name__ == "__main__":
    main()
