#!/usr/bin/env python3
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src" / "sprites"
OUT_DIR = ROOT / "public" / "sprites"

TARGET_SIZE = 128
PALETTE_COLORS = 24
PIXELATE_FACTOR = 2  # downscale then nearest-upscale to force chunkier clusters

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
    RESAMPLE_NEAREST = Image.Resampling.NEAREST
    QUANTIZE_MEDIANCUT = Image.Quantize.MEDIANCUT
    DITHER_NONE = Image.Dither.NONE
except AttributeError:
    RESAMPLE_LANCZOS = Image.LANCZOS
    RESAMPLE_NEAREST = Image.NEAREST
    QUANTIZE_MEDIANCUT = Image.MEDIANCUT
    DITHER_NONE = Image.NONE

ATLAS_SOURCES = [
    {
        "name": "ruth",
        "atlas": SRC_DIR / "ruth_sheet_repacked.json",
        "sheet": SRC_DIR / "ruth_sheet_repacked.png",
        "out_base": "ruth_sheet_pixel128_c24_i",
        "idle_count": 3,
    },
    {
        "name": "nora",
        "atlas": SRC_DIR / "nora_sheet_repacked.json",
        "sheet": SRC_DIR / "nora_sheet_repacked.png",
        "out_base": "nora_sheet_pixel128_c24_i",
        "idle_count": 6,
    },
]


def sort_frame_keys(keys: List[str]) -> List[str]:
    def key_fn(value: str) -> Tuple[str, int]:
        if "_" not in value:
            return (value, 0)
        prefix, suffix = value.rsplit("_", 1)
        try:
            return (prefix, int(suffix))
        except ValueError:
            return (prefix, 0)

    return sorted(keys, key=key_fn)


def fit_to_cell(frame: Image.Image, size: int) -> Image.Image:
    frame = frame.convert("RGBA")
    src_w, src_h = frame.size
    scale = min(size / src_w, size / src_h)
    dst_w = max(1, int(round(src_w * scale)))
    dst_h = max(1, int(round(src_h * scale)))

    resized = frame.resize((dst_w, dst_h), resample=RESAMPLE_LANCZOS)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - dst_w) // 2
    y = size - dst_h
    canvas.alpha_composite(resized, (x, y))

    if PIXELATE_FACTOR > 1:
        down = max(1, size // PIXELATE_FACTOR)
        canvas = canvas.resize((down, down), resample=RESAMPLE_NEAREST)
        canvas = canvas.resize((size, size), resample=RESAMPLE_NEAREST)

    return canvas


def blend_frame(a: Image.Image, b: Image.Image) -> Image.Image:
    # 50/50 blend creates a simple in-between for AI-generated source motion.
    return Image.blend(a, b, 0.5)


def frame_difference(a: Image.Image, b: Image.Image) -> float:
    sample_a = a.resize((32, 32), resample=RESAMPLE_NEAREST).convert("RGBA")
    sample_b = b.resize((32, 32), resample=RESAMPLE_NEAREST).convert("RGBA")

    pixels_a = sample_a.getdata()
    pixels_b = sample_b.getdata()

    total = 0.0
    for pa, pb in zip(pixels_a, pixels_b):
        rgb_delta = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]) + abs(pa[2] - pb[2])
        alpha_delta = abs(pa[3] - pb[3]) * 2
        total += rgb_delta + alpha_delta

    max_delta = 255 * 5 * (32 * 32)
    return total / max_delta


def interpolation_steps(a: Image.Image, b: Image.Image) -> int:
    # More disparate frames get more in-betweens.
    score = frame_difference(a, b)
    if score >= 0.20:
        return 4
    if score >= 0.14:
        return 3
    if score >= 0.09:
        return 2
    return 1


def quantize_rgba(sheet: Image.Image, colors: int) -> Image.Image:
    alpha = sheet.getchannel("A")
    quantized = sheet.convert("RGB").quantize(
        colors=colors,
        method=QUANTIZE_MEDIANCUT,
        dither=DITHER_NONE,
    )
    out = quantized.convert("RGBA")
    out.putalpha(alpha)
    return out


