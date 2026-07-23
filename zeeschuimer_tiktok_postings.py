#!/usr/bin/env python3
"""
Zeeschuimer TikTok Media Downloader
Lädt Videos aus einem zeeschuimer NDJSON-Export herunter.

Voraussetzung:
    pip install yt-dlp

Verwendung:
    python zeeschuimer_tiktok_postings.py export.ndjson
    python zeeschuimer_tiktok_postings.py export.ndjson --output ./meine_videos
    python zeeschuimer_tiktok_postings.py export.ndjson --quality best
    python zeeschuimer_tiktok_postings.py export.ndjson --quality 720
"""

import json
import sys
import argparse
import subprocess
from pathlib import Path


def check_ytdlp():
    """Prüft ob yt-dlp installiert ist."""
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Fehler: yt-dlp ist nicht installiert.")
        print("Bitte installieren mit:  pip install yt-dlp")
        sys.exit(1)


def extract_video_urls(ndjson_path: Path) -> list[dict]:
    """Liest alle Posts und baut die TikTok-Video-URLs zusammen."""
    items = []
    with ndjson_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Warnung: Zeile übersprungen (ungültiges JSON): {e}")
                continue

            data = d.get("data", {})
            post_id = data.get("id") or d.get("item_id")
            author = data.get("author", {})
            unique_id = author.get("uniqueId") or author.get("unique_id")
            desc = data.get("desc", "")

            if not post_id:
                continue

            if unique_id:
                url = f"https://www.tiktok.com/@{unique_id}/video/{post_id}"
            else:
                url = f"https://www.tiktok.com/video/{post_id}"

            items.append({"url": url, "id": post_id, "desc": desc[:60]})

    return items


def build_ytdlp_cmd(url: str, output_dir: Path, quality: str, user_agent: str) -> list[str]:
    """Baut den yt-dlp-Befehl zusammen."""

    # Dateiname = TikTok-ID, damit es zum Instagram-Skript parallel bleibt
    output_template = str(output_dir / "%(id)s.%(ext)s")

    # TikTok liefert Audio+Video in einem Stream (kein separates bestaudio).
    # Format-String waehlt bestes kombiniertes Format mit Audio, kein Wasserzeichen.
    if quality == "best":
        fmt = "best[acodec!=none][format_id!=download]"
    elif quality == "worst":
        fmt = "worst[acodec!=none][format_id!=download]"
    else:
        fmt = f"best[height<={quality}][acodec!=none][format_id!=download]/best[acodec!=none][format_id!=download]"

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--format", fmt,
        "--output", output_template,
        "--user-agent", user_agent,
        "--add-header", "Referer:https://www.tiktok.com/",
        "--retries", "3",
        "--fragment-retries", "3",
        "--no-warnings",
        url,
    ]
    return cmd


def main():
    parser = argparse.ArgumentParser(
        description="Videos aus einem zeeschuimer TikTok-Export herunterladen (via yt-dlp)"
    )
    parser.add_argument("ndjson", help="Pfad zur .ndjson-Exportdatei")
    parser.add_argument(
        "--output", "-o", default="./tiktok_media",
        help="Zielordner (Standard: ./tiktok_media)"
    )
    parser.add_argument(
        "--quality", "-q", default="best",
        help="Qualität: 'best', 'worst', oder Höhe in px z.B. '720' (Standard: best)"
    )
    parser.add_argument(
        "--user-agent",
        default=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:151.0) "
            "Gecko/20100101 Firefox/151.0"
        ),
        help="User-Agent (Standard: Firefox/151 macOS, passend zum zeeschuimer-Export)"
    )
    args = parser.parse_args()

    check_ytdlp()

    ndjson_path = Path(args.ndjson)
    if not ndjson_path.exists():
        print(f"Fehler: Datei nicht gefunden: {ndjson_path}")
        sys.exit(1)

    items = extract_video_urls(ndjson_path)
    if not items:
        print("Keine Videos gefunden.")
        sys.exit(0)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📂 {len(items)} Posts geladen aus: {ndjson_path.name}")
    print(f"💾 Zielordner: {output_dir.resolve()}")
    print(f"🎬 Qualität: {args.quality}\n")

    ok, skip, fail = 0, 0, 0

    for i, item in enumerate(items, start=1):
        # Bereits vorhandene überspringen (yt-dlp macht das auch, aber so sieht man es früher)
        existing = list(output_dir.glob(f"{item['id']}.*"))
        if existing:
            print(f"[{i}/{len(items)}] Übersprungen (existiert): {existing[0].name}")
            skip += 1
            continue

        desc_preview = f"  ({item['desc']}...)" if item["desc"] else ""
        print(f"[{i}/{len(items)}] {item['url']}{desc_preview}")

        cmd = build_ytdlp_cmd(item["url"], output_dir, args.quality, args.user_agent)

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Dateinamen aus yt-dlp-Output lesen
            downloaded = list(output_dir.glob(f"{item['id']}.*"))
            if downloaded:
                size_mb = downloaded[0].stat().st_size / (1024 * 1024)
                print(f"    ✓ {downloaded[0].name} ({size_mb:.1f} MB)")
            else:
                print(f"    ✓ heruntergeladen")
            ok += 1
        else:
            # yt-dlp-Fehlermeldung kompakt ausgeben
            err = result.stderr.strip().splitlines()
            short_err = err[-1] if err else "unbekannter Fehler"
            print(f"    ✗ {short_err}")
            fail += 1

    print(f"\n✅ Fertig: {ok} heruntergeladen, {skip} übersprungen, {fail} fehlgeschlagen")
    print(f"📁 Dateien gespeichert in: {output_dir.resolve()}")


if __name__ == "__main__":
    main()