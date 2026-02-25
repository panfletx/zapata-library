#!/usr/bin/env python3
"""
Classify catalogue books using Claude API based on metadata.

Reads all content/catalogue/*.md files, sends metadata to Claude Haiku
in batches, and saves subject classifications to data/llm_subjects.yaml.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 scripts/classify-subjects.py
"""

import os
import sys
import json
import time
import yaml

import anthropic

# ── Valid categories (201) ──────────────────────────────────────────────────

VALID_CATEGORIES = [
    "Aesthetics", "American Literature",
    "Animals", "Anthology", "Arabic Literature",
    "Architecture", "Argentina", "Argentine Literature", "Autobiography & Memoir",
    "Avant-garde", "Beat Generation", "Berlin", "Bibliography", "Biography",
    "Bisexuality", "Brazil", "Brazilian Literature", "Buddhism", "Canada",
    "Caribbean", "Catholicism", "Chiapas", "Childhood",
    "Children's Literature", "Chile", "Chilean Literature", "China", "Chinese Literature", "Chronicle",
    "Classical Literature", "Colombia",
    "Comics & Graphic Novel", "Conquest of Mexico",
    "Correspondence", "Cuba", "Cuban Literature", "Dance", "Death & Mourning",
    "Detective & Mystery", "Diary & Letters", "Dictionary", "Diego Rivera",
    "Drama", "Dreams", "Dublin", "Economics", "Ecuador", "Education", "Egypt",
    "Encyclopedia", "English Literature", "Epic", "Erotic Literature", "Essay",
    "Ethics", "Existentialism", "Fable & Parable",
    "Family", "Fashion", "Feminism", "Fiction", "Film & Cinema",
    "Food & Gastronomy", "France", "French Literature",
    "Gay Literature", "Gender Studies",
    "German Literature", "Germany", "Grammar & Linguistics", "Greece",
    "Guatemala", "Guatemalan Literature", "Haiti", "Horror & Gothic",
    "Human Rights", "India", "Indigenous Peoples", "Interview",
    "Irish Literature", "Italian Literature", "Italy", "Jalisco",
    "Japan", "Japanese Literature",
    "Journalism", "Judaism",
    "King Arthur", "Latin America",
    "Latin American Literature", "Latin American Politics", "Law",
    "Lesbian Studies", "Literary Criticism", "Literary History", "Love & Desire",
    "Luis Buñuel", "Madrid",
    "Marxism", "Masculinity",
    "Medicine & Health", "Medieval History", "Medieval Literature", "Memory",
    "Mexican Literature", "Mexican Revolution", "Mexico", "Mexico City",
    "Middle East", "Migration & Exile", "Modern History",
    "Museums & Collections", "Music", "Mysticism", "Mythology",
    "National Identity", "Nature & Environment", "Netherlands", "New York",
    "Novel", "Novella", "Oaxaca", "Occult & Esoteric", "Opera",
    "Oral Tradition & Folklore", "Painting", "Paris", "Pedro Almodóvar", "Peru",
    "Philosophy", "Photography", "Poetry", "Portugal", "Postmodernism",
    "Pre-Columbian", "Prison", "Psychoanalysis",
    "Puerto Rico", "Queer Studies", "Race & Ethnicity", "Religion", "Rhetoric",
    "Rio de Janeiro", "Rome", "Rural Life", "Russia", "Russian Literature",
    "Saints & Hagiography", "Satire & Humor", "Science", "Science Fiction",
    "Screenplay", "Sculpture", "Sexuality & Eroticism",
    "Sherlock Holmes", "Short Stories", "Sigmund Freud",
    "Social Movements", "Spain",
    "Spanish Literature", "Speech & Lecture",
    "Structuralism & Poststructuralism", "Surrealism", "Symbolism",
    "Theses", "Transgender Studies", "Travel Writing",
    "Tristan & Iseult", "United Kingdom", "United States", "Urban Life",
    "Uruguay", "Uruguayan Literature", "Vienna", "Visual Art", "War & Conflict", "Yucatán",
]