def make_sequence(
    frames: List[Image.Image],
    prefix: str,
    wrap: bool,
) -> Tuple[List[Tuple[str, Image.Image]], List[str]]:
    sequence: List[Tuple[str, Image.Image]] = []

    for i, frame in enumerate(frames):
        sequence.append((f"{prefix}_{len(sequence):03d}", frame))

        if i < len(frames) - 1:
            next_frame = frames[i + 1]
            steps = interpolation_steps(frame, next_frame)
            for n in range(steps):
                t = (n + 1) / (steps + 1)
                sequence.append((f"{prefix}_{len(sequence):03d}", Image.blend(frame, next_frame, t)))

    if wrap and len(frames) > 1:
        steps = interpolation_steps(frames[-1], frames[0])
        for n in range(steps):
            t = (n + 1) / (steps + 1)
            sequence.append((f"{prefix}_{len(sequence):03d}", Image.blend(frames[-1], frames[0], t)))

    keys = [key for key, _ in sequence]
    return sequence, keys


def build_pixel_atlas(source: Dict[str, object]) -> None:
    atlas_data = json.loads(Path(source["atlas"]).read_text())
    sheet_image = Image.open(Path(source["sheet"])).convert("RGBA")

    frame_keys = sort_frame_keys(list(atlas_data["frames"].keys()))
    idle_count = int(source["idle_count"])

    if idle_count <= 0 or idle_count >= len(frame_keys):
        raise ValueError(f"invalid idle_count for {source['name']}")

    idle_src_keys = frame_keys[:idle_count]
    action_src_keys = frame_keys[idle_count:]

    def extract_pixel_frames(keys: List[str]) -> List[Image.Image]:
        out: List[Image.Image] = []
        for key in keys:
            src_frame = atlas_data["frames"][key]["frame"]
            x, y = src_frame["x"], src_frame["y"]
            w, h = src_frame["w"], src_frame["h"]
            crop = sheet_image.crop((x, y, x + w, y + h))
            out.append(fit_to_cell(crop, TARGET_SIZE))
        return out

    idle_frames = extract_pixel_frames(idle_src_keys)
    action_frames = extract_pixel_frames(action_src_keys)

    idle_sequence, idle_keys = make_sequence(idle_frames, f"{source['name']}_idle", wrap=True)
    action_sequence, action_keys = make_sequence(action_frames, f"{source['name']}_action", wrap=False)

    all_sequence = idle_sequence + action_sequence
    frame_count = len(all_sequence)

    cols = min(8, frame_count)
    rows = math.ceil(frame_count / cols)
    atlas_w = cols * TARGET_SIZE
    atlas_h = rows * TARGET_SIZE

    out_sheet = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))
    out_frames: Dict[str, object] = {}

    for i, (key, frame) in enumerate(all_sequence):
        cell_x = (i % cols) * TARGET_SIZE
        cell_y = (i // cols) * TARGET_SIZE
        out_sheet.alpha_composite(frame, (cell_x, cell_y))

        out_frames[key] = {
            "frame": {"x": cell_x, "y": cell_y, "w": TARGET_SIZE, "h": TARGET_SIZE},
            "rotated": False,
            "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": TARGET_SIZE, "h": TARGET_SIZE},
            "sourceSize": {"w": TARGET_SIZE, "h": TARGET_SIZE},
            "anchorHint": {"x": cell_x + TARGET_SIZE // 2, "y": cell_y + TARGET_SIZE},
        }

    quantized_sheet = quantize_rgba(out_sheet, PALETTE_COLORS)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_png = OUT_DIR / f"{source['out_base']}.png"
    out_json = OUT_DIR / f"{source['out_base']}.json"

    quantized_sheet.save(out_png, format="PNG", optimize=True)

    out_atlas = {
        "frames": out_frames,
        "meta": {
            "image": out_png.name,
            "size": {"w": atlas_w, "h": atlas_h},
            "cols": cols,
            "rows": rows,
            "cell": {"w": TARGET_SIZE, "h": TARGET_SIZE},
            "sequences": {
                "idle": idle_keys,
                "action": action_keys,
            },
            "generated": {
                "pipeline": "split(idle/action)+fit(128x128,bottom-center)+interpolate+nearest-pixelate+quantize",
                "colors": PALETTE_COLORS,
                "pixelateFactor": PIXELATE_FACTOR,
                "idleSourceFrames": len(idle_src_keys),
                "actionSourceFrames": len(action_src_keys),
            },
        },
    }
    out_json.write_text(json.dumps(out_atlas, indent=2) + "\n")

    print(
        f"generated {source['name']}: {out_png.name}, {out_json.name}, "
        f"idle={len(idle_keys)}, action={len(action_keys)}, total={frame_count}"
    )


def main() -> None:
    for source in ATLAS_SOURCES:
        build_pixel_atlas(source)


if __name__ == "__main__":
    main()
