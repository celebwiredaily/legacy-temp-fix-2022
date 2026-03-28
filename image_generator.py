import argparse
import hashlib
import json
import logging
import os
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
# Note: Gemini/Imagen typically manages its own aspect ratios, 
# but we will prompt for vertical.
IMG_W = 1080
IMG_H = 1920

def generate_gemini(prompt: str, output_path: Path, api_key: str) -> bool:
    """Generates images using Gemini 2.0 Flash Image Generation."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash-exp:generateContent"  # Using stable beta endpoint
        f"?key={api_key}"
    )
    
    # We add your specific documentary style to the prompt here
    full_prompt = (
        f"{prompt}. 1950s documentary style, high contrast, black and white photography, "
        f"soft studio lighting, 9:16 vertical aspect ratio, cinematic film grain."
    )

    payload = json.dumps({
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
        },
    }).encode()

    try:
        req = urllib.request.Request(
            url, 
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())

        # Extract image from response
        if "candidates" in data and data["candidates"]:
            for part in data["candidates"][0]["content"]["parts"]:
                if "inlineData" in part:
                    img_bytes = base64.b64decode(part["inlineData"]["data"])
                    output_path.write_bytes(img_bytes)
                    return True

        log.warning("Gemini returned no image part")
        return False

    except Exception as exc:
        log.warning(f"Gemini failed: {exc}")
        return False

def generate_images(keywords: list[str], output_dir: Path, count: int, api_key: str) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = []

    for i in range(count):
        kw = keywords[i % len(keywords)]
        log.info(f"✨ [{i+1:03d}/{count}] Generating: {kw}")
        
        prompt_hash = hashlib.md5(kw.encode()).hexdigest()[:8]
        out_path = output_dir / f"{i:04d}_{prompt_hash}.png"

        # Check cache
        if out_path.exists():
            log.info(f"  ↩  Using cached: {out_path.name}")
            files.append(str(out_path))
            continue

        if generate_gemini(kw, out_path, api_key):
            log.info(f"  ✅ Saved: {out_path.name}")
            files.append(str(out_path))
        else:
            log.error(f"  ❌ Generation failed for: {kw}")

    return files

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", required=True, help="Comma separated keywords")
    ap.add_argument("--output", default="assets/images")
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--manifest", default="assets/manifest.json")
    args = ap.parse_args()

    # Get key from environment (more secure for GitHub Actions/Codespaces)
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        log.error("GOOGLE_API_KEY not found in environment variables.")
        return

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    output_dir = Path(args.output)
    
    files = generate_images(keywords, output_dir, args.count, api_key)

    # Write manifest
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"files": files}, indent=2))
    log.info(f"📋 Manifest updated with {len(files)} images.")

if __name__ == "__main__":
    main()
