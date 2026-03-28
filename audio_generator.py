#!/usr/bin/env python3
"""
audio_generator.py
------------------
Generates a voiceover MP3 from a script using Edge TTS (free, no API key).
Optionally mixes in a background music track at low volume.

Usage:
    python3 audio_generator.py \
        --script "Your full video script here..." \
        --output assets/audio/voiceover.mp3 \
        --voice en-US-BrianMultilingualNeural \
        --music assets/audio/background.mp3 \
        --music-volume 0.20
"""

import argparse
import asyncio
import json
import logging
import os
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

# ─── Edge TTS voices available (all free) ─────────────────────────────────────
RECOMMENDED_VOICES = [
    "en-US-BrianMultilingualNeural",   # deep, natural male
    "en-US-AndrewMultilingualNeural",  # clear male
    "en-US-EmmaMultilingualNeural",    # warm female
    "en-US-AvaMultilingualNeural",     # expressive female
    "en-GB-RyanNeural",                # British male
    "en-AU-WilliamNeural",             # Australian male
]


def check_ffmpeg():
    if not shutil.which("ffmpeg"):
        log.error("ffmpeg not found. Install it: sudo apt-get install ffmpeg")
        sys.exit(1)


def check_edge_tts():
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        log.info("Installing edge-tts...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "edge-tts", "-q"])


def split_script_into_chunks(script: str, max_chars: int = 3000) -> list[str]:
    """
    Split long scripts into chunks edge-tts can handle cleanly.
    Splits on sentence boundaries to avoid cutting mid-sentence.
    """
    if len(script) <= max_chars:
        return [script]

    # Split on sentence-ending punctuation
    import re
    sentences = re.split(r"(?<=[.!?])\s+", script.strip())

    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    log.info(f"Script split into {len(chunks)} chunks")
    return chunks


async def generate_chunk(
    text: str,
    voice: str,
    rate: str,
    output_path: Path,
) -> float:
    """Generate TTS for one chunk. Returns duration in seconds."""
    import edge_tts

    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await communicate.save(str(output_path))

    # Get duration via ffprobe
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", str(output_path)],
            capture_output=True, text=True
        )
        info = json.loads(result.stdout)
        duration = float(info["streams"][0].get("duration", 0))
        return duration
    except Exception:
        return 0.0


async def generate_voiceover(
    script: str,
    voice: str,
    rate: str,
    output_path: Path,
    tmp_dir: Path,
) -> float:
    """
    Generate full voiceover from script.
    Returns total audio duration in seconds.
    """
    import edge_tts

    log.info(f"🎙  Voice: {voice}  Rate: {rate}")

    chunks = split_script_into_chunks(script)

    if len(chunks) == 1:
        # Simple case — single chunk
        log.info("Generating voiceover (single chunk)...")
        communicate = edge_tts.Communicate(text=script, voice=voice, rate=rate)
        await communicate.save(str(output_path))
    else:
        # Multi-chunk: generate each, then concatenate with ffmpeg
        chunk_files = []
        for i, chunk in enumerate(chunks):
            chunk_path = tmp_dir / f"chunk_{i:03d}.mp3"
            log.info(f"  Generating chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
            communicate = edge_tts.Communicate(text=chunk, voice=voice, rate=rate)
            await communicate.save(str(chunk_path))
            chunk_files.append(chunk_path)

        # Concatenate all chunks
        log.info("Concatenating audio chunks...")
        concat_list = tmp_dir / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in chunk_files)
        )
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(output_path),
        ], check=True, capture_output=True)

    # Get final duration
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", str(output_path)],
        capture_output=True, text=True
    )
    try:
        info     = json.loads(result.stdout)
        duration = float(info["streams"][0].get("duration", 0))
    except Exception:
        duration = 0.0

    log.info(f"✅  Voiceover generated: {duration:.1f}s  →  {output_path}")
    return duration


