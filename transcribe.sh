# Verwendung:
#    Pfade anpassen und dann:
#    chmod +x transcribe.sh
#    ./transcribe.sh

INPUT_DIR=""
OUTPUT_DIR=""

for f in "$INPUT_DIR"/*.mp4; do
  base=$(basename "$f" .mp4)
  [ -f "$OUTPUT_DIR/${base}.txt" ] && continue
  whisper "$f" --language de --model turbo --output_format txt --output_dir "$OUTPUT_DIR"
done
