import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
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


def _check_cmd(cmd: str) -> bool:
    return shutil.which(cmd) is not None


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


def write_video_frames(
    frames_with_counts: Sequence[Tuple[Path, int]],
    output_path: Path,
    fps: float,
    title_text: Optional[str] = None,
) -> None:
    if not frames_with_counts:
        return

    first = read_image(frames_with_counts[0][0])
    if first is None:
        raise RuntimeError(f"Failed to read first frame: {frames_with_counts[0][0]}")
    height, width = first.shape[:2]
    suffix = output_path.suffix.lower()
    if suffix == ".avi":
        codec_candidates = ("MJPG", "XVID")
    else:
        codec_candidates = ("mp4v", "avc1")
    writer = ensure_writer(output_path, fps, (width, height), codec_candidates)

    try:
        for fp, count in frames_with_counts:
            img = read_image(fp)
            if img is None:
                continue
            if img.shape[1] != width or img.shape[0] != height:
                img = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
            if title_text:
                img = draw_title(img, title_text)
            img = np.ascontiguousarray(img)
            for _ in range(max(1, int(count))):
                writer.write(img)
    finally:
        writer.release()


# -------------------- Answer parsing & TTS --------------------


def extract_numbered_lines(answer: str) -> List[str]:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", answer, flags=re.IGNORECASE)
    cleaned = cleaned.replace("\r", "")
    steps: List[str] = []
    for ln in cleaned.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        m = re.match(r"^(\s*\d+)[\.)\u3001\uff0e\uff09]?\s*(.+)$", ln)
        if m:
            num = re.sub(r"\D", "", m.group(1))
            steps.append(f"{num}. {m.group(2)}")
    return steps


def load_all_steps(json_path: Path) -> List[List[str]]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    all_steps: List[List[str]] = []
    if isinstance(data, list):
        for obj in data:
            answer = ""
            if isinstance(obj, dict):
                answer = str(obj.get("answer", "") or "")
            else:
                answer = str(obj)
            steps = extract_numbered_lines(answer)
            all_steps.append(steps)
    else:
        # Fallback: single object
        answer = ""
        if isinstance(data, dict):
            answer = str(data.get("answer", "") or "")
        else:
            answer = str(data)
        all_steps.append(extract_numbered_lines(answer))
    return all_steps


def format_step_tts(text_line: str) -> Tuple[int, str]:
    m = re.match(r"^(\d+)\.\s*(.+)$", text_line.strip())
    if m:
        n = int(m.group(1))
        content = m.group(2).strip()
        # Normalize quotes and spacing a bit
        content = re.sub(r"\s+", " ", content)
        # Avoid double trailing period
        spoken = f"Step {n}: {content}"
        return n, spoken
    return 0, text_line.strip()


def tts_espeak(text: str, out_wav: Path, voice: Optional[str] = None) -> bool:
    exe = None
    for name in ("espeak-ng", "espeak"):
        if _check_cmd(name):
            exe = name
            break
    if exe is None:
        return False
    args = [exe, "-w", str(out_wav)]
    if voice:
        args += ["-v", voice]
    args += [text]
    try:
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_wav.exists()
    except Exception:
        return False


def tts_pyttsx3(text: str, out_wav: Path, voice: Optional[str] = None) -> bool:
    try:
        import pyttsx3  # type: ignore
    except Exception:
        return False
    try:
        engine = pyttsx3.init()
        if voice:
            try:
                voices = engine.getProperty("voices")
                for v in voices:
                    if voice.lower() in (str(v.name).lower(), str(v.id).lower()):
                        engine.setProperty("voice", v.id)
                        break
            except Exception:
                pass
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        engine.save_to_file(text, str(out_wav))
        engine.runAndWait()
        return out_wav.exists()
    except Exception:
        return False


