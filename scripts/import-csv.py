#!/usr/bin/env python3
"""
Import Zotero CSV export into Hugo content files.

Usage:
    python3 scripts/import-csv.py \
        --csv "/Users/alanms/Documents/_zapata library/zlibrary.csv" \
        --output content/catalogue
"""

import csv
import os
import re
import argparse
import yaml


LANG_MAP = {
    "spa": "Español",
    "eng": "English",
    "fre": "Français",
    "ger": "Deutsch",
    "por": "Português",
    "ita": "Italiano",
    "und": "Unknown",
    "mul": "Multilingual",
    "en": "English",
    "pt-BR": "Português",
    "cat": "Català",
    "lat": "Latin",
    "jpn": "Japanese",
    "rus": "Russian",
    "ara": "Arabic",
    "zho": "Chinese",
}


def parse_extra(extra):
    """Extract OCLC number and cover note from the Extra field."""
    oclc = ""
    cover_note = ""
    exlibris = ""

    if not extra:
        return oclc, cover_note, exlibris

    oclc_match = re.search(r'OCLC:\s*(\d+)', extra)
    if oclc_match:
        oclc = oclc_match.group(1)

    covnote_match = re.search(r'covnote:\s*(.+?)(?:\s*$|\s+\w+:)', extra)
    if covnote_match:
        cover_note = covnote_match.group(1).strip()

    exlibris_match = re.search(r'exlibris:\s*(.+?)(?:\s*$|\s+\w+:)', extra)
    if exlibris_match:
        exlibris = exlibris_match.group(1).strip()

    return oclc, cover_note, exlibris


def split_and_clean(value, delimiter="; "):
    """Split a delimited string into a list of cleaned, non-empty values."""
    if not value:
        return []
    items = [item.strip() for item in value.split(delimiter)]
    return [item for item in items if item]


def sanitize_yaml_string(s):
    """Ensure a string is safe for YAML front matter."""
    if not s:
        return ""
    # Replace literal backslash-n with space
    s = s.replace("\\n", " ")
    # Collapse multiple spaces
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def make_front_matter(row):
    """Convert a CSV row dict into Hugo front matter dict."""
    key = row.get("Key", "").strip()
    title = sanitize_yaml_string(row.get("Title", ""))

    if not title or not key:
        return None, None, None

    # Parse fields
    authors = split_and_clean(row.get("Author", ""), "; ")
    subjects_manual = split_and_clean(row.get("Manual Tags", ""), "; ")
    subjects_auto = split_and_clean(row.get("Automatic Tags", ""), "; ")
    subjects = list(dict.fromkeys(subjects_manual + subjects_auto))  # deduplicate, preserve order

    pub_year = row.get("Publication Year", "").strip()
    year = int(pub_year) if pub_year.isdigit() else 0

    num_pages = row.get("Num Pages", "").strip()
    pages = int(num_pages) if num_pages.isdigit() else 0

    language_code = row.get("Language", "").strip()
    language_name = LANG_MAP.get(language_code, language_code) if language_code else ""

    item_type = row.get("Item Type", "").strip()
    publisher = sanitize_yaml_string(row.get("Publisher", ""))
    place = sanitize_yaml_string(row.get("Place", ""))
    isbn = row.get("ISBN", "").strip()
    issn = row.get("ISSN", "").strip()
    doi = row.get("DOI", "").strip()
    source_url = row.get("Url", "").strip()
    edition = sanitize_yaml_string(row.get("Edition", ""))
    series = sanitize_yaml_string(row.get("Series", ""))
    date_added = row.get("Date Added", "").strip()

    oclc, cover_note, exlibris = parse_extra(row.get("Extra", ""))

    abstract = row.get("Abstract Note", "").strip()

    # Compute decade
    decade = f"{(year // 10) * 10}s" if year >= 1800 else ""

    # Build front matter
    fm = {
        "title": title,
        "date": date_added[:10] if date_added else "2024-01-01",
        "year": year,
        "decade": decade,
        "authors": authors if authors else [],
        "publishers": [publisher] if publisher else [],
        "place": place,
        "languages": [language_name] if language_name else [],
        "item_types": [item_type] if item_type else [],
        "isbn": isbn,
        "issn": issn,
        "doi": doi,
        "source_url": source_url,
        "pages": pages,
        "edition": edition,
        "series": [series] if series else [],
        "subjects": subjects,
        "oclc": oclc,
        "cover_note": cover_note,
        "exlibris": exlibris,
        "zotero_key": key,
        "cover": f"covers/{key.lower()}.jpg",
    }

    # Remove empty optional fields to keep front matter clean
    for field in ["issn", "doi", "source_url", "oclc", "cover_note", "exlibris", "isbn", "edition", "place"]:
        if not fm[field]:
            del fm[field]

    if fm["year"] == 0:
        del fm["year"]
    if not fm["decade"]:
        del fm["decade"]
    if fm["pages"] == 0:
        del fm["pages"]

    return key, fm, abstract


def write_markdown(output_dir, key, front_matter, abstract):
    """Write a Hugo content file."""
    filepath = os.path.join(output_dir, f"{key}.md")

    # Use yaml.dump for safe serialization
    fm_str = yaml.dump(front_matter, default_flow_style=False, allow_unicode=True, sort_keys=False)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(fm_str)
        f.write("---\n\n")
        if abstract:
            f.write(abstract)
            f.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Import Zotero CSV to Hugo content")
    parser.add_argument("--csv", required=True, help="Path to zlibrary.csv")
    parser.add_argument("--output", required=True, help="Output directory for Markdown files")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    count = 0
    skipped = 0

    with open(args.csv, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key, fm, abstract = make_front_matter(row)
            if key is None:
                skipped += 1
                continue

            write_markdown(args.output, key, fm, abstract)
            count += 1

            if count % 200 == 0:
                print(f"  Processed {count} items...")

    print(f"\nDone! Imported {count} items, skipped {skipped}.")
    print(f"Output: {args.output}/")


if __name__ == "__main__":
    main()
