import argparse
import hashlib
import json
import logging
import os
import random
import sys
import time
import base64
import urllib.request
import urllib.parse
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────────────────
IMG_W = 1080
IMG_H = 1920

# ─── Backend: Gemini ────────────────────────────────────────────────────────

def generate_gemini(prompt: str, output_path: Path, api_key: str) -> bool:
    """Generates images using Gemini 2.0 Flash."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash-exp:generateContent?key={api_key}"
    )
    
    # Apply your signature high-contrast documentary style
    full_prompt = (
        f"{prompt}. 1950s documentary style, high contrast, black and white photography, "
        f"cinematic film grain, 9:16 vertical aspect ratio."
    )

    payload = json.dumps({
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }).encode()

    try:
        req = urllib.request.Request(
            url, data=payload, 
            headers={"Content-Type": "application/json"}, 
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())

        if "candidates" in data and data["candidates"]:
            for part in data["candidates"][0]["content"]["parts"]:
                if "inlineData" in part:
                    img_bytes = base64.b64decode(part["inlineData"]["data"])
                    output_path.write_bytes(img_bytes)
                    return True
        return False
    except Exception as exc:
        log.warning(f"Gemini failed: {exc}")
        return False

# ─── Prompt Logic ───────────────────────────────────────────────────────────

def extract_prompts_from_script(script: str, keywords: list[str], n: int) -> list[str]:
    """Combines keywords with script segments for context."""
    prompts = []
    words = script.split()
    seg_size = max(50, len(words) // n) if words else 0
    
    for i in range(n):
        kw = keywords[i % len(keywords)]
        if words and i % 2 == 0:
            start = (i * seg_size) % len(words)
            seg = " ".join(words[start:start+20])
            prompts.append(f"{kw}, {seg}")
        else:
            prompts.append(kw)
    return prompts

# ─── Main Logic ──────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", required=True)
    ap.add_argument("--script",   default="")
    ap.add_argument("--output",   default="assets/images")
    ap.add_argument("--count",    type=int, default=5)
    ap.add_argument("--backend",  default="gemini", choices=["gemini", "pollinations"])
    ap.add_argument("--manifest", default="assets/manifest.json")
    args = ap.parse_args()

    # Load Script
    script_text = ""
    if args.script and Path(args.script).exists():
        script_text = Path(args.script).read_text(encoding="utf-8")

    # Build Prompts
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    prompts = extract_prompts_from_script(script_text, keywords, args.count)

    # Setup Output
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []

    # Get API Key
    api_key = os.environ.get("GOOGLE_API_KEY")

    for i, p in enumerate(prompts):
        p_hash = hashlib.md5(p.encode()).hexdigest()[:8]
        filename = f"{i:04d}_{p_hash}.png"
        target = out_dir / filename
        
        log.info(f"✨ [{i+1}/{args.count}] Generating: {p[:50]}...")
        
        if generate_gemini(p, target, api_key):
            log.info(f"  ✅ Saved: {filename}")
            generated_files.append(str(target))
        else:
            log.error(f"  ❌ Failed: {filename}")
        
        time.sleep(1)

    # Write Manifest
    Path(args.manifest).write_text(json.dumps({"files": generated_files}, indent=2))
    log.info(f"📋 Manifest written to {args.manifest}")

if __name__ == "__main__":
    main()
