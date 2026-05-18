#!/usr/bin/env python3
"""
Proofread and correct description_en and description_es fields in the 49
catalogue files that received English→Spanish translations.

Fixes spelling, grammar, syntax, style, and punctuation in both languages
to meet the standard expected of a public humanities website.

Usage:
    export ANTHROPIC_API_KEY=...
    python3 scripts/proofread-descriptions.py
"""

import os
import sys
import time
import yaml
import anthropic

CATALOGUE_DIR = "content/catalogue"

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

EN_PROMPT = """\
You are a copy editor for a public humanities website. Correct the following \
book description in English for spelling, grammar, syntax, style, and \
punctuation. The result should read as polished, standard prose suitable for \
an academic library catalogue. Do not add new content or change the meaning. \
Return only the corrected text, with no preamble, quotes, or explanation.

{text}"""

ES_PROMPT = """\
Eres corrector de estilo para un sitio web de humanidades de acceso público. \
Corrige la siguiente descripción de libro en español en cuanto a ortografía, \
gramática, sintaxis, estilo y puntuación. El resultado debe ser prosa \
estándar y cuidada, adecuada para un catálogo de biblioteca académica. No \
añadas contenido nuevo ni cambies el significado. Devuelve únicamente el \
texto corregido, sin preámbulos, comillas ni explicaciones.

{text}"""


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


def correct(client, prompt_template, text):
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt_template.format(text=text)}],
    )
    return resp.content[0].text.strip()


def safe_correct(client, prompt_template, text, label):
    for attempt in range(3):
        try:
            return correct(client, prompt_template, text)
        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(f"    Rate limited — waiting {wait}s…")
            time.sleep(wait)
    print(f"    [FAILED after 3 attempts] {label}")
    return text  # return original on failure


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    updated = errors = 0

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

        orig_en = front.get("description_en", "")
        orig_es = front.get("description_es", "")

        if not orig_en and not orig_es:
            print(f"  [NO DESCRIPTIONS] {key} — skipping")
            continue

        print(f"  Proofreading {key}…")

        if orig_en:
            new_en = safe_correct(client, EN_PROMPT, orig_en, f"{key}/EN")
            front["description_en"] = new_en
            if new_en != orig_en:
                print(f"    EN changed: {orig_en[:60]!r}")
                print(f"          → {new_en[:60]!r}")

        if orig_es:
            new_es = safe_correct(client, ES_PROMPT, orig_es, f"{key}/ES")
            front["description_es"] = new_es
            if new_es != orig_es:
                print(f"    ES changed: {orig_es[:60]!r}")
                print(f"          → {new_es[:60]!r}")

        write_file(path, front, body)
        updated += 1

    print(f"\nDone: {updated} files processed, {errors} errors.")


if __name__ == "__main__":
    main()
