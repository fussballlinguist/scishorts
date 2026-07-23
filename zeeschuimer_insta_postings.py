#!/usr/bin/env python3
"""
Zeeschuimer Instagram Media Downloader
Lädt Bilder und Videos aus einem zeeschuimer NDJSON-Export herunter.

Verwendung:
    python zeeschuimer_insta_postings.py export.ndjson
    python zeeschuimer_insta_postings.py export.ndjson --output ./meine_bilder
    python zeeschuimer_insta_postings.py export.ndjson --images-only
    python zeeschuimer_insta_postings.py export.ndjson --videos-only
"""

import json
import sys
import os
import argparse
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


# Instagram-CDN braucht einen Browser-User-Agent, sonst → 403
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.instagram.com/",
}

MEDIA_TYPES = {1: "Bild", 2: "Video", 8: "Karussell"}


def get_best_image_url(image_versions2: dict) -> str | None:
    """Gibt die URL des Bildes mit der höchsten Auflösung zurück."""
    candidates = image_versions2.get("candidates", [])
    if not candidates:
        return None
    # Größte Auflösung zuerst (width * height)
    best = max(candidates, key=lambda c: c.get("width", 0) * c.get("height", 0))
    return best.get("url")


def get_best_video_url(video_versions: list) -> str | None:
    """Gibt die URL der Video-Version mit der höchsten Auflösung zurück."""
    if not video_versions:
        return None
    best = max(video_versions, key=lambda v: v.get("width", 0) * v.get("height", 0))
    return best.get("url")


def collect_media(item: dict, download_images: bool, download_videos: bool) -> list[dict]:
    """
    Extrahiert alle herunterzuladenden Medien aus einem Post.
    Gibt eine Liste von Dicts mit {url, ext, label} zurück.
    """
    data = item.get("data", {})
    media_type = data.get("media_type")
    post_id = data.get("pk") or item.get("item_id", "unknown")
    results = []

    def add_from_node(node: dict, suffix: str = ""):
        node_type = node.get("media_type", media_type)
        if node_type == 2 and download_videos:
            url = get_best_video_url(node.get("video_versions", []))
            if url:
                results.append({"url": url, "ext": "mp4", "name": f"{post_id}{suffix}"})
        elif node_type in (1, None) and download_images:
            url = get_best_image_url(node.get("image_versions2", {}))
            if url:
                results.append({"url": url, "ext": "jpg", "name": f"{post_id}{suffix}"})

    if media_type == 8:  # Karussell
        for i, child in enumerate(data.get("carousel_media", []), start=1):
            add_from_node(child, suffix=f"_{i}")
    else:
        add_from_node(data)

    return results


def download_file(url: str, dest: Path) -> bool:
    """Lädt eine Datei herunter. Gibt True bei Erfolg zurück."""
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=30) as response:
            dest.write_bytes(response.read())
        return True
    except HTTPError as e:
        print(f"    ✗ HTTP {e.code}: {dest.name}")
    except URLError as e:
        print(f"    ✗ URL-Fehler: {e.reason} ({dest.name})")
    except Exception as e:
        print(f"    ✗ Fehler: {e} ({dest.name})")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Medien aus einem zeeschuimer Instagram-Export herunterladen"
    )
    parser.add_argument("ndjson", help="Pfad zur .ndjson-Exportdatei")
    parser.add_argument(
        "--output", "-o", default="./instagram_media",
        help="Zielordner (Standard: ./instagram_media)"
    )
    parser.add_argument("--images-only", action="store_true", help="Nur Bilder herunterladen")
    parser.add_argument("--videos-only", action="store_true", help="Nur Videos herunterladen")
    parser.add_argument(
        "--delay", type=float, default=0.5,
        help="Wartezeit zwischen Downloads in Sekunden (Standard: 0.5)"
    )
    args = parser.parse_args()

    download_images = not args.videos_only
    download_videos = not args.images_only

    # NDJSON einlesen
    ndjson_path = Path(args.ndjson)
    if not ndjson_path.exists():
        print(f"Fehler: Datei nicht gefunden: {ndjson_path}")
        sys.exit(1)

    items = []
    with ndjson_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Warnung: Zeile übersprungen (ungültiges JSON): {e}")

    print(f"📂 {len(items)} Posts geladen aus: {ndjson_path.name}")

    # Medien sammeln
    all_media = []
    for item in items:
        all_media.extend(collect_media(item, download_images, download_videos))

    if not all_media:
        print("Keine Medien zum Herunterladen gefunden.")
        sys.exit(0)

    print(f"🔍 {len(all_media)} Mediendateien gefunden")

    # Zielordner anlegen
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"💾 Zielordner: {output_dir.resolve()}\n")

    # Herunterladen
    ok, skip, fail = 0, 0, 0
    for i, media in enumerate(all_media, start=1):
        dest = output_dir / f"{media['name']}.{media['ext']}"

        if dest.exists():
            print(f"[{i}/{len(all_media)}] Übersprungen (existiert): {dest.name}")
            skip += 1
            continue

        print(f"[{i}/{len(all_media)}] Lade: {dest.name} ...", end=" ", flush=True)
        success = download_file(media["url"], dest)
        if success:
            size_kb = dest.stat().st_size // 1024
            print(f"✓ ({size_kb} KB)")
            ok += 1
        else:
            fail += 1

        if args.delay > 0 and i < len(all_media):
            time.sleep(args.delay)

    print(f"\n✅ Fertig: {ok} heruntergeladen, {skip} übersprungen, {fail} fehlgeschlagen")
    print(f"📁 Dateien gespeichert in: {output_dir.resolve()}")


if __name__ == "__main__":
    main()