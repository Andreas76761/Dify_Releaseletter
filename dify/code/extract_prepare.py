# Dify Code node (Python 3) — "Extract & Prepare"
# Deterministic parsing of a Jira ticket export + quality guardrails.
# Inputs : jira_text, target_language, country, division, user_group
# Outputs: facts, pi_label, report_date, linked_ids, pii_found, guidance, warnings, target_language
#
# This node produces ONLY verified facts from the source. The LLM nodes must
# generate the release letter strictly from these facts (no invention).

import re

FIELD_DEFS = [
    ("ticket",         r"(?:Vorgang|Ticket|Issue|Key)\s*[:\-]\s*([A-Z][A-Z0-9]+-\d+)"),
    ("summary",        r"(?:Zusammenfassung|Summary|Titel|Title)\s*[:\-]\s*(.+)"),
    ("typ",            r"(?:Vorgangstyp|Issue\s*Type|Typ|Type)\s*[:\-]\s*(.+)"),
    ("status",         r"(?:^|\n)\s*Status\s*[:\-]\s*(.+)"),
    ("prioritaet",     r"(?:Priorit(?:ä|ae)t|Priority)\s*[:\-]\s*(.+)"),
    ("projekt",        r"(?:Projekt|Project)\s*[:\-]\s*(.+)"),
    ("komponente",     r"(?:Komponenten?|Components?)\s*[:\-]\s*(.+)"),
    ("resolution",     r"(?:L(?:ö|oe)sung|Resolution)\s*[:\-]\s*(.+)"),
    ("labels",         r"(?:Labels?|Stichw(?:ö|oe)rter|Beschriftungen)\s*[:\-]\s*(.+)"),
    ("autor",          r"(?:Autor|Reporter|Ersteller)\s*[:\-]\s*(.+)"),
    ("bearbeiter",     r"(?:Bearbeiter|Assignee|Zugewiesen an)\s*[:\-]\s*(.+)"),
    ("erstellt",       r"(?:Erstellt|Created)\s*[:\-]\s*(.+)"),
    ("aktualisiert",   r"(?:Aktualisiert|Updated|Ge(?:ä|ae)ndert)\s*[:\-]\s*(.+)"),
    ("fixversion",     r"(?:Fix[- ]?Versions?|L(?:ö|oe)sungsversion(?:\(en\)|en)?)\s*[:\-]\s*(.+)"),
    ("affected",       r"(?:Betrifft Version(?:\(en\)|en)?|Affects?\s*Versions?|Betroffene Version(?:en)?)\s*[:\-]\s*(.+)"),
    ("verknuepfungen", r"(?:Verkn(?:ü|ue)pfungen|Linked issues|Links)\s*[:\-]\s*(.+)"),
]


def _extract(text):
    out = {}
    for key, pat in FIELD_DEFS:
        m = re.search(pat, text, re.IGNORECASE)
        if m and m.group(1):
            out[key] = m.group(1).strip()
    return out


def _is_none(v):
    return (not v) or bool(re.search(r"keine|none", v, re.I))


def main(jira_text: str, target_language: str = "both", country: str = "DE",
         division: str = "", user_group: str = "biz") -> dict:
    text = jira_text or ""
    f = _extract(text)

    no_version = _is_none(f.get("fixversion", "")) and _is_none(f.get("affected", ""))
    pi_label = "PI TBD" if no_version else (f.get("fixversion") or f.get("affected"))
    report_date = f.get("erstellt", "") or "unbekannt (Quelle prüfen)"

    linked = re.findall(r"[A-Z]+-\d+", f.get("verknuepfungen", "") or "")
    linked_ids = ", ".join(sorted(set(linked)))

    typ = f.get("typ", "")
    typ_norm = "Testfall / Validierung" if re.search(r"test", typ, re.I) else (typ or "unbekannt")

    def _sec(name):
        m = re.search(name + r"\s*[:\-]\s*([^\n]+)", text, re.I)
        return m.group(1).strip() if m else ""

    desc = {
        "current": _sec("Current State"),
        "target":  _sec("Target State"),
        "flow":    _sec("Business Flow"),
        "extra":   _sec("Extra Details"),
        "accept":  _sec("Acceptance Criteria"),
    }

    # PII safety flag (the letter must not contain these)
    pii = []
    if re.search(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", text):
        pii.append("E-Mail")
    if re.search(r"\b[A-HJ-NPR-Z0-9]{17}\b", text):
        pii.append("FIN/VIN")
    if re.search(r"\b[A-ZÄÖÜ]{1,3}-[A-Z]{1,2}\s?\d{1,4}\b", text):
        pii.append("Kennzeichen")
    for n in (f.get("autor", ""), f.get("bearbeiter", "")):
        if n and not re.search(r"nicht zugewiesen|unassigned", n, re.I):
            pii.append("Name: " + n)
    pii_found = "; ".join(pii) if pii else "keine"

    lines = []

    def add(label, val):
        if val:
            lines.append("- %s: %s" % (label, val))

    add("Referenz", f.get("ticket"))
    add("Titel", f.get("summary"))
    add("Vorgangstyp (wahrheitsgemäß)", typ_norm)
    add("Status (wörtlich)", f.get("status"))
    add("Priorität", f.get("prioritaet"))
    add("Projekt", f.get("projekt"))
    add("Komponente", f.get("komponente"))
    add("Resolution", f.get("resolution"))
    add("Labels", f.get("labels"))
    add("Release/Version", pi_label)
    add("Datum (aus 'Erstellt')", report_date)
    add("Aktueller Zustand", desc["current"])
    add("Zielzustand", desc["target"])
    add("Ablauf", desc["flow"])
    add("Zusätzliche Details", desc["extra"])
    add("Abnahmekriterien", desc["accept"])
    facts = "\n".join(lines)

    ug_map = {
        "mgmt": "Management: Kurzfassung, nur belegte Fakten, keine Marketing-Aussagen.",
        "biz":  "Fachbereich: sachlich, ausgewogen.",
        "it":   "IT/Entwicklung: technische Metadaten inkl. Labels/Komponente.",
        "end":  "Endanwender: einfache Sprache, minimale Metadaten.",
    }
    guidance = "Land %s, Sparte %s — %s" % (country, division or "-", ug_map.get(user_group, ug_map["biz"]))

    warnings = []
    if re.search(r"test", typ, re.I):
        warnings.append("Quelle ist Typ 'Test' → nicht als Feature darstellen.")
    if no_version:
        warnings.append("Keine Version in Quelle → PI TBD, keine PI erfinden.")
    if linked_ids:
        warnings.append("Verlinkte Tickets NICHT als Inhalt/Scope: %s" % linked_ids)
    if pii_found != "keine":
        warnings.append("Personenbezogene Daten vorhanden → anonymisieren: %s" % pii_found)

    return {
        "facts": facts,
        "pi_label": pi_label,
        "report_date": report_date,
        "linked_ids": linked_ids or "keine",
        "pii_found": pii_found,
        "guidance": guidance,
        "warnings": "\n".join("- " + w for w in warnings) if warnings else "- keine",
        "target_language": target_language or "both",
    }