CATEGORIES_STR = "\n".join(f"- {c}" for c in VALID_CATEGORIES)
CATEGORIES_SET = set(VALID_CATEGORIES)

# ── System prompt ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are a librarian classifying books for a bilingual (Spanish/English) personal library catalogue.

Given a batch of books with their metadata, assign 2-5 subject categories to each from the EXACT list below. Return ONLY categories from this list — no variations, no new categories.

VALID CATEGORIES:
{CATEGORIES_STR}

RULES:
1. Assign 2-5 categories per book. Prefer 3-4.
2. Use the EXACT category names from the list (case-sensitive, including accents and ampersands).
3. For literary works, always include the literary form (Fiction, Poetry, Short Stories, Essay, Drama, Novel, etc.) AND the national/regional literature (Mexican Literature, French Literature, etc.) when identifiable.
4. For translations, assign the ORIGINAL author's national literature, not the translation language. A Spanish translation of Flaubert is "French Literature", not "Spanish Literature".
5. Geographic categories (Mexico, France, etc.) are for books ABOUT that place, not just published there. A novel published in Barcelona about Mexico City gets "Mexico City", not "Spain".
6. "United States" and "American Literature" are for books by US authors or genuinely about the US. Latin American works should get "Latin America" or specific country categories instead.
7. For magazines/journals ("Revista, ..."), classify by the journal's primary topic area.
9. "Fiction" alone is never sufficient — always add at least one more specific category.
10. "Literary Criticism" is for works ABOUT literature (analysis, criticism, theory), not for literature itself.

OUTPUT FORMAT:
Return a JSON object where keys are the book IDs and values are arrays of category strings.
Example:
{{"book_1": ["Essay", "Latin America", "Mexican Literature"], "book_2": ["Poetry", "French Literature", "France"]}}

Return ONLY the JSON object, no other text."""

# ── Load catalogue ──────────────────────────────────────────────────────────

def load_catalogue(catalogue_dir="content/catalogue"):
    books = []
    for fname in sorted(os.listdir(catalogue_dir)):
        if not fname.endswith(".md"):
            continue
        filepath = os.path.join(catalogue_dir, fname)
        with open(filepath) as f:
            text = f.read()
        if not text.startswith("---"):
            continue
        end = text.index("---", 3)
        fm = yaml.safe_load(text[3:end])
        zotero_key = fname.replace(".md", "")
        books.append({
            "key": zotero_key,
            "title": fm.get("title", ""),
            "authors": fm.get("authors") or [],
            "languages": fm.get("languages") or [],
            "publishers": fm.get("publishers") or [],
            "place": fm.get("place", ""),
            "year": fm.get("year", ""),
            "item_types": fm.get("item_types") or [],
        })
    return books


def format_book(book, idx):
    """Format a single book's metadata for the prompt."""
    authors = ", ".join(book["authors"]) if book["authors"] else "Unknown"
    langs = ", ".join(book["languages"]) if book["languages"] else "Unknown"
    pubs = ", ".join(book["publishers"]) if book["publishers"] else "Unknown"
    types = ", ".join(book["item_types"]) if book["item_types"] else "Unknown"
    return (
        f"BOOK {idx} (id: {book['key']}):\n"
        f"  Title: {book['title']}\n"
        f"  Author(s): {authors}\n"
        f"  Language: {langs}\n"
        f"  Publisher: {pubs}\n"
        f"  Place: {book['place'] or 'Unknown'}\n"
        f"  Year: {book['year'] or 'Unknown'}\n"
        f"  Type: {types}"
    )

# ── API calls ───────────────────────────────────────────────────────────────

