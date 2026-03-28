import argparse
import hashlib
import json
import logging
import os
import random
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Image dimensions (vertical 9:16) ─────────────────────────────────────────
IMG_W = 1080
IMG_H = 1920

# ─── Prompt templates — makes images more cinematic/aesthetic ─────────────────
STYLE_SUFFIXES = [
    "cinematic lighting, 4k, highly detailed, aesthetic",
    "golden hour, soft shadows, beautiful composition",
    "moody atmosphere, professional photography, sharp focus",
    "warm tones, cozy aesthetic, high resolution",
    "natural light, editorial style, stunning visuals",
    "dramatic lighting, rich colors, ultra detailed",
]


def enhance_prompt(keyword: str, style_idx: int) -> str:
    """Add style suffix to make images more visually interesting."""
    suffix = STYLE_SUFFIXES[style_idx % len(STYLE_SUFFIXES)]
    return f"{keyword.strip()}, {suffix}"


# ─── Backend: Pollinations.ai ─────────────────────────────────────────────────

def generate_pollinations(
    prompt: str,
    output_path: Path,
    width: int = IMG_W,
    height: int = IMG_H,
    seed: int | None = None,
) -> bool:
    """
    Generate image via Pollinations.ai — completely free, no API key.
    GET https://image.pollinations.ai/prompt/{prompt}?width=W&height=H&seed=N
    """
    if seed is None:
        seed = random.randint(1, 999999)

    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={width}&height={height}&seed={seed}&nologo=true&enhance=true"
    )

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer":    "https://pollinations.ai",
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()

        if len(data) < 1000:  # too small = error response
            log.warning(f"Pollinations returned suspiciously small response ({len(data)} bytes)")
            return False

        output_path.write_bytes(data)
        return True

    except Exception as exc:
        log.warning(f"Pollinations failed: {exc}")
        return False


# ─── Backend: Hugging Face Inference API ─────────────────────────────────────

HF_MODELS = [
    "stabilityai/stable-diffusion-xl-base-1.0",   # best quality
    "runwayml/stable-diffusion-v1-5",              # faster fallback
    "prompthero/openjourney-v4",                   # artistic style
]

def generate_huggingface(
    prompt: str,
    output_path: Path,
    hf_token: str,
    model: str = HF_MODELS[0],
    width: int = 1024,
    height: int = 1024,
) -> bool:
    """
    Generate image via HuggingFace Inference API.
    Free tier: ~1000 requests/day. Requires HF_TOKEN secret.
    """
    import json as _json

    # HF API caps at 1024x1024 for SDXL
    width  = min(width,  1024)
    height = min(height, 1024)

    url     = f"https://api-inference.huggingface.co/models/{model}"
    payload = _json.dumps({
        "inputs": prompt,
        "parameters": {
            "width":            width,
            "height":           height,
            "num_inference_steps": 25,
            "guidance_scale":   7.5,
        }
    }).encode()

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {hf_token}",
                "Content-Type":  "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()

        # HF returns raw image bytes if successful, JSON if error
        try:
            err = json.loads(data)
            if "error" in err:
                log.warning(f"HF API error: {err['error']}")
                # Model loading — wait and retry
                if "loading" in str(err.get("error", "")).lower():
                    wait = err.get("estimated_time", 20)
                    log.info(f"Model loading, waiting {wait:.0f}s...")
                    time.sleep(min(wait, 30))
                return False
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass  # raw image bytes — good

        if len(data) < 1000:
            return False

        output_path.write_bytes(data)
        return True

    except Exception as exc:
        log.warning(f"HuggingFace API failed: {exc}")
        return False


# ─── Prompt generation from script ───────────────────────────────────────────

