#!/bin/bash
# Optimize cover images: resize to max 600px wide, 80% JPEG quality
# Requires: ImageMagick (brew install imagemagick)

SOURCE_DIR="${1:-/Users/alanms/Documents/_zapata library/Photos}"
OUTPUT_DIR="${2:-/Users/alanms/Documents/zapata-library/static/covers}"

mkdir -p "$OUTPUT_DIR"

count=0
total=$(ls -1 "$SOURCE_DIR"/*.JPG 2>/dev/null | wc -l | tr -d ' ')

echo "Optimizing $total images..."
echo "Source: $SOURCE_DIR"
echo "Output: $OUTPUT_DIR"
echo ""

for img in "$SOURCE_DIR"/*.JPG; do
    filename=$(basename "$img")
    # Lowercase the filename
    outname=$(echo "$filename" | tr '[:upper:]' '[:lower:]')

    convert "$img" -resize 600x\> -quality 80 -strip "$OUTPUT_DIR/$outname"

    count=$((count + 1))
    if [ $((count % 100)) -eq 0 ]; then
        echo "  Processed $count / $total images..."
    fi
done

echo ""
echo "Done! Optimized $count images to $OUTPUT_DIR"
du -sh "$OUTPUT_DIR"