def tts_gtts(text: str, out_wav: Path) -> bool:
    try:
        from gtts import gTTS  # type: ignore
    except Exception:
        return False
    try:
        with tempfile.TemporaryDirectory() as td:
            mp3_path = Path(td) / "seg.mp3"
            tts = gTTS(text)
            tts.save(str(mp3_path))
            # Convert to WAV with ffmpeg
            if not _check_cmd("ffmpeg"):
                return False
            args = [
                "ffmpeg",
                "-y",
                "-i",
                str(mp3_path),
                "-ar",
                "22050",
                "-ac",
                "1",
                str(out_wav),
            ]
            subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_wav.exists()
    except Exception:
        return False


def synthesize_tts(text: str, out_wav: Path, tts: str, voice: Optional[str]) -> bool:
    # Backend selection with basic diagnostics
    def _has_espeak() -> bool:
        return _check_cmd("espeak-ng") or _check_cmd("espeak")

    def _has_pyttsx3() -> bool:
        try:
            import pyttsx3  # type: ignore
            return True
        except Exception:
            return False

    def _has_gtts() -> bool:
        try:
            import gtts  # type: ignore
            return True
        except Exception:
            return False

    def _has_ffmpeg() -> bool:
        return _check_cmd("ffmpeg")

    if tts in ("espeak", "espeak-ng"):
        ok = tts_espeak(text, out_wav, voice)
        if not ok:
            if not _has_espeak():
                print("[diag] espeak/espeak-ng not found in PATH")
        return ok
    if tts == "pyttsx3":
        ok = tts_pyttsx3(text, out_wav, voice)
        if not ok:
            if not _has_pyttsx3():
                print("[diag] pyttsx3 not installed in Python environment")
        return ok
    if tts == "gtts":
        ok = tts_gtts(text, out_wav)
        if not ok:
            missing = []
            if not _has_gtts():
                missing.append("gTTS package")
            if not _has_ffmpeg():
                missing.append("ffmpeg")
            if missing:
                print(f"[diag] gTTS path requires: {', '.join(missing)}")
            else:
                print("[diag] gTTS synthesis failed (possible network issue)")
        return ok
    # auto fallback chain
    ok = False
    if _has_espeak():
        ok = ok or tts_espeak(text, out_wav, voice)
    else:
        print("[diag] espeak/espeak-ng not found in PATH")
    if not ok:
        if _has_pyttsx3():
            ok = ok or tts_pyttsx3(text, out_wav, voice)
        else:
            print("[diag] pyttsx3 not installed in Python environment")
    if not ok:
        if _has_gtts():
            if not _has_ffmpeg():
                print("[diag] ffmpeg not found; required to convert gTTS MP3 to WAV")
            ok = ok or tts_gtts(text, out_wav)
        else:
            print("[diag] gTTS package not installed")
    return ok


def wav_duration_seconds(path: Path) -> float:
    import wave
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
    if rate <= 0:
        return 0.0
    return float(frames) / float(rate)


def concat_wavs_ffmpeg(inputs: Sequence[Path], out_wav: Path) -> bool:
    if not inputs:
        return False
    if not _check_cmd("ffmpeg"):
        print("[ffmpeg] not found; cannot concat audio")
        return False
    with tempfile.TemporaryDirectory() as td:
        list_path = Path(td) / "files.txt"
        list_path.write_text("\n".join([f"file '{p.as_posix()}'" for p in inputs]), encoding="utf-8")
        args = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            str(out_wav),
        ]
        try:
            subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return out_wav.exists()
        except Exception:
            return False


def mux_audio_into_video(video_path: Path, audio_wav: Path, out_path: Path) -> bool:
    if not _check_cmd("ffmpeg"):
        print("[ffmpeg] not found; cannot mux audio")
        return False
    args = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_wav),
        "-c:v",
        "copy",
        "-c:a",
        "pcm_s16le",
        "-shortest",
        str(out_path),
    ]
    try:
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_path.exists()
    except Exception:
        return False


@dataclass
class BuildResult:
    video_no_audio: Path
    audio_wav: Path
    video_with_audio: Path


