# oneSCM Releaseletter-Generator — Dify-Pipeline

Erzeugt aus einem **Jira-Ticket** direkt beim Generieren einen **belegten Releaseletter (DE + EN)** samt **Zusammenfassung** — mit denselben Guardrails wie das Prüf-Tool: Datum aus „Erstellt", keine erfundene PI-Version, keine Phantom-Tickets, Status/Typ wahrheitsgemäß, keine personenbezogenen Daten.

## Dateien

| Datei | Zweck |
|---|---|
| `releaseletter_pipeline.yml` | Importierbare Dify-Workflow-DSL (kompletter Graph inkl. Code + Prompts) |
| `code/extract_prepare.py` | Code-Node „Extract & Prepare" (deterministische Extraktion + Guardrails) |
| `code/pii_scrub.py` | Code-Node „PII-Scrub" (Sicherheitsnetz nach dem LLM) |

## Import in Dify

1. **Studio → Create App → Import DSL** → `releaseletter_pipeline.yml` hochladen.
2. In **jedem LLM-Node** (`Releaseletter DE`, `Übersetzung EN`, `Zusammenfassung DE/EN`) das **Modell neu auswählen** — die Provider/Model-Angaben in der DSL sind Platzhalter (`openai / gpt-4o`). Wähle euer konfiguriertes Modell (z. B. Claude Opus/Sonnet, GPT-4o …).
3. **Run** → Eingaben ausfüllen → Ergebnis prüfen.

> Falls der Import an der Provider-Kennung scheitert: App leer anlegen und die Nodes anhand des Abschnitts **„Nodes im Detail"** manuell nachbauen — die Code- und Prompt-Inhalte sind unten vollständig.

## Ablauf (Graph)

```
Start ─▶ Extract & Prepare (Code) ─▶ Releaseletter DE (LLM) ─▶ Übersetzung EN (LLM) ─▶ Zusammenfassung DE/EN (LLM) ─▶ PII-Scrub (Code) ─▶ End
```

## Eingaben (Start-Node)

| Variable | Typ | Beschreibung |
|---|---|---|
| `jira_text` | Paragraph | Der Jira-Ticket-Text/-Export (Felder + Beschreibung) |
| `target_language` | Select `de/en/both` | Ausgabesprache(n) |
| `country` | Text | Land/Markt (z. B. DE, FR …) — beeinflusst Zielgruppen-Hinweis |
| `division` | Text | Sparte |
| `user_group` | Select `mgmt/biz/it/end` | Detailgrad/Ton |

## Ausgaben (End-Node)

`releaseletter_de`, `releaseletter_en`, `zusammenfassung` (DE + EN), `fakten` (belegte Quellfakten), `warnungen` (Guardrail-Hinweise), `pii_entfernt` (was der Scrub maskiert hat).

## Nodes im Detail

### 1) Start
Fünf Eingabevariablen wie oben.

### 2) Extract & Prepare — Code (Python 3)
Parst das Ticket deterministisch (kein LLM → keine Halluzination) und leitet die Guardrails ab:
- `pi_label` = `PI TBD`, wenn keine Fix-/betroffene Version in der Quelle steht (sonst der belegte Wert),
- `report_date` = Jira-Feld „Erstellt",
- `linked_ids` = Ticket-IDs aus „Verknüpfungen" (dürfen **nicht** als Inhalt erscheinen),
- `pii_found` = erkannte personenbezogene Daten,
- `facts` = sauberer Fakten-Block, den die LLMs verwenden,
- `guidance`/`warnings` = Zielgruppen- und Prüfhinweise.

Code: siehe `code/extract_prepare.py` (identisch in der DSL hinterlegt).

### 3) Releaseletter DE — LLM
System-Prompt mit fünf harten Regeln (Datum / PI / Umfang / Status+Typ / Datenschutz), Zielgruppe und Fakten. Referenziert die Extract-Ausgaben über `{{#extract.facts#}}`, `{{#extract.pi_label#}}`, `{{#extract.report_date#}}`, `{{#extract.linked_ids#}}`, `{{#extract.guidance#}}`, `{{#extract.warnings#}}`, `{{#extract.pii_found#}}`.

### 4) Übersetzung EN — LLM
Übersetzt den **deutschen** Letter (`{{#llm_de.text#}}`) 1:1 ins Englische; Zahlen/IDs/Daten/Version bleiben identisch, Produktbegriffe unverändert, `[redaktionell]` → `[editorial]`.

### 5) Zusammenfassung DE/EN — LLM
Kurze, belegte Zusammenfassung aus `{{#extract.facts#}}` im Format `DE: …` / `EN: …`.

### 6) PII-Scrub — Code (Python 3)
Maskiert E-Mail, FIN/VIN, Kennzeichen, User-ID im DE- und EN-Letter (Sicherheitsnetz). Code: siehe `code/pii_scrub.py`.

### 7) End
Mappt die Endausgaben (siehe oben).

## Guardrails = die vier Kern-Fehlerquellen

| Fehlerquelle | Wo abgesichert |
|---|---|
| Datum aus Laufdatum statt „Erstellt" | `report_date` (Code) + Regel 1 (Prompt) |
| Erfundene PI-Version | `pi_label = PI TBD` (Code) + Regel 2 (Prompt) |
| Phantom-Tickets aus Verknüpfungen | `linked_ids` (Code) + Regel 3 (Prompt) |
| Status/Typ verfälscht | „wörtlich"/„Testfall/Validierung" (Code+Prompt, Regel 4) |
| Personenbezogene Daten | Regel 5 (Prompt) + **PII-Scrub-Code** als Netz |

## Test-Eingabe (ONESCM-10263)

```
Projekt: DOT ONESCM
Vorgang: ONESCM-10263
Zusammenfassung: Service Contract | Contract Preview PDF when vehicle data not available
Typ: Test
Status: Reviewed
Priorität: Hoch
Komponente: 8 - Documents & Communications
Autor: Lorand Markus
Bearbeiter: Nicht zugewiesen
Erstellt: 05/Feb/24
Betrifft Version(en): Keine
Lösungsversion(en): Keine
Verknüpfungen: is cloned by ONESCM-14533; tests ONESCM-9045; relates to ONESCM-1846, ONESCM-8703
Beschreibung:
Current State: Contract Preview PDF cannot be generated when chassis/licence/Baumuster is missing.
Target State: Display the correct Contract Preview PDF even when vehicle data is not available.
Business Flow: In Contract Generation select Chassis/Order/Model Code; TOGGLE First Registration date unavailable.
Acceptance Criteria: When vehicle data is unavailable, the system displays the correct contract preview PDF.
```

Erwartet: Datum **05/Feb/24**, Version **PI TBD**, Typ **Testfall/Validierung**, Status **Reviewed**, **keine** Zeilen zu ONESCM-14533/-9045/-1846/-8703, kein Personenname.

## Batch (viele Tickets)

Für mehrere Tickets: den Kern-Workflow als **Tool/Workflow-App** veröffentlichen und über eine übergeordnete Workflow-App mit **Iteration-Node** über eine Ticketliste laufen lassen (jedes Element → dieser Workflow). Alternativ per Dify-API je Ticket aufrufen.
