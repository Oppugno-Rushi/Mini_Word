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
    "/shared/nas/data/m1/jiateng5/Mini_Word/function_tree_12/format/highlight/Back_to_Format/begin.png"
DEFAULT_BBOX_JSON = (
    '{"x_topleft": 192,"y_topleft": 536,"x_bottomright": 321,"y_bottomright": 597}'
)


def _parse_bbox_from_json_arg(bbox_json_arg: str) -> Dict[str, int]:
    """Parse a bbox from a JSON string or a file path to JSON.
    
    Uses new format: x_topleft, y_topleft, x_bottomright, y_bottomright
    """
    if os.path.exists(bbox_json_arg) and os.path.isfile(bbox_json_arg):
        with open(bbox_json_arg, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.loads(bbox_json_arg)
    
    # Extract new format keys only
    new_keys = {"x_topleft", "y_topleft", "x_bottomright", "y_bottomright"}
    result = {}
    for k in data:
        if k in new_keys:
            result[k] = int(data[k])
    
    return result


def _normalize_bbox(bbox: Dict[str, int], image_size: Tuple[int, int]) -> Tuple[int, int, int, int]:
    """Return a normalized (left, top, right, bottom) tuple within image bounds.

    Uses new format: x_topleft, y_topleft, x_bottomright, y_bottomright
    """
    img_w, img_h = image_size
    
    # Use new format directly (x_topleft, y_topleft, x_bottomright, y_bottomright)
    if "x_topleft" in bbox and "y_topleft" in bbox and "x_bottomright" in bbox and "y_bottomright" in bbox:
        left = int(bbox["x_topleft"])
        top = int(bbox["y_topleft"])
        right = int(bbox["x_bottomright"])
        bottom = int(bbox["y_bottomright"])
    else:
        raise ValueError("bbox must use new format: x_topleft, y_topleft, x_bottomright, y_bottomright")

    # Clamp to image bounds
    left = max(0, min(left, img_w - 1))
    top = max(0, min(top, img_h - 1))
    right = max(0, min(right, img_w - 1))
    bottom = max(0, min(bottom, img_h - 1))

    # Ensure ordering
    left = min(left, right)
    top = min(top, bottom)
    right = max(left, right)
    bottom = max(top, bottom)

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
    p.add_argument(
        "--out",
        dest="out",
        default="/shared/nas/data/m1/jiateng5/Mini_Word/training_data_image/test_bbox/begin_bbox5.png",
        help="Path to save single output image (overrides --out-dir and default naming)",
    )
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
        help="JSON string or file path with keys x_topleft,y_topleft,x_bottomright,y_bottomright",
    )
    # New format parameters
    p.add_argument("--x-topleft", type=int, dest="x_topleft", help="Top-left x coordinate")
    p.add_argument("--y-topleft", type=int, dest="y_topleft", help="Top-left y coordinate")
    p.add_argument("--x-bottomright", type=int, dest="x_bottomright", help="Bottom-right x coordinate")
    p.add_argument("--y-bottomright", type=int, dest="y_bottomright", help="Bottom-right y coordinate")
    p.add_argument("--thickness", type=int, default=2, help="Rectangle outline thickness (default: 2)")
    return p


def _collect_bbox_from_args(args: argparse.Namespace) -> Dict[str, int]:
    if args.bbox_json:
        return _parse_bbox_from_json_arg(args.bbox_json)

    fields = {}
    # Use new format only
    new_format_keys = ("x_topleft", "y_topleft", "x_bottomright", "y_bottomright")
    
    for k in new_format_keys:
        v = getattr(args, k, None)
        if v is not None:
            fields[k] = int(v)

    if not fields:
        raise SystemExit(
            "You must provide either --bbox-json or coordinate fields:\n"
            "  --x-topleft --y-topleft --x-bottomright --y-bottomright"
        )
    return fields


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    bbox = _collect_bbox_from_args(args)
    # Use --out if provided, otherwise use --out-dir via env to influence default path
    if args.out:
        output_path = args.out
    else:
        os.environ["ADD_BBOX_OUT_DIR"] = args.out_dir
        output_path = None  # Let draw_bbox_on_image use default naming
    out_path = draw_bbox_on_image(args.image, bbox, output_path=output_path, thickness=args.thickness)
    print(out_path)


if __name__ == "__main__":
    main()