def build_video_with_sound_for_item(
    item_dir: Path,
    steps: List[str],
    output_dir: Path,
    fps: float,
    tts_backend: str,
    voice: Optional[str],
    ext: str,
    title_text: Optional[str] = None,
) -> Optional[BuildResult]:
    pairs = collect_frame_pairs(item_dir)
    if not pairs:
        print(f"[skip] {item_dir.name}: no (begin, annotated) pairs found")
        return None

    # Align counts
    max_pairs = len(pairs)
    step_lines: List[str] = [s for s in steps if s.strip()]
    if not step_lines:
        print(f"[skip] {item_dir.name}: no steps parsed from answers")
        return None
    if len(step_lines) > max_pairs:
        step_lines = step_lines[:max_pairs]

    # Synthesize per-step wav and compute durations
    tmp_audio_dir = output_dir / "_tmp_audio" / item_dir.name
    tmp_audio_dir.mkdir(parents=True, exist_ok=True)

    seg_wavs: List[Path] = []
    seg_durations: List[float] = []
    for idx, line in enumerate(step_lines, start=1):
        _, spoken = format_step_tts(line)
        seg_path = tmp_audio_dir / f"step_{idx:03d}.wav"
        ok = synthesize_tts(spoken, seg_path, tts_backend, voice)
        if not ok:
            print(f"[warn] {item_dir.name}: TTS failed for step {idx}; inserting 0.8s silence")
            # Generate short silence via ffmpeg
            if _check_cmd("ffmpeg"):
                try:
                    subprocess.run([
                        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
                        "-t", "0.8", str(seg_path)
                    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
        if seg_path.exists():
            seg_wavs.append(seg_path)
            try:
                seg_durations.append(wav_duration_seconds(seg_path))
            except Exception:
                seg_durations.append(1.0)
        else:
            # fallback duration if neither TTS nor silence worked
            seg_durations.append(1.0)

    # Build frames with repetition per segment duration to match audio
    frames_with_counts: List[Tuple[Path, int]] = []
    for (begin_fp, annotated_fp), dur in zip(pairs, seg_durations):
        total_frames = max(2, int(math.ceil(dur * fps)))
        begin_count = max(1, total_frames // 2)
        annotated_count = max(1, total_frames - begin_count)
        frames_with_counts.append((begin_fp, begin_count))
        frames_with_counts.append((annotated_fp, annotated_count))

    out_ext = "." + ext.lower().lstrip(".")
    output_dir.mkdir(parents=True, exist_ok=True)
    # Use a temporary silent video path and temporary concatenated audio path inside tmp dir
    tmp_dir = output_dir / "_tmp_video" / item_dir.name
    tmp_dir.mkdir(parents=True, exist_ok=True)
    video_no_audio = tmp_dir / f"{item_dir.name}.silent{out_ext}"
    audio_wav = tmp_dir / f"{item_dir.name}.wav"
    video_with_audio = output_dir / f"{item_dir.name}{out_ext}"

    # Write video without audio first (temporary)
    write_video_frames(frames_with_counts, video_no_audio, fps=fps, title_text=title_text or item_dir.name)

    # Concat audio segments to a temporary wav
    ok_concat = concat_wavs_ffmpeg(seg_wavs, audio_wav)
    if not ok_concat:
        print(f"[warn] {item_dir.name}: audio concat failed; leaving silent video at {video_with_audio}")
        # Move silent video to final destination if audio failed
        try:
            if video_with_audio.exists():
                video_with_audio.unlink()
        except Exception:
            pass
        try:
            shutil.move(str(video_no_audio), str(video_with_audio))
        except Exception:
            pass
        # Cleanup temporary per-step wavs
        try:
            for p in seg_wavs:
                if p.exists():
                    p.unlink()
            # remove tmp directories if empty
            for d in (tmp_audio_dir, tmp_dir):
                try:
                    if d.exists():
                        d.rmdir()
                except Exception:
                    pass
        except Exception:
            pass
        return BuildResult(video_no_audio=video_no_audio, audio_wav=audio_wav, video_with_audio=video_with_audio)

    # Mux to final destination
    ok_mux = mux_audio_into_video(video_no_audio, audio_wav, video_with_audio)
    if not ok_mux:
        print(f"[warn] {item_dir.name}: mux failed; delivering silent video")
        try:
            if video_with_audio.exists():
                video_with_audio.unlink()
        except Exception:
            pass
        try:
            shutil.move(str(video_no_audio), str(video_with_audio))
        except Exception:
            pass
    # Cleanup temporary files (silent video, concatenated wav, and per-step wavs)
    try:
        if video_no_audio.exists():
            video_no_audio.unlink()
    except Exception:
        pass
    try:
        if audio_wav.exists():
            audio_wav.unlink()
    except Exception:
        pass
    for p in seg_wavs:
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass
    # Try removing tmp dirs if empty
    for d in (tmp_audio_dir, tmp_dir):
        try:
            if d.exists():
                d.rmdir()
        except Exception:
            pass
    return BuildResult(video_no_audio=video_no_audio, audio_wav=audio_wav, video_with_audio=video_with_audio)


def generate_videos_with_sound(
    input_dir: Path,
    json_path: Path,
    output_dir: Path,
    fps: float,
    overwrite: bool,
    ext: str,
    tts_backend: str,
    voice: Optional[str],
    limit: Optional[int],
) -> None:
    # One-time environment diagnostics
    def _env_diag() -> None:
        has_es = _check_cmd("espeak-ng") or _check_cmd("espeak")
        try:
            import pyttsx3  # type: ignore
            has_p3 = True
        except Exception:
            has_p3 = False
        try:
            import gtts  # type: ignore
            has_gt = True
        except Exception:
            has_gt = False
        has_ff = _check_cmd("ffmpeg")
        print(
            f"[env] tts={tts_backend} | espeak={has_es} pyttsx3={has_p3} gtts={has_gt} ffmpeg={has_ff}"
        )

    _env_diag()

    output_dir.mkdir(parents=True, exist_ok=True)
    items = find_items(input_dir)
    if isinstance(limit, int) and limit > 0:
        items = items[:limit]

    all_steps = load_all_steps(json_path)

    for idx, item_dir in enumerate(items):
        item_name = item_dir.name
        steps: List[str] = []
        if idx < len(all_steps):
            steps = all_steps[idx]
        if not steps:
            print(f"[skip] {item_name}: no steps found in JSON entry {idx+1}")
            continue

        out_path = output_dir / f"{item_name}.{ext}"
        if out_path.exists() and not overwrite:
            print(f"[skip] {item_name}: {out_path.name} exists (use --overwrite to replace)")
            continue

        print(f"[write] {item_name}: {len(steps)} steps, tts={tts_backend}, fps={fps}")
        res = build_video_with_sound_for_item(
            item_dir,
            steps,
            output_dir=output_dir,
            fps=fps,
            tts_backend=tts_backend,
            voice=voice,
            ext=ext,
            title_text=item_name,
        )
        if res and res.video_with_audio.exists():
            print(f"[ok] {item_name}: {res.video_with_audio}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose begin+annotated frames into videos with step-aligned narration.")
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
        "--json-path",
        type=Path,
        default=Path(
            "/shared/nas/data/m1/jiateng5/Mini_Word/inference/results_text/"
            "evaluate_data_combination2,3,4_inference_results.json"
        ),
        help="Path to JSON containing 'answer' fields",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/shared/nas/data/m1/jiateng5/Mini_Word/video_generate_with_sound"),
        help="Directory to write generated videos",
    )
    parser.add_argument("--fps", type=float, default=2.0, help="Frames per second for output videos")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output videos")
    parser.add_argument("--ext", choices=["mp4", "avi"], default="avi", help="Output container/extension")
    parser.add_argument("--tts", choices=["auto", "espeak", "espeak-ng", "pyttsx3", "gtts"], default="auto")
    parser.add_argument("--voice", type=str, default=None, help="Voice id/name for TTS backends that support it")
    parser.add_argument("--limit", type=int, default=None, help="Only process first N item_* folders")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_videos_with_sound(
        input_dir=args.input_dir,
        json_path=args.json_path,
        output_dir=args.output_dir,
        fps=args.fps,
        overwrite=bool(args.overwrite),
        ext=args.ext,
        tts_backend=args.tts,
        voice=args.voice,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()


