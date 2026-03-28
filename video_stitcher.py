#!/usr/bin/env python3
"""
video_stitcher.py
-----------------
Stitches Pinterest assets (images + video clips) with the voiceover into
a final long-form MP4. Uses simple Ken Burns pan/zoom on images and
crossfade transitions. No paid APIs. Pure ffmpeg.

Output: 1080×1920 (9:16 vertical) at 30fps — ideal for YouTube Shorts,
        TikTok, or Reels, but easily changed to 1920×1080 for landscape.

Usage:
    python3 video_stitcher.py \
        --manifest assets/manifest.json \
        --audio    assets/audio/voiceover.mp3 \
        --output   output/final_video.mp4 \
        --title    "My Awesome Video" \
        --orientation vertical
"""

import argparse
import json
import logging
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Video settings ────────────────────────────────────────────────────────────
ORIENTATIONS = {
    "vertical":  {"w": 1080, "h": 1920},   # 9:16  (YouTube Shorts / TikTok)
    "horizontal":{"w": 1920, "h": 1080},   # 16:9  (YouTube standard)
    "square":    {"w": 1080, "h": 1080},   # 1:1   (Instagram)
}

FPS              = 30
TRANSITION_SECS  = 0.5     # crossfade duration between clips
MIN_CLIP_SECS    = 4.0     # minimum display time per image
MAX_CLIP_SECS    = 12.0    # maximum display time per image
VIDEO_CLIP_CAP   = 8.0     # cap video clips to this length (avoid dominant clips)
TITLE_CARD_SECS  = 2.5     # optional title card at start

# Ken Burns zoom presets — subtle, non-distracting
KB_PRESETS = [
    {"z_start": 1.0,  "z_end": 1.08, "x": "iw/2", "y": "ih/2"},          # gentle zoom in (center)
    {"z_start": 1.08, "z_end": 1.0,  "x": "iw/2", "y": "ih/2"},          # gentle zoom out (center)
    {"z_start": 1.0,  "z_end": 1.07, "x": "iw*0.3", "y": "ih*0.3"},      # zoom in top-left
    {"z_start": 1.0,  "z_end": 1.07, "x": "iw*0.7", "y": "ih*0.7"},      # zoom in bottom-right
    {"z_start": 1.05, "z_end": 1.0,  "x": "iw*0.5", "y": "ih*0.4"},      # zoom out upper center
]


def check_ffmpeg():
    if not shutil.which("ffmpeg"):
        log.error("ffmpeg not found. Install: sudo apt-get install ffmpeg")
        sys.exit(1)


def get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", str(audio_path)],
        capture_output=True, text=True
    )
    info = json.loads(result.stdout)
    for stream in info.get("streams", []):
        d = stream.get("duration")
        if d:
            return float(d)
    return 0.0


def get_video_info(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", str(path)],
        capture_output=True, text=True
    )
    info   = json.loads(result.stdout)
    out    = {"width": 0, "height": 0, "duration": 0.0, "has_video": False, "has_audio": False}
    for s in info.get("streams", []):
        if s["codec_type"] == "video":
            out["width"]     = s.get("width", 0)
            out["height"]    = s.get("height", 0)
            out["has_video"] = True
            try:
                dur = s.get("duration") or info.get("format", {}).get("duration", 0)
                out["duration"] = float(dur)
            except Exception:
                pass
        elif s["codec_type"] == "audio":
            out["has_audio"] = True
    return out


def load_manifest(manifest_path: Path) -> list[Path]:
    data  = json.loads(manifest_path.read_text())
    files = [Path(f) for f in data.get("files", [])]
    files = [f for f in files if f.exists()]
    if not files:
        log.error("No valid files in manifest.")
        sys.exit(1)
    log.info(f"📋  Manifest: {len(files)} assets")
    return files


