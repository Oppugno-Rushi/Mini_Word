#!/usr/bin/env python3
"""
Draw a red bounding box on an image.

Usage examples:

1) With individual fields:
   python add_bbox_on_image.py /path/to/img.png --x 180 --y 577 --width 78 --height 34

2) With explicit right/bottom:
   python add_bbox_on_image.py /path/to/img.png --x 180 --y 577 --right 258 --bottom 611

3) With a JSON string or file path (same keys as trajectory.json):
   python add_bbox_on_image.py /path/to/img.png --bbox-json '{"x":180,"y":577,"width":78,"height":34,"right":258,"bottom":611}'
   python add_bbox_on_image.py /path/to/img.png --bbox-json /path/to/bbox.json

Outputs the image with a red rectangle to <name>_bbox<ext> unless --out is provided.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Dict, Optional, Tuple

try:
    from PIL import Image, ImageDraw
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "Pillow (PIL) is required. Install with: pip install pillow\n"
        f"Import error: {exc}"
    )

# Note: We implement bbox drawing directly to avoid dependency on collect_functional_tree

# Defaults for quick use with your provided image and bbox
DEFAULT_IMAGE = \
    "/shared/nas/data/m1/jiateng5/Mini_Word/function_tree_10/format/highlight/Back_to_Format/begin.png"
DEFAULT_BBOX_JSON = (
    '{"x": 192,"y": 536,"width": 129,"height": 61}'
)


def _parse_bbox_from_json_arg(bbox_json_arg: str) -> Dict[str, int]:
    """Parse a bbox from a JSON string or a file path to JSON."""
    if os.path.exists(bbox_json_arg) and os.path.isfile(bbox_json_arg):
        with open(bbox_json_arg, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.loads(bbox_json_arg)
    return {k: int(data[k]) for k in data if k in {"x", "y", "width", "height", "right", "bottom"}}


def _normalize_bbox(bbox: Dict[str, int], image_size: Tuple[int, int]) -> Tuple[int, int, int, int]:
    """Return a normalized (left, top, right, bottom) tuple within image bounds.

    Accepts keys: x, y, width, height, right, bottom.
    Prefers explicit right/bottom if present; otherwise computes from width/height.
    The dataset pattern uses right = x + width and bottom = y + height.
    """
    if "x" not in bbox or "y" not in bbox:
        raise ValueError("bbox must include 'x' and 'y'.")

    x = int(bbox["x"])  # left
    y = int(bbox["y"])  # top

    if "right" in bbox:
        right = int(bbox["right"])
    elif "width" in bbox:
        right = x + int(bbox["width"])  # matches provided pattern
    else:
        raise ValueError("bbox needs either 'right' or 'width'.")

    if "bottom" in bbox:
        bottom = int(bbox["bottom"])
    elif "height" in bbox:
        bottom = y + int(bbox["height"])  # matches provided pattern
    else:
        raise ValueError("bbox needs either 'bottom' or 'height'.")

    img_w, img_h = image_size

    # Clamp to image bounds
    x = max(0, min(x, img_w - 1))
    y = max(0, min(y, img_h - 1))
    right = max(0, min(right, img_w - 1))
    bottom = max(0, min(bottom, img_h - 1))

    # Ensure ordering
    left = min(x, right)
    top = min(y, bottom)
    right = max(x, right)
    bottom = max(y, bottom)

    return left, top, right, bottom


def draw_bbox_on_image(
    image_path: str,
    bbox: Dict[str, int],
    output_path: Optional[str] = None,
    color: Tuple[int, int, int] = (255, 0, 0),
    thickness: int = 4,
) -> str:
    """Draw a bounding box on an image and save it.
    
    Uses a fixed red outline (width=4) to match collect_functional_tree.py behavior.
    """
    # Ensure we have right/bottom values
    with Image.open(image_path) as im:
        left, top, right, bottom = _normalize_bbox(bbox, im.size)
        
        # Draw the rectangle on the image
        draw = ImageDraw.Draw(im)
        # Use red outline with width=4 to match collect_functional_tree behavior
        draw.rectangle([left, top, right, bottom], outline='red', width=4)
        
        # Determine output path
        if not output_path:
            # Build default output path under out-dir using the source filename
            src_name = os.path.basename(image_path)
            name, ext = os.path.splitext(src_name)
            out_dir = os.environ.get("ADD_BBOX_OUT_DIR", "./test_bbox")
            os.makedirs(out_dir, exist_ok=True)
            output_path = os.path.join(out_dir, f"{name}_bbox{ext or '.png'}")
        
        # Save the image
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        im.save(output_path)
    
    return output_path


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Draw a red bounding box on an image.")
    p.add_argument(
        "image",
        nargs="?",
        default=DEFAULT_IMAGE,
        help="Path to input image (default: preset path)",
    )
    p.add_argument("--out", dest="out", help="Path to save single output image (overrides --out-dir)")
    p.add_argument(
        "--out-dir",
        dest="out_dir",
        default="/shared/nas/data/m1/jiateng5/Mini_Word/training_data_image/test_bbox",
        help="Directory to save output image(s) (default: /shared/nas/data/m1/jiateng5/Mini_Word/training_data_image/test_bbox)",
    )
    # Either provide JSON (string or file path) or individual fields
    p.add_argument(
        "--bbox-json",
        dest="bbox_json",
        default=DEFAULT_BBOX_JSON,
        help="JSON string or file path with keys x,y,width,height,right,bottom (default: preset bbox)",
    )
    p.add_argument("--x", type=int, help="Left (x) coordinate")
    p.add_argument("--y", type=int, help="Top (y) coordinate")
    p.add_argument("--width", type=int, help="Box width")
    p.add_argument("--height", type=int, help="Box height")
    p.add_argument("--right", type=int, help="Right coordinate (x + width)")
    p.add_argument("--bottom", type=int, help="Bottom coordinate (y + height)")
    p.add_argument("--thickness", type=int, default=2, help="Rectangle outline thickness (default: 2)")
    return p


def _collect_bbox_from_args(args: argparse.Namespace) -> Dict[str, int]:
    if args.bbox_json:
        return _parse_bbox_from_json_arg(args.bbox_json)

    fields = {}
    for k in ("x", "y", "width", "height", "right", "bottom"):
        v = getattr(args, k)
        if v is not None:
            fields[k] = int(v)

    if not fields:
        raise SystemExit(
            "You must provide either --bbox-json or some of --x --y --width/--right --height/--bottom"
        )
    return fields


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    bbox = _collect_bbox_from_args(args)
    # Allow --out to override, otherwise use --out-dir via env to influence default path
    if not args.out:
        os.environ["ADD_BBOX_OUT_DIR"] = args.out_dir
    out_path = draw_bbox_on_image(args.image, bbox, output_path=args.out, thickness=args.thickness)
    print(out_path)


if __name__ == "__main__":
    main()


