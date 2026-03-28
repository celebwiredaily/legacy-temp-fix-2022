#!/usr/bin/env python3
"""
pinterest_scraper.py
--------------------
Scrapes Pinterest images/videos using keywords and a session cookie.
Saves media to assets/pinterest/<keyword>/

Usage:
    python3 pinterest_scraper.py \
        --keywords "aesthetic rooms,cozy bedroom" \
        --output assets/pinterest \
        --count 50 \
        --cookie "$PINTEREST_COOKIE"
"""

import argparse
import json
import os
import re
import sys
import time
import random
import logging
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Pinterest API constants ───────────────────────────────────────────────────
PINTEREST_BASE = "https://www.pinterest.com"
SEARCH_API     = f"{PINTEREST_BASE}/resource/BaseSearchResource/get/"

HEADERS_TEMPLATE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.pinterest.com/",
    "X-Requested-With": "XMLHttpRequest",
    "X-Pinterest-AppState": "active",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def build_headers(cookie: str) -> dict:
    h = dict(HEADERS_TEMPLATE)
    h["Cookie"] = cookie
    # Extract CSRF token from cookie string
    csrf_match = re.search(r"csrftoken=([^;]+)", cookie)
    if csrf_match:
        h["X-CSRFToken"] = csrf_match.group(1)
    return h