def categorize_assets(files: list[Path]) -> tuple[list[Path], list[Path]]:
    images = [f for f in files if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    videos = [f for f in files if f.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv")]
    log.info(f"  Images: {len(images)}  Videos: {len(videos)}")
    return images, videos


def calculate_clip_durations(
    total_audio: float,
    n_clips: int,
    transition_secs: float,
) -> list[float]:
    """
    Distribute audio duration evenly across clips, accounting for transitions.
    Clips overlap by transition_secs at each join, so we add that back.
    """
    # Total timeline = sum(durations) - (n-1)*transition
    # => sum(durations) = total_audio + (n-1)*transition
    total_needed  = total_audio + (n_clips - 1) * transition_secs
    base_duration = total_needed / n_clips
    base_duration = max(MIN_CLIP_SECS, min(MAX_CLIP_SECS, base_duration))
    return [base_duration] * n_clips


def select_assets(
    images: list[Path],
    videos: list[Path],
    n_needed: int,
    seed: int = 42,
) -> list[tuple[str, Path]]:
    """
    Build an ordered list of (type, path) tuples for the video.
    Mixes images and video clips. Videos are inserted periodically for variety.
    """
    rng = random.Random(seed)

    imgs = list(images)
    vids = list(videos)
    rng.shuffle(imgs)
    rng.shuffle(vids)

    selected: list[tuple[str, Path]] = []
    img_idx = 0
    vid_idx = 0
    vid_every = 5  # insert a video clip every N items

    for i in range(n_needed):
        use_video = (vids and i % vid_every == (vid_every - 1))
        if use_video and vid_idx < len(vids):
            selected.append(("video", vids[vid_idx % len(vids)]))
            vid_idx += 1
        elif img_idx < len(imgs):
            selected.append(("image", imgs[img_idx % len(imgs)]))
            img_idx += 1
        elif vids:
            selected.append(("video", vids[vid_idx % len(vids)]))
            vid_idx += 1
        else:
            # cycle images if we run out
            selected.append(("image", imgs[i % len(imgs)]))

    return selected


def build_image_clip(
    image_path: Path,
    duration: float,
    w: int,
    h: int,
    tmp_dir: Path,
    idx: int,
    kb_preset: dict,
) -> Path:
    """
    Convert a single image to a video clip with Ken Burns effect.
    Returns path to the output clip.
    """
    out = tmp_dir / f"clip_{idx:04d}.mp4"

    n_frames    = int(duration * FPS)
    z_start     = kb_preset["z_start"]
    z_end       = kb_preset["z_end"]
    focus_x     = kb_preset["x"]
    focus_y     = kb_preset["y"]

    # zoompan filter: zoom from z_start to z_end linearly
    # We pad the image to at least target size first, then zoompan, then scale
    zoompan_filter = (
        f"scale=8000:-1,"                          # upscale to avoid zoom artifacts
        f"zoompan="
        f"z='min(zoom+({z_end-z_start:.4f}/{n_frames}),{max(z_start,z_end):.4f})':"
        f"x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':"
        f"d={n_frames}:"
        f"s={w}x{h}:"
        f"fps={FPS},"
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-vf", zoompan_filter,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-an",
        str(out),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.warning(f"Image clip failed for {image_path.name}, using fallback")
        log.debug(result.stderr[-500:])
        # Fallback: simple scale without Ken Burns
        fallback_filter = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
            f"setsar=1"
        )
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(image_path),
            "-vf", fallback_filter,
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-an", str(out),
        ], check=True, capture_output=True)

    return out


def build_video_clip(
    video_path: Path,
    duration: float,
    w: int,
    h: int,
    tmp_dir: Path,
    idx: int,
) -> Path:
    """
    Trim and reformat a Pinterest video clip to match target dimensions.
    """
    out = tmp_dir / f"clip_{idx:04d}.mp4"

    info     = get_video_info(video_path)
    clip_dur = min(duration, info["duration"], VIDEO_CLIP_CAP)
    if clip_dur <= 0:
        clip_dur = duration

    scale_filter = (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1,fps={FPS}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", scale_filter,
        "-t", str(clip_dur),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-an",   # strip original audio — we use the voiceover
        str(out),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.warning(f"Video clip failed for {video_path.name}: {result.stderr[-300:]}")
        # If the video clip fails entirely, create a black frame fallback
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=black:s={w}x{h}:r={FPS}",
            "-t", str(clip_dur),
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-an", str(out),
        ], check=True, capture_output=True)

    return out


