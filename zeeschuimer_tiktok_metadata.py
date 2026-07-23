#!/usr/bin/env python3
"""
Zeeschuimer TikTok Metadata Extractor
Extrahiert Metadaten aus einem zeeschuimer NDJSON-Export als TSV.

Verwendung:
    python zeeschuimer_tiktok_metadata.py tiktok.ndjson
    python zeeschuimer_tiktok_metadata.py tiktok.ndjson --output metadaten.tsv
"""

import json
import csv
import sys
import argparse
from pathlib import Path
from datetime import datetime


FIELDS = [
    "video_id",
    "url",
    "created_at",
    "description",
    "media_type",
    "views",
    "likes",
    "comments",
    "shares",
    "saves",
    "reposts",
    "duration",
    "resolution",
    "author_id",
    "author_name",
    "music_title",
    "music_author",
    "music_original",
    "hashtags",
    "is_ad",
]


def extract_hashtags(contents: list) -> str:
    """Extrahiert Hashtags aus dem contents-Array."""
    tags = []
    for item in contents:
        desc = item.get("desc", "")
        tags += [word for word in desc.split() if word.startswith("#")]
    return " ".join(tags)


def parse_item(item: dict) -> dict:
    data = item.get("data", {})
    stats = data.get("statsV2") or data.get("stats") or {}
    video = data.get("video", {})
    author = data.get("author", {})
    music = data.get("music", {})

    post_id = data.get("id") or item.get("item_id", "")
    unique_id = author.get("uniqueId") or author.get("unique_id", "")
    url = f"https://www.tiktok.com/@{unique_id}/video/{post_id}" if unique_id else f"https://www.tiktok.com/video/{post_id}"

    created_at = ""
    ct = data.get("createTime")
    if ct:
        try:
            created_at = datetime.fromtimestamp(int(ct)).strftime("%Y-%m-%d %H:%M")
        except Exception:
            created_at = str(ct)

    width = video.get("width", "")
    height = video.get("height", "")
    resolution = f"{width}x{height}" if width and height else ""

    return {
        "video_id":       post_id,
        "url":            url,
        "created_at":     created_at,
        "description":    data.get("desc", "").replace("\n", " "),
        "media_type":     "",
        "views":          stats.get("playCount", ""),
        "likes":          stats.get("diggCount", ""),
        "comments":       stats.get("commentCount", ""),
        "shares":         stats.get("shareCount", ""),
        "saves":          stats.get("collectCount", ""),
        "reposts":        stats.get("repostCount", ""),
        "duration":       video.get("duration", ""),
        "resolution":     resolution,
        "author_id":      unique_id,
        "author_name":    author.get("nickname", ""),
        "music_title":    music.get("title", ""),
        "music_author":   music.get("authorName", ""),
        "music_original": music.get("original", ""),
        "hashtags":       extract_hashtags(data.get("contents", [])),
        "is_ad":          data.get("isAd", ""),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Metadaten aus einem zeeschuimer TikTok-Export als TSV speichern"
    )
    parser.add_argument("ndjson", help="Pfad zur .ndjson-Exportdatei")
    parser.add_argument(
        "--output", "-o", default=None,
        help="Zieldatei (Standard: gleicher Name wie Input, aber .tsv)"
    )
    args = parser.parse_args()

    ndjson_path = Path(args.ndjson)
    if not ndjson_path.exists():
        print(f"Fehler: Datei nicht gefunden: {ndjson_path}")
        sys.exit(1)

    output_path = Path(args.output) if args.output else ndjson_path.with_suffix(".tsv")

    items = []
    with ndjson_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Warnung: Zeile uebersprungen: {e}")

    rows = [parse_item(item) for item in items]

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ {len(rows)} Videos exportiert nach: {output_path}")


if __name__ == "__main__":
    main()