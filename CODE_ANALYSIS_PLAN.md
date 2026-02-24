# Webmacs – Code-Qualitätsanalyse: Task-Plan (Divide & Conquer)

> **Stand:** 2026-02-24  
> **Ziel:** Systematische Bewertung von Wartbarkeit, Lesbarkeit, Verständlichkeit, Austauschbarkeit, Skalierbarkeit und Erweiterbarkeit  
> **Methode:** Jede Task = 1–3 Dateien, eigenständig mit günstigem LLM abarbeitbar  
> **Constraint:** `just qa` muss nach jeder Änderung grün bleiben

---

## Status-Legende

| Symbol | Bedeutung |
|--------|-----------|
| ⬜ | Nicht gestartet |
| 🔵 | In Bearbeitung |
| ✅ | Abgeschlossen |
| 🔴 | Blockiert |
| ⚠️ | Befund mit Handlungsbedarf |

## Prioritäten

| Code | Bedeutung |
|------|-----------|
| P1 | Kritisch – behindert Wartbarkeit/Sicherheit direkt |
| P2 | Wichtig – signifikante Verbesserung der Codequalität |
| P3 | Nice-to-have – polish, minor improvements |

## Token-Schätzung

| Größe | Tokens | Dateigröße ca. |
|-------|--------|----------------|
| S | < 2k | < 100 Zeilen |
| M | 2–5k | 100–300 Zeilen |
| L | 5–10k | 300–600 Zeilen |
| XL | > 10k | mehrere Dateien / > 600 Zeilen |

---

## Phase 1: Backend – Kernstruktur (Fundament)

> Diese Tasks analysieren die Basisschicht. Alle weiteren Phasen bauen darauf auf.

