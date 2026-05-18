#!/usr/bin/env python3
"""
Translate English book descriptions to Spanish and store both versions as
front matter fields (description_en / description_es), clearing the body.

Usage:
    export ANTHROPIC_API_KEY=...
    python3 scripts/translate-descriptions.py
"""

import os
import re
import sys
import time
import yaml
import anthropic

CATALOGUE_DIR = "content/catalogue"

# Files identified as having English descriptions
ENGLISH_KEYS = [
    "2BM25ZZK", "2CV9BZK4", "398Q59E2", "3SMQEZN7", "4BC4FQC3", "4ULHAV32",
    "54HSZYX5", "5CREXMUP", "5XXQ5GUU", "8HDTNN6W", "8YD5KTZY", "8YZ85V2C",
    "BQHY5BVQ", "C2B5GXE6", "D296K3NC", "DITB6CET", "DLMCXYLC", "ELX924VJ",
    "EW3YHRBD", "F4HN3C4W", "F7SC5GNM", "F7WF7B3L", "FBFNFGKL", "FI2UWZWE",
    "FW5Y8FLY", "INIJ5SS2", "IRTDS7QA", "J5FHA6QE", "KBFDJ43B", "KD6LS5KL",
    "MJXWN27N", "NZYKE9WS", "P6RD3T8E", "QWBWPKKR", "QXKFXJ82", "R5L39TYF",
    "R5ZSCN7N", "RN8KG92M", "S72L48FT", "TJD9L7AL", "TXA6RZ2Z", "U9UCNWHF",
    "W4B7GU4P", "W9L8L3K5", "WIFV3LDV", "XIBKXDRD", "Y2HLREPE", "YR35TIGD",
    "YVPVKKL6",
]


def parse_file(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    parts = raw.split("---")
    if len(parts) < 3:
        return None, None
    front = yaml.safe_load(parts[1])
    body = "---".join(parts[2:]).strip()
    return front, body


def write_file(path, front, body=""):
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(front, f, allow_unicode=True, default_flow_style=False, sort_keys=True)
        f.write("---\n")
        if body:
            f.write(body + "\n")


def translate(client, text):
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": (
                "Translate the following book description from English to Spanish. "
                "Return only the translated text, no preamble or quotes.\n\n"
                f"{text}"
            ),
        }],
    )
    return resp.content[0].text.strip()


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    skipped = 0
    updated = 0
    errors = 0

    for key in ENGLISH_KEYS:
        path = os.path.join(CATALOGUE_DIR, f"{key}.md")
        if not os.path.exists(path):
            print(f"  [MISSING] {key}")
            errors += 1
            continue

        front, body = parse_file(path)
        if front is None:
            print(f"  [PARSE ERROR] {key}")
            errors += 1
            continue

        if not body:
            print(f"  [NO BODY] {key} — skipping")
            skipped += 1
            continue

        if "description_en" in front and "description_es" in front:
            print(f"  [SKIP] {key} — already translated")
            skipped += 1
            continue

        print(f"  Translating {key}: {body[:60]}…")
        try:
            spanish = translate(client, body)
        except anthropic.RateLimitError:
            print("    Rate limited — waiting 60s…")
            time.sleep(60)
            spanish = translate(client, body)
        except Exception as e:
            print(f"    [ERROR] {e}")
            errors += 1
            continue

        front["description_en"] = body
        front["description_es"] = spanish

        write_file(path, front, body="")
        print(f"    → {spanish[:60]}…")
        updated += 1

    print(f"\nDone: {updated} translated, {skipped} skipped, {errors} errors.")


if __name__ == "__main__":
    main()