def fetch_json(url: str, headers: dict, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            log.warning(f"Fetch attempt {attempt+1}/{retries} failed: {exc}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt + random.random())
    raise RuntimeError(f"Failed to fetch: {url}")


def download_file(url: str, dest: Path, headers: dict) -> bool:
    """Download a single file. Returns True on success."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": headers["User-Agent"],
            "Referer": "https://www.pinterest.com/",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as exc:
        log.warning(f"Download failed ({url}): {exc}")
        return False


def extract_media_urls(pin_data: dict) -> list[dict]:
    """Pull the best image/video URL out of a pin object."""
    results = []

    # ── Videos ──────────────────────────────────────────────────────────────
    videos = pin_data.get("videos") or {}
    vformats = (videos.get("video_list") or {})
    if vformats:
        # pick highest-quality variant available
        for quality in ("V_HLSV4_MOBILE", "V_720P", "V_480P", "V_360P"):
            vdata = vformats.get(quality)
            if vdata and vdata.get("url"):
                results.append({
                    "type": "video",
                    "url":  vdata["url"],
                    "width":  vdata.get("width", 0),
                    "height": vdata.get("height", 0),
                })
                break

    # ── Images ───────────────────────────────────────────────────────────────
    images = pin_data.get("images") or {}
    for size in ("orig", "736x", "564x", "474x"):
        img = images.get(size)
        if img and img.get("url"):
            results.append({
                "type": "image",
                "url":  img["url"],
                "width":  img.get("width", 0),
                "height": img.get("height", 0),
            })
            break

    return results


def search_pinterest(
    keyword: str,
    headers: dict,
    count: int = 50,
    bookmark: str | None = None,
) -> tuple[list[dict], str | None]:
    """
    One page of Pinterest search results.
    Returns (list_of_pin_dicts, next_bookmark_or_None).
    """
    options = {
        "query":            keyword,
        "scope":            "pins",
        "page_size":        min(count, 50),
        "bookmarks":        [bookmark] if bookmark else [],
        "field_set_key":    "unauth_react",
        "no_fetch_context_on_resource": False,
        "article":          "",
        "auto_correction_disabled": False,
        "corpus": None,
        "customized_rerank_type": None,
        "filters":          None,
        "query_pin_sigs":   None,
        "redux_normalize_feed": True,
        "rs":               "typed",
        "source_url":       f"/search/pins/?q={urllib.parse.quote(keyword)}&rs=typed",
    }
    params = urllib.parse.urlencode({
        "source_url": f"/search/pins/?q={urllib.parse.quote(keyword)}",
        "data":       json.dumps({"options": options, "context": {}}),
    })
    url = f"{SEARCH_API}?{params}"

    data = fetch_json(url, headers)

    pins         = []
    next_bookmark = None

    resource_response = data.get("resource_response") or {}
    rdata = resource_response.get("data") or {}

    results = rdata.get("results") or []
    for pin in results:
        if pin.get("type") != "pin":
            continue
        pins.append(pin)

    # Pagination bookmark
    bookmarks_list = resource_response.get("bookmark")
    if isinstance(bookmarks_list, str) and bookmarks_list not in ("-end-", ""):
        next_bookmark = bookmarks_list
    elif isinstance(bookmarks_list, list) and bookmarks_list:
        bm = bookmarks_list[0]
        if bm not in ("-end-", ""):
            next_bookmark = bm

    return pins, next_bookmark


# ─── Main ─────────────────────────────────────────────────────────────────────

def scrape(
    keywords: list[str],
    output_dir: Path,
    total_count: int,
    cookie: str,
    prefer_video: bool = True,
) -> list[str]:
    """
    Scrape Pinterest for each keyword.
    Returns list of local file paths that were successfully downloaded.
    """
    headers   = build_headers(cookie)
    per_kw    = max(10, total_count // len(keywords)) + 5   # slight overcount
    all_files: list[str] = []

    for keyword in keywords:
        log.info(f"🔍  Keyword: '{keyword}' — target {per_kw} assets")
        kw_dir = output_dir / re.sub(r"[^\w]+", "_", keyword.lower())
        kw_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0
        bookmark   = None
        seen_urls: set[str] = set()

        while downloaded < per_kw:
            try:
                pins, bookmark = search_pinterest(keyword, headers, count=50, bookmark=bookmark)
            except Exception as exc:
                log.error(f"Search failed for '{keyword}': {exc}")
                break

            if not pins:
                log.info(f"No more pins for '{keyword}'")
                break

            random.shuffle(pins)  # add variety to ordering

            for pin in pins:
                if downloaded >= per_kw:
                    break

                media_items = extract_media_urls(pin)
                if not media_items:
                    continue

                # prefer video, fall back to image
                if prefer_video:
                    ordered = sorted(media_items, key=lambda x: x["type"] != "video")
                else:
                    ordered = [m for m in media_items if m["type"] == "image"] or media_items

                for media in ordered:
                    url = media["url"]
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # Skip very small images (icons / thumbnails)
                    if media["type"] == "image":
                        if media.get("width", 999) < 400 or media.get("height", 999) < 400:
                            continue

                    ext  = "mp4" if media["type"] == "video" else "jpg"
                    name = f"{downloaded:04d}_{pin.get('id','unknown')}.{ext}"
                    dest = kw_dir / name

                    if dest.exists():
                        log.info(f"  ↩  Already exists: {name}")
                        all_files.append(str(dest))
                        downloaded += 1
                        break

                    log.info(f"  ⬇  Downloading {media['type']}: {name}")
                    ok = download_file(url, dest, headers)
                    if ok:
                        all_files.append(str(dest))
                        downloaded += 1
                        time.sleep(random.uniform(0.3, 0.8))  # polite delay
                        break

            if not bookmark:
                log.info(f"Reached end of results for '{keyword}'")
                break

            time.sleep(random.uniform(1.0, 2.0))

        log.info(f"✅  '{keyword}': {downloaded} assets saved to {kw_dir}")

    log.info(f"🎉  Total downloaded: {len(all_files)} assets")
    return all_files


def main():
    ap = argparse.ArgumentParser(description="Pinterest scraper for video pipeline")
    ap.add_argument("--keywords", required=True,
                    help="Comma-separated list of search keywords")
    ap.add_argument("--output",   default="assets/pinterest",
                    help="Output directory (default: assets/pinterest)")
    ap.add_argument("--count",    type=int, default=60,
                    help="Total number of assets to download across all keywords")
    ap.add_argument("--cookie",   default=os.environ.get("PINTEREST_COOKIE", ""),
                    help="Pinterest session cookie string (or set PINTEREST_COOKIE env var)")
    ap.add_argument("--images-only", action="store_true",
                    help="Download images only, skip videos")
    ap.add_argument("--manifest", default="assets/manifest.json",
                    help="Write downloaded file list to this JSON file")
    args = ap.parse_args()

    if not args.cookie:
        log.error("No Pinterest cookie provided. Set --cookie or PINTEREST_COOKIE env var.")
        sys.exit(1)

    keywords   = [k.strip() for k in args.keywords.split(",") if k.strip()]
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = scrape(
        keywords    = keywords,
        output_dir  = output_dir,
        total_count = args.count,
        cookie      = args.cookie,
        prefer_video= not args.images_only,
    )

    if not files:
        log.error("No assets downloaded. Check your cookie and keywords.")
        sys.exit(1)

    # Write manifest so other scripts know what was downloaded
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"files": files}, indent=2))
    log.info(f"📋  Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