def extract_prompts_from_script(script: str, keywords: list[str], n: int) -> list[str]:
    """
    Build a list of image prompts by combining keywords with script context.
    Cycles through keywords to fill n prompts total.
    """
    prompts = []

    # Split script into rough segments for contextual prompts
    words    = script.split()
    seg_size = max(50, len(words) // n)
    segments = [
        " ".join(words[i:i+seg_size])
        for i in range(0, len(words), seg_size)
    ]

    for i in range(n):
        kw      = keywords[i % len(keywords)]
        style   = STYLE_SUFFIXES[i % len(STYLE_SUFFIXES)]

        # Every 3rd prompt uses a script segment for context
        if segments and i % 3 == 2:
            seg    = segments[i % len(segments)]
            # Extract the most visually descriptive words from the segment
            prompt = f"{kw}, {seg[:80].strip()}, {style}"
        else:
            prompt = f"{kw}, {style}"

        prompts.append(prompt)

    return prompts


# ─── Main generation loop ─────────────────────────────────────────────────────

def generate_images(
    prompts: list[str],
    output_dir: Path,
    backend: str,
    hf_token: str = "",
) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []

    for i, prompt in enumerate(prompts):
        # Use prompt hash for filename so same prompt = same file (cache-friendly)
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        out_path    = output_dir / f"{i:04d}_{prompt_hash}.jpg"

        # Skip if already generated (useful for re-runs)
        if out_path.exists() and out_path.stat().st_size > 5000:
            log.info(f"  ↩  [{i+1:03d}/{len(prompts)}] Cache hit: {out_path.name}")
            files.append(str(out_path))
            continue

        log.info(f"  🎨  [{i+1:03d}/{len(prompts)}] Prompt: {prompt[:70]}...")

        success = False

        if backend == "pollinations":
            success = generate_pollinations(
                prompt      = prompt,
                output_path = out_path,
                seed        = i * 137,   # deterministic seeds
            )
            if not success and hf_token:
                log.info("  ↩  Pollinations failed, trying HuggingFace...")
                success = generate_huggingface(prompt, out_path, hf_token)

        elif backend == "huggingface":
            if not hf_token:
                log.error("HuggingFace backend requires HF_TOKEN")
                sys.exit(1)
            success = generate_huggingface(prompt, out_path, hf_token)
            if not success:
                log.info("  ↩  HuggingFace failed, trying Pollinations...")
                success = generate_pollinations(prompt, out_path, seed=i * 137)

        if success:
            size_kb = out_path.stat().st_size // 1024
            log.info(f"  ✅  Saved: {out_path.name} ({size_kb}KB)")
            files.append(str(out_path))
        else:
            log.warning(f"  ❌  Failed to generate image {i+1}, skipping")

        # Polite delay between requests
        if i < len(prompts) - 1:
            time.sleep(random.uniform(1.0, 2.5))

    log.info(f"\n🎉  Generated {len(files)}/{len(prompts)} images")
    return files


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="AI image generator for video b-roll")
    ap.add_argument("--keywords", required=True,
                    help="Comma-separated visual keywords")
    ap.add_argument("--script",   default="",
                    help="Path to script file for context-aware prompts (optional)")
    ap.add_argument("--output",   default="assets/images",
                    help="Output directory")
    ap.add_argument("--count",    type=int, default=50,
                    help="Number of images to generate")
    ap.add_argument("--backend",  default="pollinations",
                    choices=["pollinations", "huggingface"],
                    help="Image generation backend")
    ap.add_argument("--hf-token", default=os.environ.get("HF_TOKEN", ""),
                    help="HuggingFace API token (or set HF_TOKEN env var)")
    ap.add_argument("--manifest", default="assets/manifest.json",
                    help="Output manifest path")
    ap.add_argument("--width",    type=int, default=IMG_W)
    ap.add_argument("--height",   type=int, default=IMG_H)
    args = ap.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if not keywords:
        log.error("No keywords provided")
        sys.exit(1)

    # Load script if provided
    script = ""
    if args.script and Path(args.script).exists():
        script = Path(args.script).read_text(encoding="utf-8").strip()
        log.info(f"📝  Script loaded: {len(script)} chars")

    log.info(f"🎨  Backend: {args.backend}")
    log.info(f"📐  Resolution: {args.width}×{args.height}")
    log.info(f"🔑  Keywords: {keywords}")
    log.info(f"🖼  Target count: {args.count}")

    # Build prompts
    prompts = extract_prompts_from_script(script, keywords, args.count)

    # Generate
    output_dir = Path(args.output)
    files      = generate_images(
        prompts    = prompts,
        output_dir = output_dir,
        backend    = args.backend,
        hf_token   = args.hf_token,
    )

    if not files:
        log.error("No images generated. Check your network connection.")
        sys.exit(1)

    # Write manifest (same format as pinterest_scraper.py)
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"files": files}, indent=2))
    log.info(f"📋  Manifest written: {manifest_path}")


if __name__ == "__main__":
    main()
