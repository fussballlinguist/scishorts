#!/usr/bin/env python3
"""
Zeeschuimer Instagram Metadata Extractor
Extrahiert Metadaten aus einem zeeschuimer NDJSON-Export als TSV.

Verwendung:
    python zeeschuimer_insta_metadata.py export.ndjson
    python zeeschuimer_insta_metadata.py export.ndjson --output metadaten.tsv
"""

import json
import csv
import sys
import argparse
from pathlib import Path
from datetime import datetime


# Spaltennamen – identisch zum TikTok-Skript, ergänzt um Instagram-spezifische Felder
FIELDS = [
    "post_id",
    "url",
    "created_at",
    "description",
    "media_type",       # Bild / Video / Karussell (Instagram-spezifisch)
    "views",            # bei Instagram nicht verfügbar
    "likes",
    "comments",
    "shares",           # bei Instagram nicht verfügbar
    "saves",            # bei Instagram nicht verfügbar
    "reposts",          # bei Instagram nicht verfügbar
    "duration",         # bei Instagram nicht verfügbar
    "author_id",
    "author_name",
    "author_username",
    "author_verified",
    "music_title",      # bei Instagram nicht verfügbar
    "music_author",     # bei Instagram nicht verfügbar
    "music_original",   # bei Instagram nicht verfügbar
    "hashtags",
    "location",         # Instagram-spezifisch
    "is_ad",
]

MEDIA_TYPE_LABELS = {
    1: "Bild",
    2: "Video",
    8: "Karussell",
}


def extract_hashtags(text: str) -> str:
    """Extrahiert alle #Hashtags aus dem Caption-Text."""
    return " ".join(word for word in text.split() if word.startswith("#"))


def parse_item(item: dict) -> dict:
    data = item.get("data", {})

    # --- IDs und URL ---
    post_id   = data.get("pk", "")
    shortcode = data.get("code", "")
    url       = f"https://www.instagram.com/p/{shortcode}/" if shortcode else ""

    # --- Zeitstempel ---
    taken_at   = data.get("taken_at")
    created_at = datetime.fromtimestamp(taken_at).strftime("%Y-%m-%d %H:%M") if taken_at else ""

    # --- Caption und Hashtags ---
    caption     = data.get("caption") or {}
    caption_text = caption.get("text", "") if isinstance(caption, dict) else ""
    description = caption_text.replace("\n", " ")
    hashtags    = extract_hashtags(caption_text)

    # --- Medientyp ---
    media_type = MEDIA_TYPE_LABELS.get(data.get("media_type"), "")

    # --- Autor ---
    user             = data.get("user", {})
    author_id        = user.get("pk", "")
    author_username  = user.get("username", "")
    author_name      = user.get("full_name", "")
    author_verified  = user.get("is_verified", "")

    # --- Engagement ---
    likes    = data.get("like_count", "")
    comments = data.get("comment_count", "")

    # --- Ort ---
    location_data = data.get("location") or {}
    location      = location_data.get("name", "")

    # --- Werbung ---
    is_ad = data.get("is_paid_partnership", "")

    return {
        "post_id":        post_id,
        "url":            url,
        "created_at":     created_at,
        "description":    description,
        "media_type":     media_type,
        "views":          "",
        "likes":          likes,
        "comments":       comments,
        "shares":         "",
        "saves":          "",
        "reposts":        "",
        "duration":       "",
        "author_id":      author_id,
        "author_name":    author_name,
        "author_username": author_username,
        "author_verified": author_verified,
        "music_title":    "",
        "music_author":   "",
        "music_original": "",
        "hashtags":       hashtags,
        "location":       location,
        "is_ad":          is_ad,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Metadaten aus einem zeeschuimer Instagram-Export als TSV speichern"
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

    # NDJSON einlesen
    items = []
    with ndjson_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Warnung: Zeile übersprungen: {e}")

    # Metadaten extrahieren und schreiben
    rows = [parse_item(item) for item in items]

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ {len(rows)} Posts exportiert nach: {output_path}")


if __name__ == "__main__":
    main()