#!/usr/bin/env python3
"""
Remap subjects in all catalogue files using data/subject_map.yaml.

For each .md file in content/catalogue/:
  1. Read current subjects
  2. Map each to new categories via subject_map.yaml
  3. Deduplicate and sort
  4. Write back updated frontmatter

For books with NO subjects after mapping:
  - Auto-assign based on metadata (language, publisher location, item_type)
"""

import yaml
import os
import re

# Load subject map
with open('data/subject_map.yaml', 'r', encoding='utf-8') as f:
    SUBJECT_MAP = yaml.safe_load(f)

# Language → literature category mapping
LANG_LIT_MAP = {
    'Español': 'Fiction',
    'Français': 'French Literature',
    'English': 'Fiction',
    'Deutsch': 'German Literature',
    'Português': 'Fiction',
    'Italiano': 'Italian Literature',
    'Latin': 'Classical Literature',
    'Japanese': 'Japanese Literature',
    'Russian': 'Russian Literature',
    'Arabic': 'Arabic Literature',
    'Chinese': 'Fiction',
    'Català': 'Fiction',
}

# Mexican publishers (approximate)
MEXICAN_PUBLISHERS = [
    'fondo de cultura', 'fce', 'siglo xxi', 'era', 'joaquín mortiz',
    'unam', 'grijalbo', 'cal y arena', 'tusquets', 'colibrí',
    'conaculta', 'planeta mexicana', 'alfaguara', 'porrúa',
    'ediciones del ermitaño', 'la cifra', 'posada', 'oceano',
    'océano', 'universidad', 'colofón', 'fontamara', 'gedisa',
    'debolsillo', 'seix barral', 'diana', 'praxis', 'aldus',
    'resistencia', 'trilce', 'sexto piso', 'tintanueva',
    'nueva imagen', 'culturales', 'jus', 'conacyt',
]


def is_mexican_publisher(publishers):
    """Check if any publisher looks Mexican."""
    if not publishers:
        return False
    for p in publishers:
        pl = p.lower()
        for mp in MEXICAN_PUBLISHERS:
            if mp in pl:
                return True
    return False


def auto_assign(front):
    """Auto-assign categories for books with no subjects."""
    cats = []
    langs = front.get('languages') or []
    publishers = front.get('publishers') or []
    item_types = front.get('item_types') or []

    # Based on language
    for lang in langs:
        lit_cat = LANG_LIT_MAP.get(lang)
        if lit_cat and lit_cat not in cats:
            cats.append(lit_cat)

    # Mexican publisher → Mexican Literature
    if is_mexican_publisher(publishers):
        if 'Mexican Literature' not in cats:
            cats.append('Mexican Literature')

    # Default to Fiction for books
    if 'book' in item_types and not cats:
        cats.append('Fiction')

    return cats


def remap_file(filepath):
    """Remap subjects in a single catalogue file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    if not text.startswith('---'):
        return False

    # Find end of frontmatter
    end_idx = text.index('---', 3)
    front_text = text[3:end_idx]
    body = text[end_idx:]

    front = yaml.safe_load(front_text)
    if front is None:
        return False

    old_subjects = front.get('subjects') or []

    # Map subjects
    new_subjects = []
    for subj in old_subjects:
        mapped = SUBJECT_MAP.get(subj)
        if mapped is None:
            # Subject not in map — keep as-is (should be very rare)
            if subj not in new_subjects:
                new_subjects.append(subj)
        else:
            for cat in mapped:
                if cat not in new_subjects:
                    new_subjects.append(cat)

    # Auto-assign if empty
    if not new_subjects:
        new_subjects = auto_assign(front)

    # Sort for consistency
    new_subjects.sort()

    # Update frontmatter
    front['subjects'] = new_subjects if new_subjects else None

    # Rebuild YAML frontmatter preserving order as much as possible
    new_front = yaml.dump(front, default_flow_style=False, allow_unicode=True, sort_keys=False, width=200)

    new_text = '---\n' + new_front + body

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_text)

    return True


def main():
    catalogue_dir = 'content/catalogue'
    files = [f for f in os.listdir(catalogue_dir) if f.endswith('.md') and f != '_index.en.md']

    total = 0
    updated = 0
    empty_before = 0
    empty_after = 0

    for fn in sorted(files):
        filepath = os.path.join(catalogue_dir, fn)
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()

        if not text.startswith('---'):
            continue

        total += 1
        end_idx = text.index('---', 3)
        front = yaml.safe_load(text[3:end_idx])
        old_subjects = front.get('subjects') or []

        if not old_subjects:
            empty_before += 1

        if remap_file(filepath):
            updated += 1

        # Check result
        with open(filepath, 'r', encoding='utf-8') as f:
            text2 = f.read()
        end_idx2 = text2.index('---', 3)
        front2 = yaml.safe_load(text2[3:end_idx2])
        new_subjects = front2.get('subjects') or []
        if not new_subjects:
            empty_after += 1

    print(f"Total files: {total}")
    print(f"Updated: {updated}")
    print(f"Empty subjects before: {empty_before}")
    print(f"Empty subjects after: {empty_after}")

    # Count unique categories now in use
    all_cats = set()
    for fn in sorted(files):
        filepath = os.path.join(catalogue_dir, fn)
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        if not text.startswith('---'):
            continue
        end_idx = text.index('---', 3)
        front = yaml.safe_load(text[3:end_idx])
        for s in (front.get('subjects') or []):
            all_cats.add(s)

    print(f"Unique categories in use: {len(all_cats)}")


if __name__ == "__main__":
    main()