def mix_with_background_music(
    voiceover_path: Path,
    music_path: Path,
    output_path: Path,
    music_volume: float = 0.20,
    voiceover_duration: float = 0.0,
):
    """
    Mix voiceover with background music.
    Music loops if shorter than voiceover, fades out at the end.
    """
    if not music_path.exists():
        log.warning(f"Music file not found: {music_path} — skipping mix")
        shutil.copy(voiceover_path, output_path)
        return

    log.info(f"🎵  Mixing background music at {music_volume:.0%} volume...")

    # Get voiceover duration if not provided
    if voiceover_duration <= 0:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", str(voiceover_path)],
            capture_output=True, text=True
        )
        info = json.loads(result.stdout)
        voiceover_duration = float(info["streams"][0].get("duration", 0))

    fade_start = max(0, voiceover_duration - 3)

    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(voiceover_path),
        "-stream_loop", "-1",          # loop music if needed
        "-i", str(music_path),
        "-filter_complex",
        (
            f"[1:a]volume={music_volume},"
            f"afade=t=out:st={fade_start:.2f}:d=3,"
            f"atrim=duration={voiceover_duration:.3f}[music];"
            "[0:a][music]amix=inputs=2:duration=first:dropout_transition=0[out]"
        ),
        "-map", "[out]",
        "-t", str(voiceover_duration),
        "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path),
    ], check=True, capture_output=True)

    log.info(f"✅  Mixed audio saved: {output_path}")


def write_metadata(
    output_dir: Path,
    voice: str,
    duration: float,
    script: str,
):
    meta = {
        "voice":    voice,
        "duration": round(duration, 2),
        "chars":    len(script),
        "words":    len(script.split()),
    }
    meta_path = output_dir / "audio_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    log.info(f"📋  Audio metadata: {meta}")


def main():
    ap = argparse.ArgumentParser(description="Edge TTS voiceover generator")
    ap.add_argument("--script",         required=True,
                    help="Video script text (or @path to read from file)")
    ap.add_argument("--output",         default="assets/audio/voiceover.mp3")
    ap.add_argument("--voice",          default="en-US-BrianMultilingualNeural",
                    help=f"Edge TTS voice. Options: {', '.join(RECOMMENDED_VOICES)}")
    ap.add_argument("--rate",           default="+0%",
                    help="Speech rate adjustment e.g. +10%% (faster) or -10%% (slower)")
    ap.add_argument("--music",          default="",
                    help="Optional background music file to mix in")
    ap.add_argument("--music-volume",   type=float, default=0.20,
                    help="Background music volume 0.0–1.0 (default: 0.20)")
    ap.add_argument("--no-music",       action="store_true",
                    help="Skip background music mixing even if --music is provided")
    args = ap.parse_args()

    check_ffmpeg()
    check_edge_tts()

    # Read script from file if prefixed with @
    script = args.script
    if script.startswith("@"):
        script_path = Path(script[1:])
        if not script_path.exists():
            log.error(f"Script file not found: {script_path}")
            sys.exit(1)
        script = script_path.read_text(encoding="utf-8").strip()

    if not script:
        log.error("Script is empty.")
        sys.exit(1)

    log.info(f"📝  Script: {len(script)} chars / ~{len(script.split())} words")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        # 1. Generate voiceover
        raw_vo = tmp_dir / "voiceover_raw.mp3"
        duration = asyncio.run(
            generate_voiceover(
                script      = script,
                voice       = args.voice,
                rate        = args.rate,
                output_path = raw_vo,
                tmp_dir     = tmp_dir,
            )
        )

        if duration <= 0:
            log.error("Voiceover generation produced no audio.")
            sys.exit(1)

        log.info(f"⏱  Voiceover duration: {duration:.1f}s ({duration/60:.1f} min)")

        # 2. Mix with background music (optional)
        music_path = Path(args.music) if args.music else None
        if music_path and not args.no_music:
            mix_with_background_music(
                voiceover_path    = raw_vo,
                music_path        = music_path,
                output_path       = output_path,
                music_volume      = args.music_volume,
                voiceover_duration= duration,
            )
        else:
            shutil.copy(raw_vo, output_path)
            log.info(f"✅  Voiceover saved: {output_path}")

        # 3. Write metadata for the stitcher
        write_metadata(output_path.parent, args.voice, duration, script)

    log.info("🎉  Audio generation complete")


if __name__ == "__main__":
    main()
