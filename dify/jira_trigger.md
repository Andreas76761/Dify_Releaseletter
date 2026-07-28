# Echter Jira-Trigger für die Dify-Pipeline

Dify hat keinen internen Jira-Node — der Workflow wird über die **Workflow-Run-API** gestartet.
Es gibt zwei saubere Wege, das automatisch bei neuen/aktualisierten Tickets zu tun.

## Option A — n8n-Brücke (empfohlen, robust)

Datei: `n8n/dify_bridge_jira_trigger.json`

```
Jira Trigger  →  Jira → Text (Map)  →  Dify Workflow ausführen (HTTP)
```

Warum robust: n8n empfängt das **wohlgeformte** Jira-Webhook-JSON und baut daraus sauber
`jira_text` (inkl. ADF-Beschreibung, Verknüpfungen, Versionen) — kein manuelles JSON-Escaping.

**Import & Setup**
1. n8n → Workflows → Import from File → `dify_bridge_jira_trigger.json`.
2. **Jira Trigger**: Credential *Jira SW Cloud* (bzw. *Jira Server*) hinterlegen; Events `issue_created`, `issue_updated`. n8n registriert den Webhook automatisch.
3. **Dify Workflow ausführen** (HTTP): Credential *HTTP Header Auth* mit `Authorization: Bearer app-XXXXXXXX` (App-API-Key aus Dify → deine Workflow-App → *API Access*).
4. Env-Variable `DIFY_API_URL` (Default `https://api.dify.ai/v1/workflows/run`; bei Self-Hosting `https://<dein-dify>/v1/workflows/run`).
5. Activate.

Der HTTP-Body, den n8n an Dify sendet:
```json
{
  "inputs": { "jira_text": "<gemappter Ticket-Text>", "target_language": "both", "country": "DE", "division": "", "user_group": "biz" },
  "response_mode": "blocking",
  "user": "jira-ONESCM-10263"
}
```

## Option B — Jira Automation → Dify (ohne n8n)

Direkt aus Jira, ohne Zwischentool.

1. **Project settings → Automation → Create rule.**
2. **Trigger:** *Issue created* (und eine zweite Regel/Trigger *Issue updated*).
3. **Action:** *Send web request*
   - **Web request URL:** `https://api.dify.ai/v1/workflows/run` (bzw. euer Self-Hosting-Host)
   - **HTTP method:** `POST`
   - **Headers:** `Authorization: Bearer app-XXXXXXXX` · `Content-Type: application/json`
   - **Web request body:** *Custom data*:
```json
{
  "inputs": {
    "jira_text": "Projekt: {{issue.project.key}}\nVorgang: {{issue.key}}\nZusammenfassung: {{issue.summary}}\nTyp: {{issue.issueType.name}}\nStatus: {{issue.status.name}}\nPrioritaet: {{issue.priority.name}}\nKomponente: {{#issue.components}}{{name}} {{/}}\nLoesung: {{issue.resolution.name}}\nLabels: {{issue.labels}}\nAutor: {{issue.reporter.displayName}}\nBearbeiter: {{issue.assignee.displayName}}\nErstellt: {{issue.created}}\nAktualisiert: {{issue.updated}}\nLoesungsversion(en): {{#issue.fixVersions}}{{name}} {{/}}\nBetrifft Version(en): {{#issue.versions}}{{name}} {{/}}\nVerknuepfungen: {{#issue.issuelinks}}{{type.outward}} {{outwardIssue.key}}{{inwardIssue.key}}; {{/}}\nBeschreibung:\n{{issue.description}}"
  },
  "response_mode": "blocking",
  "user": "jira-automation"
}
```

> **Achtung Escaping:** `{{issue.description}}` (und Kommentare) können Zeilenumbrüche/Anführungszeichen enthalten, die den JSON-Body brechen. Für Freitext-lastige Tickets ist **Option A** verlässlicher. Für kurze Tickets funktioniert Option B gut; alternativ das Beschreibungsfeld weglassen und nur Metadaten senden.

## Testen (curl)

```bash
curl -X POST "https://api.dify.ai/v1/workflows/run" \
  -H "Authorization: Bearer app-XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{"inputs":{"jira_text":"Projekt: DOT ONESCM\nVorgang: ONESCM-10263\nZusammenfassung: Contract Preview PDF when vehicle data not available\nTyp: Test\nStatus: Reviewed\nErstellt: 05/Feb/24\nLoesungsversion(en): Keine\nVerknuepfungen: is cloned by ONESCM-14533","target_language":"both","country":"DE","user_group":"biz"},"response_mode":"blocking","user":"test"}'
```

Erwartet: Datum **05/Feb/24**, Version **PI TBD**, Typ **Testfall/Validierung**, Status **Reviewed**, keine Zeilen zu ONESCM-14533.
