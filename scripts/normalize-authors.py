#!/usr/bin/env python3
"""
Normalize duplicate author name variants across all catalogue files.
Merges the less-common/incorrect form into the preferred simpler form.
"""

import os
import re

CONTENT_DIR = "content/catalogue"

# Maps: old name → preferred name
AUTHOR_MAP = {
    # Leopoldo Alas "Clarín"
    "Alas y Ureña, Leopoldo": "Alas, Leopoldo",
    # Balzac abbreviation
    "Balzac, H. de": "Balzac, Honoré de",
    # Paul Bowles
    "Bowles, Paul Frederich": "Bowles, Paul",
    # Calderón de la Barca (add first name)
    "Calderón de la Barca": "Calderón de la Barca, Pedro",
    # Dostoevsky
    "Dostoievski, Fedor Mikhailovich": "Dostoievski, Fiodor",
    # Umberto Eco (misspelled as Humberto)
    "Eco, Humberto": "Eco, Umberto",
    # Lucien Febvre
    "Febvre, Lucien Paul Victor": "Febvre, Lucien",
    # Flaubert (misspelled Gustav)
    "Flaubert, Gustav": "Flaubert, Gustave",
    # Viktor Frankl
    "Frankl, Viktor Emil": "Frankl, Viktor E.",
    # Jean Genet (last name only → full name)
    "Genet": "Genet, Jean",
    # Marta Guastavino
    "Guastavino, Marta I.": "Guastavino, Marta",
    # Alexander von Humboldt (Spanish/wrong-particle variants)
    "Humboldt, Alejandro De": "Humboldt, Alexander von",
    "Humboldt, Alexander de": "Humboldt, Alexander von",
    # Kazantzakis (lowercase typo)
    "Kazantzakis, nikos": "Kazantzakis, Nikos",
    # Jiddu Krishnamurti (initial → full first name)
    "Krishnamurti, J.": "Krishnamurti, Jiddu",
    # Machado de Assis (with first name → without)
    "Machado de Assis, Joaquin": "Machado de Assis",
    # Gaston Mauger
    "Mauger, G.": "Mauger, Gaston",
    # Álvaro Mutis (missing accent)
    "Mutis, Alvaro": "Mutis, Álvaro",
    # Marquis de Sade (full name → common form)
    "Sade, Donatien Alphonse François": "Sade",
    # J. D. Salinger
    "Salinger, Jerome David": "Salinger, J. D.",
    # José María Valverde (missing accents)
    "Valverde, Jose Maria": "Valverde, José María",
    # Alan Watts
    "Watts, Alan Watson": "Watts, Alan",
    # Óscar Zorrilla (missing accent)
    "Zorrilla, Oscar": "Zorrilla, Óscar",
}


def normalize_file(path, author_map):
    with open(path) as f:
        content = f.read()

    original = content

    # Parse and replace author lines one by one
    def replace_author_line(m):
        block = m.group(0)
        new_block = block
        for old, new in author_map.items():
            # Match exact author name in a list item
            new_block = re.sub(
                rf'^(- ){re.escape(old)}$',
                rf'\g<1>{new}',
                new_block,
                flags=re.MULTILINE
            )
        return new_block

    content = re.sub(
        r'^authors:\s*\n((?:- .+\n)+)',
        replace_author_line,
        content,
        flags=re.MULTILINE
    )

    if content != original:
        with open(path, 'w') as f:
            f.write(content)
        return True
    return False


def main():
    files = [f for f in os.listdir(CONTENT_DIR) if f.endswith('.md')]
    updated = 0
    changes = {}

    for fn in sorted(files):
        path = os.path.join(CONTENT_DIR, fn)
        with open(path) as f:
            content = f.read()

        # Detect which mappings apply
        m = re.search(r'^authors:\s*\n((?:- .+\n)+)', content, re.MULTILINE)
        if not m:
            continue
        block = m.group(0)
        for old, new in AUTHOR_MAP.items():
            if re.search(rf'^- {re.escape(old)}$', block, re.MULTILINE):
                changes.setdefault(old, []).append(fn)

        if normalize_file(path, AUTHOR_MAP):
            updated += 1

    print(f"Updated {updated} files\n")
    print("Changes applied:")
    for old, new in AUTHOR_MAP.items():
        files_changed = changes.get(old, [])
        if files_changed:
            print(f"  {old!r} → {new!r}  ({len(files_changed)} file(s))")


if __name__ == "__main__":
    main()
