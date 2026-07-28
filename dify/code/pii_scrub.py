# Dify Code node (Python 3) — "PII Scrub" (safety net after the LLM)
# Masks any personal / identifying data that may have slipped into the letter.
# Inputs : text_de, text_en
# Outputs: clean_de, clean_en, removed (comma-separated list of what was masked)

import re

PATTERNS = [
    (r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",          "[E-Mail entfernt]",      "E-Mail"),
    (r"\b[A-HJ-NPR-Z0-9]{17}\b",                "[FIN/VIN entfernt]",     "FIN/VIN"),
    (r"\b[A-ZÄÖÜ]{1,3}-[A-Z]{1,2}\s?\d{1,4}\b", "[Kennzeichen entfernt]", "Kennzeichen"),
    (r"\b[Uu](?:ID|SR)?\d{5,}\b",               "[User-ID entfernt]",     "User-ID"),
]


def _scrub(text):
    t = text or ""
    hits = set()
    for pat, repl, label in PATTERNS:
        if re.search(pat, t):
            hits.add(label)
            t = re.sub(pat, repl, t)
    return t, hits


def main(text_de: str = "", text_en: str = "") -> dict:
    de, h1 = _scrub(text_de)
    en, h2 = _scrub(text_en)
    removed = ", ".join(sorted(h1 | h2)) if (h1 | h2) else "keine"
    return {"clean_de": de, "clean_en": en, "removed": removed}