### B1 – `models.py`: Monolithische ORM-Modelle
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | L (412 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/models.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | – (Fundament) |

**Ziel:** Prüfen ob alle SQLAlchemy-Entities in einer Datei ein Wartbarkeitsproblem darstellen.

**Analysefragen:**
1. Wie viele Entities/Klassen sind definiert? Sind Verantwortlichkeiten klar getrennt?
2. Gibt es fehlende `__repr__`-Methoden, unklare Relationship-Definitionen oder fehlende Indizes?
3. Sind alle Fremdschlüssel-Constraints korrekt definiert (ON DELETE, nullable)?
4. Gibt es zirkuläre Abhängigkeiten zwischen Models?
5. Werden `created_at`/`updated_at`-Timestamps konsistent via Mixin oder Basisklasse gesetzt?
6. Sind Spalten-Defaults sinnvoll (server_default vs. Python-Default)?

**Output-Format:** Liste mit Befunden pro Entity, Verbesserungsvorschlag (refactor in Sub-Module? Basis-Mixin einführen?)

---

### B2 – `schemas.py`: Monolithische Pydantic-Schemas
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | XL (585 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/schemas.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B1 |

**Ziel:** Bewerten ob 585 Zeilen Schema-Definitionen in einer Datei DRY-Verletzungen und Lesbarkeit beeinträchtigen.

**Analysefragen:**
1. Gibt es Schema-Duplikation (Create/Update/Response-Triplets ähnlicher Struktur)?
2. Werden `model_validator` / `field_validator` konsistent eingesetzt?
3. Sind Response-Schemas vollständig typisiert oder gibt es `Any`-Felder?
4. Gibt es Schemas die nur für interne Nutzung existieren (könnten in `models.py` verbleiben)?
5. Werden gemeinsame Felder (z.B. `id`, `created_at`) in Basis-Schemas ausgelagert?
6. Sind `orm_mode`/`from_attributes` korrekt gesetzt?

**Output-Format:** Schema-Inventur-Tabelle, Splitting-Empfehlung nach Domain (z.B. `schemas/events.py`, `schemas/users.py`)

---

### B3 – `repository.py` + `database.py`: Datenbankschicht
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | M (120 + 75 = 195 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/repository.py`, `backend/src/webmacs_backend/database.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B1 |

**Ziel:** Bewerten der generischen Repository-Abstraktion und des DB-Session-Managements.

**Analysefragen:**
1. Ist das Repository-Pattern vollständig umgesetzt oder werden Raw-Queries in den Routern verwendet?
2. Wird `AsyncSession` korrekt genutzt? Gibt es potenzielle N+1-Query-Probleme?
3. Ist Connection-Pooling konfigurierbar?
4. Werden Transactions explizit verwaltet oder implizit via Context-Manager?
5. Gibt es Query-Logging / Slow-Query-Detection?
6. Ist die Session-Dependency in `dependencies.py` korrekt auf `async with` aufgebaut?

**Output-Format:** Befundliste, konkrete Code-Beispiele für gefundene Antipatterns

---

### B4 – `config.py` + `dependencies.py`: Settings & Dependency Injection
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (107 + 115 = 222 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/config.py`, `backend/src/webmacs_backend/dependencies.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | – |

**Ziel:** Prüfen ob Settings sauber via Pydantic Settings verwaltet werden und ob DI-Abhängigkeiten austauschbar sind.

**Analysefragen:**
1. Wird `pydantic-settings` mit `BaseSettings` und Env-Var-Validierung verwendet?
2. Sind sensible Felder (Passwörter, Secrets) mit `SecretStr` typisiert?
3. Gibt es Hard-coded Default-Werte die ein Sicherheitsrisiko darstellen?
4. Sind FastAPI-Dependencies testbar (können gemockt werden)?
5. Gibt es zirkuläre Import-Abhängigkeiten?
6. Werden alle Settings dokumentiert (Docstrings, Beschreibung)?

**Output-Format:** Befundliste mit Sicherheits-Markierung, Verbesserungsvorschläge für Testbarkeit der Dependencies

---

### B5 – `enums.py`: Enum-Organisation
| Feld | Wert |
|------|------|
| **Priorität** | P3 |
| **Token-Größe** | M (127 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/enums.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | – |

**Ziel:** Prüfen ob Enums konsistent, vollständig und gut dokumentiert sind.

**Analysefragen:**
1. Werden `StrEnum` / `IntEnum` korrekt und konsistent genutzt?
2. Sind alle Enum-Werte beschrieben (Docstrings auf Enum-Klasse und/oder Wert-Level)?
3. Gibt es Redundanzen zwischen Enums oder mit `models.py`-Konstanten?
4. Sind Enums auch im Frontend (TypeScript) synchronisiert oder muss das manuell gepflegt werden?
5. Könnte eine Code-Generation (z.B. `openapi-typescript`) diese Synchronisierung automatisieren?

**Output-Format:** Enum-Inventurübersicht, Synchronisierungsempfehlung

---

### B6 – `main.py`: App-Konfiguration & Router-Registration
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (214 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/main.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | – |

**Ziel:** Prüfen ob App-Startup klar, modular und testbar ist.

**Analysefragen:**
1. Gibt es Startup/Shutdown-Lifespan-Events? Werden Ressourcen sauber freigegeben?
2. Ist CORS korrekt und sicher konfiguriert (keine `allow_origins=["*"]` in Production)?
3. Werden alle Router mit konsistenten Tags/Präfixen registriert?
4. Ist globales Error-Handling implementiert (HTTPException-Handler, Validation-Error-Handler)?
5. Gibt es eine global konfigurierte OpenAPI-Beschreibung (Titel, Version, Contact)?
6. Werden Middleware in sinnvoller Reihenfolge registriert?

**Output-Format:** Checkliste Security/Korrektheit, konkrete Konfigurationsempfehlungen

---

### B7 – `security.py`: Auth & JWT
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | S (89 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/security.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B4 |

**Ziel:** Sicherheitsbewertung der JWT-Implementierung.

**Analysefragen:**
1. Wird `python-jose` oder `PyJWT`? Ist das Library aktuell (bekannte CVEs)?
2. Ist der Secret-Key aus der Config und **nicht** hard-coded?
3. Werden Token-Expiry, Audience und Issuer validiert?
4. Gibt es Refresh-Token-Mechanismus? Wie werden Token invalidiert (Blacklist/DB)?
5. Ist Passwort-Hashing sicher (bcrypt mit angemessenem Work-Factor)?
6. Werden Security-relevante Events geloggt (failed logins, token refresh)?

**Output-Format:** Security-Checkliste (Pass/Fail/Warning), priorisierte Risiken

---

## Phase 2: API-Layer (Router-Analyse)

> Jede Task fokussiert auf 1–2 thematisch verwandte Router-Dateien.

### A1 – `auth.py` + `tokens.py`: Authentifizierung & Token-Management
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | M (50 + 104 = 154 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/api/v1/auth.py`, `backend/src/webmacs_backend/api/v1/tokens.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B7 |

**Analysefragen:**
1. Sind Login-Endpoints gegen Brute-Force abgesichert (Rate-Limiting)?
2. Wird das Passwort im Error-Log niemals geloggt?
3. Sind API-Token-Endpoints (CRUD) vollständig mit RBAC geschützt?
4. Gibt es einen Logout-Endpoint der Token invalidiert?
5. Werden HTTP-only Cookies oder Bearer-Token verwendet? Sind CSRF-Risks bedacht?

---

### A2 – `users.py` + `health.py`: User-CRUD & Health-Check
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | S (76 + 78 = 154 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/api/v1/users.py`, `backend/src/webmacs_backend/api/v1/health.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B3, B4 |

**Analysefragen:**
1. Ist User-CRUD vollständig (List, Get, Create, Update, Delete, Change-Password)?
2. Werden Rollen-Checks konsistent via Dependency oder im Handler implementiert?
3. Prüft der Healthcheck DB-Connectivity, externe Services und Cache?
4. Gibt es Liveness vs. Readiness Endpoints (für Kubernetes)?
5. Werden sensible User-Daten (Passwort-Hash) nie in Response-Schemas zurückgegeben?

---

### A3 – `events.py` + `experiments.py`: Kern-Domäne
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (66 + 145 = 211 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/api/v1/events.py`, `backend/src/webmacs_backend/api/v1/experiments.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B3 |

**Analysefragen:**
1. Gibt es Pagination für List-Endpoints (`offset`/`limit` oder Cursor-basiert)?
2. Gibt es Filter/Sort-Parameter? Werden diese sicher an die DB weitergegeben (kein SQL-Injection-Risiko)?
3. Sind Status-Transitions (Event-States, Experiment-States) als State-Machine modelliert oder if/else-Logik?
4. Werden Business-Rule-Validierungen im Router oder in einem Service gemacht?
5. Sind Event-Timestamps timezone-aware?

---

### A4 – `datapoints.py` + `logging.py`: Zeitreihendaten & Audit-Log
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | M (137 + 165 = 302 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/api/v1/datapoints.py`, `backend/src/webmacs_backend/api/v1/logging.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B3, S2 |

**Analysefragen:**
1. Wie werden große Datenmengen (Zeitreihendaten) paginiert – gibt es Time-Range-Filter?
2. Gibt es Bulk-Ingestion-Endpoints? Wie werden Batches transaktional behandelt?
3. Wird der Log-Endpoint durch `background_tasks` oder einen Queue entkoppelt?
4. Gibt es Retention-Policies für alte Datenpunkte und Logs?
5. Werden Datapoint-Queries durch DB-Indizes optimiert (Index auf `timestamp`, `key`)?
6. Gibt es Aggregations-Endpoints (min/max/avg pro Zeitraum) oder muss der Client alle Daten laden?

---

### A5 – `dashboards.py`: Dashboard-Management
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (181 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/api/v1/dashboards.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B3 |

**Analysefragen:**
1. Werden Dashboard-Konfigurationen als JSON/JSONB gespeichert? Gibt es Schema-Validierung?
2. Gibt es Sharing/Permission-Modelle für Dashboards (Public/Private/Team)?
3. Gibt es Import/Export-Funktionalität? Format-Stabilität?
4. Werden Widget-Definitionen von Datapoint-Abfragen entkoppelt?
5. Gibt es einen Preview-Mechanismus ohne alle Daten zu laden?

---

### A6 – `webhooks.py` + `rules.py`: Event-Driven Features
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (142 + 106 = 248 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/api/v1/webhooks.py`, `backend/src/webmacs_backend/api/v1/rules.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | S1, S4 |

**Analysefragen:**
1. Können Webhooks sicher konfiguriert werden (HTTPS-Validierung, Secret-Rotation)?
2. Gibt es eine Retry-Konfiguration pro Webhook (oder ist sie global)?
3. Wie werden Regeln validiert? Gibt es einen Dry-Run-Endpoint?
4. Sind Regeln als DSL oder as-Code definiert? Wie erweiterbar ist das Rule-Format?
5. Gibt es Zirkulär-Regel-Erkennung (Rule A triggert Rule B triggert Rule A)?

---

### A7 – `plugins.py` (API): God-Router-Analyse
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | XL (513 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/api/v1/plugins.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | S5 |

**Ziel:** Prioritär! Mit 513 Zeilen ist dies der größte Router – clear God-Router-Kandidat.

**Analysefragen:**
1. Wie viele unterschiedliche Verantwortlichkeiten hat dieser Router (Plugin-CRUD, Config, Status, Packages, Config-Sync...)?
2. Welche Endpunkte könnten in eigenständige Router ausgelagert werden?
3. Gibt es Business-Logik direkt im Router (die in Services gehört)?
4. Werden alle Plugin-Aktionen (start/stop/restart) idempotent behandelt?
5. Gibt es Race-Conditions bei gleichzeitigem Plugin-Start über mehrere Requests?
6. Ist das Plugin-State-Management (running/stopped/error) als State-Machine ausmodelliert?

**Output-Format:** Router-Decomposition-Vorschlag mit 3–4 Sub-Routern, Refactoring-Roadmap

---

### A8 – `ota.py` (API): OTA Update Flow
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (192 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/api/v1/ota.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | S6 |

**Analysefragen:**
1. Wie wird der OTA-Fortschritt dem Client kommuniziert (WebSocket, Polling, SSE)?
2. Gibt es Rollback-Mechanismus bei fehlgeschlagenem Update?
3. Werden Update-Bundles vor Ausführung kryptografisch verifiziert?
4. Ist der Update-Prozess idempotent (mehrfacher Aufruf sicher)?
5. Gibt es Timeout-Handling für lang laufende Update-Prozesse?

---

### A9 – `sso.py`: SSO/OAuth2-Integration (God-Router)
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | XL (491 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/api/v1/sso.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B7 |

**Ziel:** Prioritär! 491 Zeilen für SSO ist zu groß – wahrscheinlich mehrere OAuth-Provider in einem File.

**Analysefragen:**
1. Welche OAuth2/OIDC-Provider werden unterstützt? Sind sie durch eine Abstraktion entkoppelt?
2. Wird der OAuth2-State-Parameter korrekt validiert (CSRF-Schutz)?
3. Werden Access-/Refresh-Tokens sicher gespeichert (nicht im localStorage)?
4. Gibt es Token-Introspection oder JWK-Set-Validierung?
5. Wie wird User-Mapping (SSO-Identity → lokaler User) gehandhabt?
6. Gibt es ein klares Provider-Interface das neue SSO-Provider einfach integrierbar macht?

**Output-Format:** Security-Analyse, Provider-Abstraktion-Vorschlag, Splitting-Plan

---

## Phase 3: Services-Layer

### S1 – `services/__init__.py`: Webhook-Dispatcher (Falsche Platzierung)
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | M (228 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/services/__init__.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B3 |

**Ziel:** Kritisch! Business-Logik im `__init__.py` ist ein klares Anti-Pattern.

**Analysefragen:**
1. Warum ist der Webhook-Dispatcher in `__init__.py` statt `webhook_dispatcher.py`?
2. Hat `webhook_dispatcher.py` Inhalt oder ist es leer/ein Re-Export?
3. Gibt es andere Code-Dateien die fälschlicherweise via `__init__.py` importiert werden?
4. Ist die Retry-Logik testbar (injectable HTTP-Client)?
5. Gibt es eine Dead-Letter-Queue-Strategie (persistente Speicherung fehlgeschlagener Deliveries)?
6. Wird exponential Backoff mit Jitter implementiert?

**Output-Format:** Umbenennungsplan, Refactoring-Schritte ohne Test-Breakage

---

### S2 – `ingestion.py`: Datenpunkt-Ingestion
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | M (210 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/services/ingestion.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B3 |

**Analysefragen:**
1. Wird Bulk-Insert (z.B. `bulk_insert_mappings`) für Batches von Datenpunkten genutzt?
2. Gibt es Validierung/Sanitization vor der DB-Persistierung?
3. Wird nach Ingestion ein WebSocket-Broadcast getriggert? Ist das entkoppelt (async task)?
4. Gibt es Back-Pressure-Mechanismen wenn der Ingestion-Buffer voll läuft?
5. Werden doppelte Datenpunkte (gleicher Key + Timestamp) behandelt (Upsert)?
6. Gibt es Metriken zur Ingestion-Rate und Latency?

---

### S3 – `log_service.py`: Log-Service (Thin Layer?)
| Feld | Wert |
|------|------|
| **Priorität** | P3 |
| **Token-Größe** | S (29 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/services/log_service.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B3 |

**Analysefragen:**
1. Ist der Service zu dünn (nur DB-Wrapper ohne Business-Logik)?
2. Sollte Log-Logik direkt im Router oder im Repository liegen?
3. Gibt es strukturiertes Logging (structlog/loguru)?
4. Werden Log-Levels korrekt eingesetzt?

---

### S4 – `rule_evaluator.py`: Regel-Engine
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (151 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/services/rule_evaluator.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | A6 |

**Analysefragen:**
1. Wie werden Bedingungen evaluiert? Gibt es AST-basiertes Parsing oder `eval()`?
2. Ist die Regel-Engine austauschbar (Interface-Abstraktion oder konkrete Klasse)?
3. Wie wird mit fehlerhaften Regel-Ausdrücken umgegangen (Exception-Handling)?
4. Werden Regel-Evaluierungen gecacht (gleiche Eingabe → gecachtes Ergebnis)?
5. Ist die Engine gegen Code-Injection abgesichert (falls eval/exec genutzt)?
6. Gibt es Unit-Tests für Edge-Cases (leere Eingabe, NaN, Overflow)?

---

### S5 – `plugin_service.py` + `wheel_validator.py`: Plugin-Lifecycle
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (77 + 91 = 168 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/services/plugin_service.py`, `backend/src/webmacs_backend/services/wheel_validator.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | A7 |

**Analysefragen:**
1. Werden `.whl`-Dateien vor Installation auf Herkunft/Signatur geprüft?
2. Gibt es Sandboxing für Plugin-Code (separater Prozess, virtualenv)?
3. Wird Dependency-Konflikt-Detection beim Plugin-Install durchgeführt?
4. Ist das Plugin-Interface (was muss ein Plugin implementieren) klar dokumentiert?
5. Gibt es Versionierungs-Checking (Plugin-API-Version vs. Backend-Version)?

---

### S6 – `ota_service.py` + `updater.py`: OTA-Update-Prozess
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | L (315 + 326 = 641 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/services/ota_service.py`, `backend/src/webmacs_backend/services/updater.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | A8 |

**Analysefragen:**
1. Ist die Verantwortungsaufteilung zwischen `ota_service.py` und `updater.py` klar?
2. Gibt es State-Persistence bei Update-Unterbrechung (Resume-Fähigkeit)?
3. Wird der Update-Status in der DB persistiert (für Statusabfragen)?
4. Wie groß sind die Update-Bundles? Gibt es Streaming/Chunking für den Download?
5. Werden System-Ressourcen (Disk-Space) vor Update geprüft?
6. Ist der Updater testbar ohne echte Hardware?

---

## Phase 4: WebSocket & Middleware

### W1 – `ws/connection_manager.py` + `ws/endpoints.py`: WebSocket-Layer
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (80 + 219 = 299 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/ws/connection_manager.py`, `backend/src/webmacs_backend/ws/endpoints.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B7 |

**Analysefragen:**
1. Ist der ConnectionManager thread-safe (async-safe) bei gleichzeitigen Connects/Disconnects?
2. Gibt es reconnect-Logik und Heartbeat/Ping-Pong?
3. Werden WebSocket-Verbindungen authentifiziert (Token im Query-Param oder über Handshake)?
4. Gibt es Room/Channel-Konzept (Subscriber nur für relevante Datenpunkte)?
5. Wie skaliert der Connection-Manager über mehrere Prozesse/Instanzen (Redis-PubSub?)?
6. Werden Slow-Consumer-Probleme behandelt (Buffer-Overflows)?

---

### W2 – `middleware/rate_limit.py` + `middleware/request_id.py`: Middleware
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (183 + 41 = 224 Zeilen) |
| **Datei(en)** | `backend/src/webmacs_backend/middleware/rate_limit.py`, `backend/src/webmacs_backend/middleware/request_id.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B4 |

**Analysefragen:**
1. Basiert Rate-Limiting auf IP, User oder API-Key? Ist es konfigurierbar?
2. Wird Redis oder In-Memory für Rate-Limit-State genutzt? (In-Memory = nicht multi-process-fähig)
3. Werden Rate-Limit-Headers in der Response gesetzt (`X-RateLimit-Remaining`)?
4. Wird die Request-ID propagiert in Logs und Downstream-Calls?
5. Ist die Middleware-Reihenfolge (rate-limit vor auth oder danach) korrekt?

---

## Phase 5: Controller (Hardware-Abstraction)

### C1 – `controller/app.py`: Controller-Orchestrator
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (247 Zeilen) |
| **Datei(en)** | `controller/src/webmacs_controller/app.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | – |

**Analysefragen:**
1. Ist `app.py` ein God-Object? Wie viele Verantwortlichkeiten hat er (Init, Loop, Error-Recovery, Plugin-Mgmt)?
2. Gibt es eine klare Main-Loop-Struktur (Task-Group, Event-Loop)?
3. Wie wird Graceful-Shutdown implementiert (SIGTERM-Handling)?
4. Werden Hardware-Fehler von Logik-Fehlern unterschieden (unterschiedliche Recovery-Strategien)?
5. Gibt es Circuit-Breaker für Backend-API-Calls?

---

### C2 – `controller/services/plugin_bridge.py`: Plugin-Bridge (Größte Datei)
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | L (361 Zeilen) |
| **Datei(en)** | `controller/src/webmacs_controller/services/plugin_bridge.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | C1 |

**Ziel:** Mit 361 Zeilen die größte Controller-Datei – potenzielle God-Class.

**Analysefragen:**
1. Wie viele Verantwortlichkeiten hat die Bridge (Plugin-Lifecycle, Datentransfer, Config-Mgmt)?
2. Ist das Plugin-Interface klar (abstrakte Basisklasse oder Protocol)?
3. Werden Plugin-Crashes isoliert behandelt (kein Crash des gesamten Controllers)?
4. Gibt es Timeout-Handling für Plugin-Calls?
5. Wie werden Plugin-Configs hot-reloaded ohne Controller-Neustart?
6. Wird das Observer/Callback-Pattern für Plugin-Events genutzt?

**Output-Format:** Splitting-Vorschlag (z.B. `plugin_loader.py`, `plugin_runner.py`, `plugin_config.py`)

---

### C3 – `controller/services/api_client.py`: Backend API Client
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (201 Zeilen) |
| **Datei(en)** | `controller/src/webmacs_controller/services/api_client.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | C1 |

**Analysefragen:**
1. Wird `httpx.AsyncClient` mit Connection-Pooling und Timeout konfiguriert?
2. Gibt es Retry-Logik mit Exponential-Backoff für transiente Fehler?
3. Ist der Client testbar (injectable base-url, mockable transport)?
4. Werden Auth-Token automatisch refreshed wenn sie ablaufen?
5. Gibt es Type-Safe Response-Parsing (Pydantic-Models der Backend-Schemas)?

---

### C4 – `rule_engine.py` + `hardware.py` + `telemetry.py`: Kern-Services
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (128 + 121 + 119 = 368 Zeilen) |
| **Datei(en)** | `controller/src/webmacs_controller/services/rule_engine.py`, `controller/src/webmacs_controller/services/hardware.py`, `controller/src/webmacs_controller/services/telemetry.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | C1 |

**Analysefragen (rule_engine):**
1. Gibt es Code-Duplikation zwischen Controller `rule_engine.py` und Backend `rule_evaluator.py`?
2. Welche Regel-Evaluation findet auf Controller-Seite statt vs. Backend-Seite?

**Analysefragen (hardware):**
1. Ist die Hardware-Abstraktion über ein Interface definiert (austauschbar für Tests)?
2. Gibt es Mock-Implementierungen für CI/CD ohne echte Hardware?

**Analysefragen (telemetry):**
1. Welche Metriken werden gesammelt? Gibt es OpenTelemetry/Prometheus-Integration?
2. Werden Telemetrie-Daten gepuffert wenn die Backend-Connection nicht verfügbar ist?

---

## Phase 6: Frontend – Stores & Composables

### F1 – `stores/dashboards.ts` + `stores/logs.ts`: Pinia-Stores
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (129 + 130 = 259 Zeilen) |
| **Datei(en)** | `frontend/src/stores/dashboards.ts`, `frontend/src/stores/logs.ts` |
| **Status** | ⬜ |
| **Abhängigkeiten** | F3 |

**Analysefragen:**
1. Gibt es Boilerplate-Duplikation zwischen Stores (Loading-State, Error-Handling)?
2. Wird `useCrudStore` composable konsequent für CRUD-Stores genutzt?
3. Sind Stores typsicher (keine `any`-Typen)?
4. Gibt es Store-übergreifende Actions die Coupling erzeugen?
5. Werden reactive refs korrekt verwendet (kein unnötiges `.value`-Unwrapping)?

---

### F2 – `stores/plugins.ts` + `stores/ota.ts`: Komplexe Stores
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (149 + 73 = 222 Zeilen) |
| **Datei(en)** | `frontend/src/stores/plugins.ts`, `frontend/src/stores/ota.ts` |
| **Status** | ⬜ |
| **Abhängigkeiten** | F3 |

**Analysefragen:**
1. Wie wird Plugin-Status-Polling implementiert? Gibt es Race-Conditions?
2. Werden OTA-Updates über WebSocket oder Polling verfolgt?
3. Gibt es optimistische Updates (UI zeigt Änderung bevor API-Antwort)?
4. Werden Stores nach Logout/Re-Login korrekt zurückgesetzt?

---

### F3 – `composables/useCrudStore.ts`: Generisches CRUD-Pattern
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | M (179 Zeilen) |
| **Datei(en)** | `frontend/src/composables/useCrudStore.ts` |
| **Status** | ⬜ |
| **Abhängigkeiten** | – |

**Ziel:** Dieses Composable ist ein zentrales Abstraktionsmuster – Qualität hier beeinflusst alle Stores.

**Analysefragen:**
1. Ist das Composable vollständig generisch (TypeScript Generics korrekt)?
2. Gibt es Error-State-Management (API-Fehler werden sauber exponiert)?
3. Wird Pagination-State verwaltet?
4. Ist das Composable testbar (Mocking der API-Calls)?
5. Gibt es Optimistic-Update-Unterstützung?
6. Werden Loading-States granular verwaltet (per-operation)?

**Output-Format:** TypeScript-Interface-Analyse, Verbesserungsvorschläge mit konkreten Type-Definitionen

---

### F4 – `composables/useRealtimeDatapoints.ts` + `composables/usePolling.ts`: Realtime-Pattern
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (188 + 32 = 220 Zeilen) |
| **Datei(en)** | `frontend/src/composables/useRealtimeDatapoints.ts`, `frontend/src/composables/usePolling.ts` |
| **Status** | ⬜ |
| **Abhängigkeiten** | X2 |

**Analysefragen:**
1. Wie wird zwischen WebSocket-Realtime und Polling entschieden?
2. Wird bei WebSocket-Disconnect auf Polling-Fallback gewechselt?
3. Gibt es Memory-Leaks durch nicht gecleante Event-Listener in `onUnmounted`?
4. Wird das Polling-Intervall adaptiv angepasst (Exponential Backoff bei Fehlern)?
5. Gibt es Data-Deduplication (gleicher Datenpunkt zweimal empfangen)?

---

### F5 – `stores/auth.ts` + `composables/useAuditLog.ts`: Auth-State & Audit
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | S (62 + 36 = 98 Zeilen) |
| **Datei(en)** | `frontend/src/stores/auth.ts`, `frontend/src/composables/useAuditLog.ts` |
| **Status** | ⬜ |
| **Abhängigkeiten** | – |

**Analysefragen:**
1. Wird das Auth-Token sicher gespeichert (Memory > localStorage)?
2. Gibt es Token-Refresh-Logik im Frontend?
3. Wird bei 401-Responses automatisch logout getriggert?
4. Werden RBAC-Rollen im Frontend-State gecacht? Wie wird Stale-State verhindert?

---

## Phase 7: Frontend – Views (God-Component-Analyse)

> Views über 400 Zeilen sind Kandidaten für God-Components und sollten in kleinere Komponenten zerlegt werden.

### V1 – `DatapointsView.vue`: Größte View-Komponente
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | XL (811 Zeilen) |
| **Datei(en)** | `frontend/src/views/DatapointsView.vue` |
| **Status** | ⬜ |
| **Abhängigkeiten** | F4 |

**Ziel:** 811 Zeilen ist eindeutig eine God-Component – Decomposition dringend nötig.

**Analysefragen:**
1. Wie viele verschiedene UI-Bereiche gibt es (Table, Filter, Charts, Detail-Panel)?
2. Welche Teile haben eigenständige Logik die in eigene Composables gehören?
3. Gibt es gemischte Concerns (Datenbeschaffung + Rendering + State in einer Komponente)?
4. Werden Template-Abschnitte über 100 Zeilen über `v-if`/`v-for` strukturiert?
5. Wie viele `ref()` / `computed()` / `watch()` hat die Komponente? (> 10 = Warnsignal)
6. Welche 3–5 Unter-Komponenten könnten extrahiert werden?

**Output-Format:** Komponenten-Decomposition-Plan mit klaren Schnittstellen (Props/Emits)

---

### V2 – `DashboardCustomView.vue` + `DashboardView.vue`: Dashboard-Views
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | XL (810 + 702 = 1512 Zeilen) |
| **Datei(en)** | `frontend/src/views/DashboardCustomView.vue`, `frontend/src/views/DashboardView.vue` |
| **Status** | ⬜ |
| **Abhängigkeiten** | F1 |

**Analysefragen:**
1. Gibt es Code-Duplikation zwischen `DashboardView` und `DashboardCustomView`?
2. Könnte ein gemeinsames `useDashboard`-Composable extrahiert werden?
3. Werden Widget-Typen polymorph gehandhabt (je nach Typ verschiedene Komponente) oder via if/else?
4. Gibt es drag-and-drop für Widget-Positioning? Welches Library?
5. Werden React-ive Updates bei neuen Datenpunkten effizient gehandhabt (kein komplettes Re-Render)?

---

### V3 – `OtaView.vue`: OTA Update UI
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | L (541 Zeilen) |
| **Datei(en)** | `frontend/src/views/OtaView.vue` |
| **Status** | ⬜ |
| **Abhängigkeiten** | F2 |

**Analysefragen:**
1. Wie wird Update-Progress angezeigt (Echtzeit oder Polling)?
2. Gibt es einen klaren Wizard-Flow (Check → Download → Verify → Install → Reboot)?
3. Können UI-Schritte als eigenständige Step-Komponenten extrahiert werden?
4. Gibt es angemessenes Error-Handling mit Recovery-Optionen?

---

### V4 – `PluginsView.vue` + `PluginDetailView.vue`: Plugin-UI
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | L (441 + 421 = 862 Zeilen) |
| **Datei(en)** | `frontend/src/views/PluginsView.vue`, `frontend/src/views/PluginDetailView.vue` |
| **Status** | ⬜ |
| **Abhängigkeiten** | F2 |

**Analysefragen:**
1. Wie werden dynamische Plugin-Konfigurations-Formulare gerendert (JSON-Schema-basiert?)?
2. Gibt es Formular-Validierung für Plugin-Config-Felder?
3. Werden Plugin-Logs in der Detail-View live angezeigt (WebSocket)?
4. Gibt es Shared-Logic zwischen `PluginsView` und `PluginDetailView` die dupliziert ist?

---

### V5 – `RulesView.vue`: Regel-Editor
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (379 Zeilen) |
| **Datei(en)** | `frontend/src/views/RulesView.vue` |
| **Status** | ⬜ |
| **Abhängigkeiten** | – |

**Analysefragen:**
1. Gibt es einen visuellen Regel-Builder oder nur Text-Eingabe?
2. Wie wird Regel-Syntax-Validierung im Frontend gehandhabt?
3. Gibt es einen Simulation/Dry-Run-Button?
4. Werden Regel-Dependenzen (Regel triggert andere Regel) visualisiert?

---

## Phase 8: Frontend – Types & Services

### X1 – `types/index.ts`: TypeScript Type-Definitionen
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | M (306 Zeilen) |
| **Datei(en)** | `frontend/src/types/index.ts` |
| **Status** | ⬜ |
| **Abhängigkeiten** | B2 |

**Analysefragen:**
1. Sind alle Types mit den Backend-Pydantic-Schemas synchronisiert?
2. Gibt es `any`-Typen die durch präzise Types ersetzt werden sollten?
3. Könnte `openapi-typescript` oder `@hey-api/openapi-ts` zur Auto-Generierung genutzt werden?
4. Werden Utility-Types (`Partial<>`, `Pick<>`, `Omit<>`) wo sinnvoll eingesetzt?
5. Gibt es duplizierte Type-Definitionen (gleiche Struktur mehrfach definiert)?
6. Sind Discriminated Unions für Polymorphismus (z.B. Widget-Types) korrekt modelliert?

**Output-Format:** Type-Gap-Analyse, Empfehlung für Code-Generierung aus OpenAPI-Spec

---

### X2 – `services/api.ts` + `services/websocket.ts`: Frontend Service-Layer
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | S (39 + 150 = 189 Zeilen) |
| **Datei(en)** | `frontend/src/services/api.ts`, `frontend/src/services/websocket.ts` |
| **Status** | ⬜ |
| **Abhängigkeiten** | X1 |

**Analysefragen:**
1. Ist `api.ts` typsicher (generische Response-Types) oder nutzt es `any`?
2. Werden HTTP-Fehler zentral abgefangen und normalisiert?
3. Wird der Auth-Token automatisch als Bearer-Header injiziert?
4. Gibt es Request-Interceptors für Token-Refresh?
5. Ist der WebSocket-Service zustandsbehaftet? Kann er reconnecten?
6. Werden WebSocket-Nachrichten typsicher geparst (zod oder type-guards)?

---

## Phase 9: Plugin-System (Erweiterbarkeit)

### P1 – Plugin-Interface & Core-Plugin: Erweiterbarkeitsanalyse
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | M (plugins/core/ + plugins/simulated/) |
| **Datei(en)** | `plugins/core/`, `plugins/simulated/` |
| **Status** | ⬜ |
| **Abhängigkeiten** | S5, C2 |

**Analysefragen:**
1. Gibt es ein klar definiertes Plugin-Interface (abstrakte Klasse, Protocol, oder nur Konvention)?
2. Welche Methoden/Properties muss ein Plugin implementieren (Lifecycle: `setup`, `poll`, `teardown`)?
3. Ist das `simulated`-Plugin ein sauberes Beispiel für Plugin-Entwicklung?
4. Gibt es Plugin-Metadaten (Name, Version, Author, Dependencies)?
5. Kann ein Plugin konfigurierbare Parameter deklarieren (Config-Schema)?
6. Gibt es klare Dokumentation für Third-Party-Plugin-Entwickler?

**Output-Format:** Plugin-Interface-Dokumentation, Beispiel-Plugin-Template

---

### P2 – `plugins/revpi/` + `plugins/system/`: Hardware-Plugin-Implementierungen
| Feld | Wert |
|------|------|
| **Priorität** | P3 |
| **Token-Größe** | M |
| **Datei(en)** | `plugins/revpi/`, `plugins/system/` |
| **Status** | ⬜ |
| **Abhängigkeiten** | P1 |

**Analysefragen:**
1. Sind alle Implementierungen konsistent mit dem Plugin-Interface in `core/`?
2. Gibt es Hardware-spezifischen Code der schwer testbar ist (kein Abstraktions-Layer)?
3. Wie werden Hardware-Fehler (Verbindungsabbruch, Timeout) behandelt?

---

## Phase 10: Tests & Testqualität

### T1 – `conftest.py`: Test-Infrastruktur
| Feld | Wert |
|------|------|
| **Priorität** | P1 |
| **Token-Größe** | M (320 Zeilen) |
| **Datei(en)** | `backend/tests/conftest.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | – |

**Analysefragen:**
1. Gibt es Factory-Fixtures für alle wichtigen Entities?
2. Werden Tests isoliert (separate DB-Transaktionen pro Test)?
3. Gibt es Test-User für verschiedene Rollen (Admin, Viewer, etc.)?
4. Werden externe Services (HTTP, WebSocket) gemockt?
5. Wird `pytest-asyncio` korrekt konfiguriert (`asyncio_mode = "auto"`)?
6. Gibt es übermäßig komplexe Fixtures die selbst getestet werden müssten?

---

### T2 – `test_sso.py`: Größte Test-Datei
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | XL (704 Zeilen) |
| **Datei(en)** | `backend/tests/test_sso.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | T1, A9 |

**Analysefragen:**
1. Warum ist diese Testdatei so groß (704 Zeilen)? Gibt es zu viel Boilerplate?
2. Werden alle OAuth2-Flows getestet (Authorization Code, PKCE, Implicit)?
3. Werden Negative-Tests (ungültige State, abgelaufene Codes) abgedeckt?
4. Gibt es Code-Duplikation zwischen SSO-Tests?
5. Sind Test-Helper/Fixtures ausreichend ausgelagert?

---

### T3 – `test_integration.py` + `test_new_features.py`: Höherwertige Tests
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | L (373 + 423 = 796 Zeilen) |
| **Datei(en)** | `backend/tests/test_integration.py`, `backend/tests/test_new_features.py` |
| **Status** | ⬜ |
| **Abhängigkeiten** | T1 |

**Analysefragen:**
1. Testen Integrationstests echte Service-zu-Service-Interaktionen oder nur einzelne Endpoints?
2. Was testet `test_new_features.py`? Deutet der Name auf temporäre Tests hin?
3. Gibt es Tests für die WebSocket-Kommunikation?
4. Gibt es Performance-Tests oder nur Correctness-Tests?
5. Werden Edge-Cases (Datenbankfehler, externe-Service-Timeouts) getestet?

---

### T4 – Test-Coverage-Analyse: Gesamtübersicht
| Feld | Wert |
|------|------|
| **Priorität** | P2 |
| **Token-Größe** | S (nur Report-Analyse) |
| **Datei(en)** | Alle Tests + Coverage-Report |
| **Status** | ⬜ |
| **Abhängigkeiten** | T1, T2, T3 |

**Befehl:** `just qa` oder `pytest --cov=webmacs_backend --cov-report=term-missing`

**Analysefragen:**
1. Welche Module haben Coverage < 80%?
2. Gibt es kritische Pfade (Auth, Security) mit zu geringer Coverage?
3. Gibt es Tests die nichts testen (immer True-Assertions)?
4. Gibt es flaky Tests (manchmal pass, manchmal fail)?

---

## Übersichtsmatrix: Alle Tasks

| ID | Titel | Priorität | Tokens | Status | Abhängigkeiten | Qualitätsdimension |
|----|-------|-----------|--------|--------|----------------|-------------------|
| B1 | models.py – Monolith | P1 | L | ✅ | – | Wartbarkeit |
| B2 | schemas.py – Monolith | P1 | XL | ✅ | B1 | Wartbarkeit, DRY |
| B3 | repository + database | P1 | M | ✅ | B1 | Skalierbarkeit |
| B4 | config + dependencies | P2 | M | ✅ | – | Austauschbarkeit |
| B5 | enums.py | P3 | M | ✅ | – | Lesbarkeit |
| B6 | main.py | P2 | M | ✅ | – | Wartbarkeit |
| B7 | security.py | P1 | S | ✅ | B4 | Sicherheit |
| A1 | auth + tokens Router | P1 | M | ✅ | B7 | Sicherheit |
| A2 | users + health Router | P2 | S | ✅ | B3, B4 | Lesbarkeit |
| A3 | events + experiments Router | P2 | M | ✅ | B3 | Skalierbarkeit |
| A4 | datapoints + logging Router | P1 | M | ✅ | B3, S2 | Skalierbarkeit |
| A5 | dashboards Router | P2 | M | ✅ | B3 | Erweiterbarkeit |
| A6 | webhooks + rules Router | P2 | M | ✅ | S1, S4 | Erweiterbarkeit |
| A7 | plugins.py Router (God-Router) | P1 | XL | ✅ | S5 | Wartbarkeit |
| A8 | ota Router | P2 | M | ✅ | S6 | Verständlichkeit |
| A9 | sso.py Router (God-Router) | P1 | XL | ✅ | B7 | Sicherheit, Austauschbarkeit |
| S1 | services/__init__.py (falsch platziert) | P1 | M | ✅ | B3 | Lesbarkeit |
| S2 | ingestion.py | P1 | M | ✅ | B3 | Skalierbarkeit |
| S3 | log_service.py | P3 | S | ✅ | B3 | Wartbarkeit |
| S4 | rule_evaluator.py | P2 | M | ✅ | A6 | Sicherheit, Erweiterbarkeit |
| S5 | plugin_service + wheel_validator | P2 | M | ✅ | A7 | Sicherheit |
| S6 | ota_service + updater | P2 | L | ✅ | A8 | Wartbarkeit |
| W1 | ws/ connection + endpoints | P2 | M | ✅ | B7 | Skalierbarkeit |
| W2 | middleware/ rate_limit + request_id | P2 | M | ✅ | B4 | Skalierbarkeit |
| C1 | controller app.py | P2 | M | ✅ | – | Wartbarkeit |
| C2 | plugin_bridge.py (God-Class) | P1 | L | ✅ | C1 | Wartbarkeit |
| C3 | controller api_client.py | P2 | M | ✅ | C1 | Austauschbarkeit |
| C4 | rule_engine + hardware + telemetry | P2 | M | ✅ | C1 | Austauschbarkeit |
| F1 | stores dashboards + logs | P2 | M | ✅ | F3 | Lesbarkeit |
| F2 | stores plugins + ota | P2 | M | ✅ | F3 | Lesbarkeit |
| F3 | useCrudStore (Pattern-Kern) | P1 | M | ✅ | – | Erweiterbarkeit |
| F4 | useRealtimeDatapoints + usePolling | P2 | M | ✅ | X2 | Skalierbarkeit |
| F5 | auth store + useAuditLog | P2 | S | ✅ | – | Sicherheit |
| V1 | DatapointsView (God-Component) | P1 | XL | ✅ | F4 | Wartbarkeit |
| V2 | DashboardCustomView + DashboardView | P1 | XL | ✅ | F1 | Wartbarkeit |
| V3 | OtaView.vue | P2 | L | ✅ | F2 | Lesbarkeit |
| V4 | PluginsView + PluginDetailView | P2 | L | ✅ | F2 | Wartbarkeit |
| V5 | RulesView.vue | P2 | M | ✅ | – | Erweiterbarkeit |
| X1 | types/index.ts | P2 | M | ✅ | B2 | Verständlichkeit |
| X2 | services/api.ts + websocket.ts | P1 | S | ✅ | X1 | Austauschbarkeit |
| P1 | Plugin-Interface & Core | P1 | M | ✅ | S5, C2 | Erweiterbarkeit |
| P2 | revpi + system Plugins | P3 | M | ✅ | P1 | Austauschbarkeit |
| T1 | conftest.py – Test-Infrastruktur | P1 | M | ✅ | – | Verständlichkeit |
| T2 | test_sso.py – Riesentest-Datei | P2 | XL | ✅ | T1, A9 | Wartbarkeit |
| T3 | test_integration + test_new_features | P2 | L | ✅ | T1 | Verständlichkeit |
| T4 | Coverage-Analyse | P2 | S | ✅ | T1-T3 | Verständlichkeit |

---

## Empfohlene Bearbeitungsreihenfolge (Kritischer Pfad)

```
Woche 1 – Fundament (P1, keine Abhängigkeiten):
  B1 → B2 → B3 → B7 → S1 → T1

Woche 2 – API & Services (P1, aufbauend):
  A1 → A4 → A7 → A9 → S2 → F3 → X2

Woche 3 – God-Components & Controller (P1/P2):
  V1 → V2 → C2 → P1 → B4 → B6

Woche 4 – Restliche P2-Tasks (parallel möglich):
  [A3, A5, A6, S4, S5, W1, W2] parallel
  [F1, F2, F4, F5, C1, C3, C4] parallel

Woche 5 – Frontend Views & Types (P2):
  X1 → V3 → V4 → V5 → T2 → T3 → T4

Woche 6 – P3 Clean-up:
  B5 → S3 → P2 + Umsetzung der priorisierten Befunde
```

---

## Bekannte Hotspots (Sofortige Aufmerksamkeit)

| # | Hotspot | Problem | Empfehlung |
|---|---------|---------|------------|
| 1 | `services/__init__.py` | Business-Logic in `__init__.py` | Umbenennen zu `webhook_dispatcher.py` |
| 2 | `api/v1/plugins.py` (513 Z.) | God-Router | In 3–4 Sub-Router aufteilen |
| 3 | `api/v1/sso.py` (491 Z.) | God-Router | Provider-Abstraktion einführen |
| 4 | `DatapointsView.vue` (811 Z.) | God-Component | 5 Sub-Komponenten extrahieren |
| 5 | `DashboardCustomView.vue` (810 Z.) | God-Component | Widget-System als eigene Komponenten |
| 6 | `controller/services/plugin_bridge.py` (361 Z.) | God-Class | In 3 Klassen aufteilen |
| 7 | `schemas.py` (585 Z.) | Monolith | Domain-spezifische Schema-Module |
| 8 | `models.py` (412 Z.) | Fehlende Basis-Klasse | Timestamp-Mixin, Repr-Mixin |

---

## Output-Format für jede abgearbeitete Task

Jede analysierte Task soll folgendes Ergebnis liefern:

```markdown
## [Task-ID] – [Titel]

**Befunde:**
| # | Befund | Schwere | Zeile(n) | Empfehlung |
|---|--------|---------|----------|------------|
| 1 | ... | P1/P2/P3 | L.42-55 | ... |

**Konkrete Verbesserung (Code-Beispiel):**
```python
# Vorher
...

# Nachher  
...
```

**Risikoabschätzung für Umsetzung:**
- Tests betroffen: Ja/Nein
- Breaking Change: Ja/Nein
- Geschätzter Aufwand: S/M/L
```