def concatenate_with_crossfade(
    clip_paths: list[Path],
    durations: list[float],
    output_path: Path,
    transition_secs: float,
    w: int,
    h: int,
    tmp_dir: Path,
) -> Path:
    """
    Concatenate clips using xfade crossfade transitions.
    Returns path to the concatenated video (no audio).
    """
    if len(clip_paths) == 1:
        shutil.copy(clip_paths[0], output_path)
        return output_path

    log.info(f"🔗  Concatenating {len(clip_paths)} clips with crossfades...")

    # Build ffmpeg filter graph with xfade
    # xfade works by specifying when each transition starts (cumulative offset)
    inputs     = []
    for p in clip_paths:
        inputs += ["-i", str(p)]

    # Build filter chain
    # Each clip must be [N:v] labelled, then chained through xfade
    n      = len(clip_paths)
    parts  = []
    offset = 0.0

    # First xfade takes [0:v][1:v]
    offset += durations[0] - transition_secs
    parts.append(
        f"[0:v][1:v]xfade=transition=fade:duration={transition_secs}:offset={offset:.3f}[vx1]"
    )

    for i in range(2, n):
        offset += durations[i-1] - transition_secs
        in_label  = f"[vx{i-1}]"
        out_label = f"[vx{i}]"
        parts.append(
            f"{in_label}[{i}:v]xfade=transition=fade:duration={transition_secs}"
            f":offset={offset:.3f}{out_label}"
        )

    final_label = f"[vx{n-1}]"
    filter_complex = ";".join(parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", final_label,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.warning("xfade failed, falling back to simple concat (no transitions)")
        log.debug(result.stderr[-600:])
        _simple_concat(clip_paths, output_path, tmp_dir)

    return output_path


def _simple_concat(clip_paths: list[Path], output_path: Path, tmp_dir: Path):
    """Fallback: concat without transitions."""
    concat_list = tmp_dir / "concat_list.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in clip_paths)
    )
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(output_path),
    ], check=True, capture_output=True)


def mux_audio(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    video_duration: float,
):
    """Mux the voiceover audio into the concatenated video."""
    log.info("🔊  Muxing audio...")

    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",           # trim to shorter of video/audio
        str(output_path),
    ], check=True, capture_output=True)

    log.info(f"✅  Final video: {output_path}")


def add_title_card(
    title: str,
    w: int,
    h: int,
    duration: float,
    tmp_dir: Path,
    font_size: int = 72,
) -> Path:
    """Generate a simple black title card with white text."""
    out = tmp_dir / "title_card.mp4"

    # Try to find a font
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    font = next((f for f in font_paths if os.path.exists(f)), "")

    if font:
        drawtext = (
            f"drawtext=fontfile='{font}':"
            f"text='{title}':"
            f"fontsize={font_size}:"
            f"fontcolor=white:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2:"
            f"line_spacing=10:"
            f"box=1:boxcolor=black@0.4:boxborderw=20"
        )
        vf = f"color=black:s={w}x{h}:r={FPS}[bg];[bg]{drawtext}"
    else:
        vf = f"color=black:s={w}x{h}:r={FPS}"

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", vf if not font else f"color=black:s={w}x{h}:r={FPS}",
        *([] if not font else ["-vf", drawtext]),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-an",
        str(out),
    ], capture_output=True)

    return out if out.exists() else None