def classify_batch(client, books_batch, batch_num, total_batches):
    """Send a batch of books to Claude and get classifications."""
    books_text = "\n\n".join(
        format_book(b, i + 1) for i, b in enumerate(books_batch)
    )
    user_msg = f"Classify these {len(books_batch)} books:\n\n{books_text}"

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            text = response.content[0].text.strip()
            # Parse JSON from response (handle markdown code blocks)
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            result = json.loads(text)
            # Validate categories
            validated = {}
            for book_id, cats in result.items():
                valid = [c for c in cats if c in CATEGORIES_SET]
                if not valid:
                    valid = ["Fiction"]  # absolute fallback
                validated[book_id] = valid
            return validated

        except json.JSONDecodeError as e:
            print(f"  JSON parse error on attempt {attempt + 1}: {e}")
            print(f"  Raw response: {text[:200]}...")
            if attempt < 2:
                time.sleep(2)
        except anthropic.RateLimitError:
            wait = 30 * (attempt + 1)
            print(f"  Rate limited, waiting {wait}s...")
            time.sleep(wait)
        except Exception as e:
            print(f"  Error on attempt {attempt + 1}: {e}")
            if attempt < 2:
                time.sleep(5)

    # If all attempts fail, return None
    return None


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        print("Run: export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Load existing results to support resuming
    output_path = "data/llm_subjects.yaml"
    if os.path.exists(output_path):
        with open(output_path) as f:
            results = yaml.safe_load(f) or {}
        print(f"Loaded {len(results)} existing classifications from {output_path}")
    else:
        results = {}

    # Load catalogue
    books = load_catalogue()
    print(f"Loaded {len(books)} books from catalogue")

    # Filter out already-classified books
    remaining = [b for b in books if b["key"] not in results]
    print(f"Remaining to classify: {len(remaining)}")

    if not remaining:
        print("All books already classified!")
        return

    # Process in batches of 20
    batch_size = 20
    batches = [remaining[i:i + batch_size] for i in range(0, len(remaining), batch_size)]
    total = len(batches)

    print(f"Processing {total} batches of ~{batch_size} books each...")
    print()

    for i, batch in enumerate(batches):
        print(f"Batch {i + 1}/{total} ({len(batch)} books)...", end=" ", flush=True)
        classified = classify_batch(client, batch, i + 1, total)

        if classified is None:
            print("FAILED — skipping batch")
            continue

        # Map back using book keys
        for book in batch:
            key = book["key"]
            # The LLM might use the key directly or "book_N" format
            if key in classified:
                results[key] = classified[key]
            else:
                # Try to find by any key that matches
                found = False
                for resp_key, cats in classified.items():
                    if key in resp_key or resp_key in key:
                        results[key] = cats
                        found = True
                        break
                if not found:
                    # Fall back to positional matching
                    items = list(classified.values())
                    idx = batch.index(book)
                    if idx < len(items):
                        results[key] = items[idx]

        classified_count = sum(1 for b in batch if b["key"] in results)
        print(f"OK ({classified_count}/{len(batch)} classified)")

        # Save progress after each batch
        os.makedirs("data", exist_ok=True)
        with open(output_path, "w") as f:
            yaml.dump(results, f, default_flow_style=False, allow_unicode=True, width=200)

        # Small delay between batches to avoid rate limits
        if i < total - 1:
            time.sleep(1)

    # Final stats
    print()
    print(f"Total classified: {len(results)}/{len(books)}")

    # Category frequency
    from collections import Counter
    cat_counts = Counter()
    for cats in results.values():
        for c in cats:
            cat_counts[c] += 1
    print(f"Unique categories used: {len(cat_counts)}")
    print()
    print("Top 20 categories:")
    for cat, count in cat_counts.most_common(20):
        print(f"  {count:4d}  {cat}")

    # Check for invalid categories
    invalid = set()
    for cats in results.values():
        for c in cats:
            if c not in CATEGORIES_SET:
                invalid.add(c)
    if invalid:
        print(f"\nWARNING: {len(invalid)} invalid categories found:")
        for c in sorted(invalid):
            print(f"  - {c}")


if __name__ == "__main__":
    main()
