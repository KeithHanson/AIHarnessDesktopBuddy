#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from PIL import Image, ImageOps, ImageSequence

WIDTH = 128
HEIGHT = 64
FRAME_COUNT = 8


def sample_frames(img: Image.Image, mode: str) -> List[Image.Image]:
    if mode == "gif" or (mode == "auto" and getattr(img, "is_animated", False)):
        frames = [frame.copy().convert("RGBA") for frame in ImageSequence.Iterator(img)]
        if not frames:
            raise ValueError("no frames found in animated image")
        if len(frames) == 1:
            return frames * FRAME_COUNT
        picks = []
        for i in range(FRAME_COUNT):
            idx = round(i * (len(frames) - 1) / max(1, FRAME_COUNT - 1))
            picks.append(frames[idx])
        return picks

    if mode == "strip" or (mode == "auto" and img.width % FRAME_COUNT == 0 and img.width > img.height):
        frame_w = img.width // FRAME_COUNT
        return [img.crop((i * frame_w, 0, (i + 1) * frame_w, img.height)).convert("RGBA") for i in range(FRAME_COUNT)]

    return [img.convert("RGBA")] * FRAME_COUNT


def fit_frame(frame: Image.Image, invert: bool, threshold: int) -> Image.Image:
    bg = Image.new("L", (WIDTH, HEIGHT), 0)
    gray = frame.convert("L")
    fitted = ImageOps.contain(gray, (WIDTH, HEIGHT))
    x = (WIDTH - fitted.width) // 2
    y = (HEIGHT - fitted.height) // 2
    bg.paste(fitted, (x, y))
    if invert:
        bg = ImageOps.invert(bg)
    bw = bg.point(lambda p: 255 if p >= threshold else 0, mode="1")
    return bw


def pack_mono_vlsb(img: Image.Image) -> bytes:
    if img.size != (WIDTH, HEIGHT):
        raise ValueError("frame must be 128x64")
    out = bytearray(WIDTH * HEIGHT // 8)
    pixels = img.load()
    idx = 0
    for page in range(HEIGHT // 8):
        y0 = page * 8
        for x in range(WIDTH):
            b = 0
            for bit in range(8):
                if pixels[x, y0 + bit]:
                    b |= 1 << bit
            out[idx] = b
            idx += 1
    return bytes(out)


def write_module(out_path: Path, name: str, description: str, packed_frames: List[bytes]) -> None:
    frames_hex = ",\n    ".join(f'bytes.fromhex("{frame.hex()}")' for frame in packed_frames)
    out_path.write_text(
        f"NAME = {name!r}\n"
        f"DESCRIPTION = {description!r}\n"
        f"WIDTH = {WIDTH}\n"
        f"HEIGHT = {HEIGHT}\n"
        f"FRAMES = [\n    {frames_hex}\n]\n"
    )


def rebuild_registry(generated_dir: Path) -> None:
    modules = sorted(p.stem for p in generated_dir.glob("*.py") if p.name != "__init__.py")
    lines = []
    for mod in modules:
        lines.append(f"from . import {mod} as _{mod}")
    lines.append("")
    lines.append("GENERATED_FACES = {")
    for mod in modules:
        lines.append(
            f"    {mod!r}: {{'name': _{mod}.NAME, 'description': _{mod}.DESCRIPTION, 'frames': _{mod}.FRAMES, 'width': _{mod}.WIDTH, 'height': _{mod}.HEIGHT}},"
        )
    lines.append("}")
    lines.append("")
    (generated_dir / "__init__.py").write_text("\n".join(lines))


def write_preview_sheet(out_path: Path, frames: List[Image.Image]) -> None:
    sheet = Image.new("1", (WIDTH * FRAME_COUNT, HEIGHT), 0)
    for i, frame in enumerate(frames):
        sheet.paste(frame, (i * WIDTH, 0))
    sheet.save(out_path)


def write_preview_gif(out_path: Path, frames: List[Image.Image], duration_ms: int = 80) -> None:
    seq = [frame.convert("P") for frame in frames]
    seq[0].save(
        out_path,
        save_all=True,
        append_images=seq[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an 8-frame OLED face animation from an image file.")
    parser.add_argument("input", help="source image file (gif/webp/png/jpg/etc)")
    parser.add_argument("--name", required=True, help="face name / module name, e.g. wink")
    parser.add_argument("--description", default="Generated face animation.")
    parser.add_argument("--mode", choices=["auto", "gif", "strip", "static"], default="auto")
    parser.add_argument("--threshold", type=int, default=128)
    parser.add_argument("--invert", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    generated_dir = root / "device" / "buddy" / "generated_faces"
    preview_dir = root / "generated_previews"
    generated_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    name = args.name.strip().lower().replace("-", "_").replace(" ", "_")
    img = Image.open(args.input)
    mode = args.mode
    if mode == "static":
        frames = [img.convert("RGBA")] * FRAME_COUNT
    else:
        frames = sample_frames(img, mode)
    frames = [fit_frame(frame, args.invert, args.threshold) for frame in frames]
    packed = [pack_mono_vlsb(frame) for frame in frames]

    write_module(generated_dir / f"{name}.py", name, args.description, packed)
    rebuild_registry(generated_dir)
    write_preview_sheet(preview_dir / f"{name}.png", frames)
    write_preview_gif(preview_dir / f"{name}.gif", frames)

    print(f"wrote module: {generated_dir / (name + '.py')}")
    print(f"updated registry: {generated_dir / '__init__.py'}")
    print(f"wrote preview sheet: {preview_dir / (name + '.png')}")
    print(f"wrote preview gif: {preview_dir / (name + '.gif')}")


if __name__ == "__main__":
    main()