def main():
    ap = argparse.ArgumentParser(description="Video stitcher — Pinterest assets + voiceover → MP4")
    ap.add_argument("--manifest",      required=True,
                    help="Path to manifest.json from pinterest_scraper.py")
    ap.add_argument("--audio",         required=True,
                    help="Voiceover audio file (MP3/WAV)")
    ap.add_argument("--output",        default="output/final_video.mp4")
    ap.add_argument("--title",         default="",
                    help="Optional title card text at the start")
    ap.add_argument("--orientation",   default="vertical",
                    choices=list(ORIENTATIONS.keys()),
                    help="Video orientation (default: vertical 9:16)")
    ap.add_argument("--transition",    type=float, default=TRANSITION_SECS,
                    help=f"Crossfade duration in seconds (default: {TRANSITION_SECS})")
    ap.add_argument("--seed",          type=int, default=42,
                    help="Random seed for asset selection (for reproducibility)")
    ap.add_argument("--keep-tmp",      action="store_true",
                    help="Keep temporary clip files (for debugging)")
    args = ap.parse_args()

    check_ffmpeg()

    dims = ORIENTATIONS[args.orientation]
    w, h = dims["w"], dims["h"]
    log.info(f"🎬  Output: {w}×{h} ({args.orientation})  FPS: {FPS}")

    # ── Load assets ────────────────────────────────────────────────────────────
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        log.error(f"Manifest not found: {manifest_path}")
        sys.exit(1)

    audio_path = Path(args.audio)
    if not audio_path.exists():
        log.error(f"Audio not found: {audio_path}")
        sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Get audio duration ─────────────────────────────────────────────────────
    audio_duration = get_audio_duration(audio_path)
    if audio_duration <= 0:
        log.error("Could not determine audio duration.")
        sys.exit(1)
    log.info(f"⏱  Audio duration: {audio_duration:.1f}s ({audio_duration/60:.1f} min)")

    # ── Load and categorize assets ─────────────────────────────────────────────
    all_files       = load_manifest(manifest_path)
    images, videos  = categorize_assets(all_files)

    if not images and not videos:
        log.error("No usable media assets found.")
        sys.exit(1)

    # ── Calculate how many clips we need ──────────────────────────────────────
    # Aim for clips of MIN–MAX seconds; compute minimum clips needed
    avg_clip_dur = (MIN_CLIP_SECS + MAX_CLIP_SECS) / 2
    n_clips      = max(
        10,
        math.ceil(audio_duration / (avg_clip_dur - args.transition))
    )
    log.info(f"🖼  Target clip count: {n_clips}")

    assets     = select_assets(images, videos, n_clips, seed=args.seed)
    durations  = calculate_clip_durations(audio_duration, len(assets), args.transition)

    log.info(f"📐  Clip duration: ~{durations[0]:.1f}s each")

    # ── Build individual clips ─────────────────────────────────────────────────
    tmp_ctx = tempfile.TemporaryDirectory() if not args.keep_tmp else None
    tmp_dir = Path(tmp_ctx.name) if tmp_ctx else Path("tmp_clips")
    tmp_dir.mkdir(exist_ok=True)

    try:
        clip_paths: list[Path] = []
        kb_presets  = KB_PRESETS

        for i, (asset_type, asset_path) in enumerate(assets):
            duration = durations[i]
            log.info(f"  [{i+1:03d}/{len(assets)}] {asset_type}: {asset_path.name} ({duration:.1f}s)")

            if asset_type == "image":
                kb = kb_presets[i % len(kb_presets)]
                clip = build_image_clip(asset_path, duration, w, h, tmp_dir, i, kb)
            else:
                clip = build_video_clip(asset_path, duration, w, h, tmp_dir, i)

            clip_paths.append(clip)

        # ── Prepend title card if requested ───────────────────────────────────
        if args.title:
            log.info(f"🎬  Adding title card: '{args.title}'")
            title_clip = add_title_card(args.title, w, h, TITLE_CARD_SECS, tmp_dir)
            if title_clip:
                clip_paths.insert(0, title_clip)
                durations.insert(0, TITLE_CARD_SECS)

        # ── Concatenate with crossfades ────────────────────────────────────────
        concat_path = tmp_dir / "concatenated.mp4"
        concatenate_with_crossfade(
            clip_paths     = clip_paths,
            durations      = durations,
            output_path    = concat_path,
            transition_secs= args.transition,
            w=w, h=h,
            tmp_dir        = tmp_dir,
        )

        # ── Mux audio into video ───────────────────────────────────────────────
        mux_audio(concat_path, audio_path, output_path, audio_duration)

        # ── Final report ───────────────────────────────────────────────────────
        size_mb = output_path.stat().st_size / (1024 * 1024)
        log.info(f"🎉  Done! Output: {output_path}  ({size_mb:.1f} MB)")

        # Write output metadata
        meta = {
            "output":       str(output_path),
            "duration_s":   audio_duration,
            "clips":        len(clip_paths),
            "resolution":   f"{w}x{h}",
            "size_mb":      round(size_mb, 2),
            "orientation":  args.orientation,
        }
        (output_path.parent / "video_meta.json").write_text(json.dumps(meta, indent=2))

    finally:
        if tmp_ctx:
            tmp_ctx.cleanup()


if __name__ == "__main__":
    main()
