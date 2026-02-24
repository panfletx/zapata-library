#!/usr/bin/env python3
"""
Normalize publisher names in all catalogue files using data/publisher_map.yaml.

For each .md file in content/catalogue/:
  1. Read current publishers list
  2. For each entry: check map for exact match first (handles "/" and comma compounds)
  3. If no exact match: auto-split on " : " and " ; ", then normalize each part
  4. Strip bracketed annotations like "[distribuidor]" from unmatched parts
  5. Deduplicate and write back
"""

import yaml
import os
import re


with open('data/publisher_map.yaml', 'r', encoding='utf-8') as f:
    PUBLISHER_MAP = yaml.safe_load(f) or {}


def normalize_entry(entry):
    """
    Normalize a single raw publisher entry.
    Returns a list of canonical publisher names (may be empty to drop, or multiple to split).
    """
    entry = entry.strip()
    if not entry:
        return []

    # 1. Exact match in map (handles "/" combos, comma combos, and single variants)
    if entry in PUBLISHER_MAP:
        mapped = PUBLISHER_MAP[entry]
        return mapped if mapped else []  # empty list = drop

    # 2. Auto-split on " : " and " ; "
    parts = re.split(r'\s*[;:]\s*', entry)
    if len(parts) == 1:
        # No split occurred — strip brackets and look up
        cleaned = re.sub(r'\s*\[.*?\]', '', entry).strip()
        if not cleaned:
            return []
        # Check map again after bracket stripping
        if cleaned in PUBLISHER_MAP:
            mapped = PUBLISHER_MAP[cleaned]
            return mapped if mapped else []
        return [cleaned]

    # Multiple parts from split
    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Check map for the part as-is first (may have brackets like "Patria [distribuidor]")
        if part in PUBLISHER_MAP:
            mapped = PUBLISHER_MAP[part]
            if mapped:
                result.extend(mapped)
            # else: mapped to [] = drop this part
            continue
        # Strip bracketed annotations
        cleaned = re.sub(r'\s*\[.*?\]', '', part).strip()
        if not cleaned:
            continue
        # Check map after bracket stripping
        if cleaned in PUBLISHER_MAP:
            mapped = PUBLISHER_MAP[cleaned]
            if mapped:
                result.extend(mapped)
            # else: drop
            continue
        result.append(cleaned)

    return result


def normalize_file(filepath):
    """Normalize publishers in a single catalogue file. Returns True if changed."""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    if not text.startswith('---'):
        return False

    end_idx = text.index('---', 3)
    front_text = text[3:end_idx]
    body = text[end_idx:]

    front = yaml.safe_load(front_text)
    if front is None:
        return False

    raw_publishers = front.get('publishers') or []
    if not raw_publishers:
        return False

    new_publishers = []
    for entry in raw_publishers:
        new_publishers.extend(normalize_entry(str(entry)))

    # Deduplicate preserving order
    seen = set()
    deduped = []
    for p in new_publishers:
        if p not in seen:
            seen.add(p)
            deduped.append(p)

    if deduped == raw_publishers:
        return False

    front['publishers'] = deduped if deduped else None

    new_front = yaml.dump(front, default_flow_style=False, allow_unicode=True,
                          sort_keys=False, width=200)
    new_text = '---\n' + new_front + body

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_text)

    return True


def main():
    catalogue_dir = 'content/catalogue'
    files = [f for f in os.listdir(catalogue_dir)
             if f.endswith('.md') and f != '_index.en.md']

    total = 0
    updated = 0
    all_publishers_before = set()
    all_publishers_after = set()

    for fn in sorted(files):
        filepath = os.path.join(catalogue_dir, fn)
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        if not text.startswith('---'):
            continue
        total += 1
        end_idx = text.index('---', 3)
        front = yaml.safe_load(text[3:end_idx])
        for p in (front.get('publishers') or []):
            all_publishers_before.add(str(p))

        if normalize_file(filepath):
            updated += 1

        with open(filepath, 'r', encoding='utf-8') as f:
            text2 = f.read()
        end_idx2 = text2.index('---', 3)
        front2 = yaml.safe_load(text2[3:end_idx2])
        for p in (front2.get('publishers') or []):
            all_publishers_after.add(str(p))

    print(f"Total files:           {total}")
    print(f"Files updated:         {updated}")
    print(f"Unique publishers before: {len(all_publishers_before)}")
    print(f"Unique publishers after:  {len(all_publishers_after)}")
    print(f"Reduction:             {len(all_publishers_before) - len(all_publishers_after)}")


if __name__ == "__main__":
    main()
