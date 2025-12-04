import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np


BEGIN_PATTERN = re.compile(r"^step_(\d{3})begin\.png$")


def find_items(input_dir: Path) -> List[Path]:
    return sorted([p for p in input_dir.iterdir() if p.is_dir() and p.name.startswith("item_")])


def collect_frame_pairs(item_dir: Path) -> List[Tuple[Path, Path]]:
    screenshots_dir = item_dir / "screenshots"
    annotated_dir = item_dir / "annotated"

    if not screenshots_dir.is_dir() or not annotated_dir.is_dir():
        return []

    step_to_begin: Dict[int, Path] = {}
    for f in screenshots_dir.iterdir():
        if not f.is_file():
            continue
        m = BEGIN_PATTERN.match(f.name)
        if m:
            step_num = int(m.group(1))
            step_to_begin[step_num] = f

    pairs: List[Tuple[Path, Path]] = []
    for step in sorted(step_to_begin.keys()):
        begin_path = step_to_begin[step]
        annotated_path = annotated_dir / f"step_{step:03d}.png"
        if annotated_path.is_file():
            pairs.append((begin_path, annotated_path))
    return pairs


def read_image(path: Path) -> Optional[np.ndarray]:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return img


def draw_title(frame: np.ndarray, title: str) -> np.ndarray:
    img = frame.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1.0
    thickness = 2
    (text_w, text_h), baseline = cv2.getTextSize(title, font, scale, thickness)
    pad_x, pad_y = 12, 10
    x, y = 10, 20 + text_h
    box_x2 = x + text_w + pad_x * 2
    box_y2 = y + pad_y

    overlay = img.copy()
    cv2.rectangle(overlay, (x - pad_x, y - text_h - pad_y), (box_x2, box_y2), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)
    cv2.putText(img, title, (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)
    return img


def ensure_writer(output_path: Path, fps: float, size: Tuple[int, int], codec_candidates: Sequence[str]) -> cv2.VideoWriter:
    w, h = size
    for fourcc_str in codec_candidates:
        fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))
        if writer.isOpened():
            print(f"[codec] {output_path.name}: using {fourcc_str}")
            return writer
        else:
            writer.release()
    raise RuntimeError(f"Failed to open VideoWriter for {output_path} with codecs {list(codec_candidates)}")


def write_video(
    frames: Sequence[Path],
    output_path: Path,
    fps: float,
    title_text: Optional[str] = None,
) -> None:
    if not frames:
        return

    first = read_image(frames[0])
    if first is None:
        raise RuntimeError(f"Failed to read first frame: {frames[0]}")
    height, width = first.shape[:2]
    # Choose codecs by container
    suffix = output_path.suffix.lower()
    if suffix == ".avi":
        codec_candidates = ("MJPG", "XVID")
    else:
        codec_candidates = ("mp4v", "avc1")
    writer = ensure_writer(output_path, fps, (width, height), codec_candidates)

    try:
        for fp in frames:
            img = read_image(fp)
            if img is None:
                continue
            if img.shape[1] != width or img.shape[0] != height:
                img = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
            if title_text:
                img = draw_title(img, title_text)
            img = np.ascontiguousarray(img)
            writer.write(img)
    finally:
        writer.release()


def generate_videos(
    input_dir: Path,
    output_dir: Path,
    fps: float,
    overwrite: bool,
    ext: str,
    codec: Optional[str],
    limit: Optional[int],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    items = find_items(input_dir)
    if isinstance(limit, int) and limit > 0:
        items = items[:limit]
    for item_dir in items:
        item_name = item_dir.name
        pairs = collect_frame_pairs(item_dir)
        if not pairs:
            print(f"[skip] {item_name}: no valid (begin, annotated) pairs found")
            continue

        ordered_frames: List[Path] = []
        for begin_path, annotated_path in pairs:
            ordered_frames.append(begin_path)
            ordered_frames.append(annotated_path)

        out_ext = "." + ext.lower().lstrip(".")
        out_path = output_dir / f"{item_name}{out_ext}"
        if out_path.exists() and not overwrite:
            print(f"[skip] {item_name}: {out_path.name} exists (use --overwrite to replace)")
            continue

        print(f"[write] {item_name}: {len(ordered_frames)} frames -> {out_path}")
        if codec:
            # Force a specific codec by temporarily adjusting extension match
            # We pass through write_video which will map by container; if codec is provided,
            # we bypass that by calling ensure_writer directly inside write_video via suffix mapping.
            # To avoid duplicating logic, we create the file here to validate the codec.
            first = read_image(ordered_frames[0])
            if first is None:
                print(f"[skip] {item_name}: cannot read first frame for codec init")
                continue
            height, width = first.shape[:2]
            writer = ensure_writer(out_path, fps, (width, height), (codec,))
            try:
                for fp in ordered_frames:
                    img = read_image(fp)
                    if img is None:
                        continue
                    if img.shape[1] != width or img.shape[0] != height:
                        img = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
                    img = draw_title(img, item_name)
                    img = np.ascontiguousarray(img)
                    writer.write(img)
            finally:
                writer.release()
        else:
            write_video(ordered_frames, out_path, fps=fps, title_text=item_name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose begin+annotated frames into MP4 videos.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(
            "/shared/nas/data/m1/jiateng5/Mini_Word/inference/text_to_image_output/"
            "evaluate_data_combination2,3,4_inference_results"
        ),
        help="Root directory containing item_* folders",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/shared/nas/data/m1/jiateng5/Mini_Word/video_generate"),
        help="Directory to write generated .mp4 files",
    )
    parser.add_argument("--fps", type=float, default=2.0, help="Frames per second for output videos")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output videos")
    parser.add_argument("--ext", choices=["mp4", "avi"], default="mp4", help="Output container/extension")
    parser.add_argument("--codec", type=str, default=None, help="Force a specific fourcc (e.g., MJPG, mp4v, avc1)")
    parser.add_argument("--limit", type=int, default=None, help="Only process first N item_* folders")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_videos(
        args.input_dir,
        args.output_dir,
        fps=args.fps,
        overwrite=bool(args.overwrite),
        ext=args.ext,
        codec=args.codec,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()


