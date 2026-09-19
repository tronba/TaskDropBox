# TaskDropBox — Software Design Document

**Status:** Revised V1 implementation specification  
**License:** GNU Affero General Public License v3.0 or later (`AGPL-3.0-or-later`)  
**Platform:** Ubuntu Server 26.04 LTS (current point release preferred)  
**Deployment:** Standalone school LAN, static IP, no runtime Internet dependency  
**Stack:** Python, Django, SQLite, Gunicorn, Nginx, server-rendered HTML, minimal JavaScript

## 1. Purpose

TaskDropBox is a self-hosted application for distributing temporary school assignments and collecting student submissions during an Internet outage or continuity event.

It is installed and tested before an outage, then runs entirely on an isolated local network. It requires no DNS, certificate infrastructure, cloud service, external authentication, email, CDN, telemetry, or Internet connection at runtime.

There are no teacher or student accounts. A teacher uses one installation-level six-digit creator PIN. Each task receives two independent, unguessable links/keys: one for students and one for teacher administration. Students manually enter their name and submit plain text and/or files. Teachers review submissions, identify late work, export everything, close or reopen the task, and delete it.

## 2. Confirmed scope

### Version 1

- Product and repository name: **TaskDropBox** / `taskdropbox`.
- `AGPL-3.0-or-later` license.
- Ubuntu Server 26.04 LTS production target.
- Plain HTTP at a static private IP such as `http://10.20.0.10`.
- No DNS, mDNS, certificates, or other infrastructure required.
- One front page provides entry points for creating, opening, and managing tasks.
- Task creation requires a system-wide six-digit PIN configured during installation.
- Desktop and Chromebook browsers are the primary clients.
- English-only interface with all source strings translation-ready.
- Plain-text task instructions and student web answers.
- No saved drafts or autosave.
- Optional soft deadline; open tasks accept late work and mark it late.
- Separate close/reopen control; closed tasks reject submissions.
- Individual downloads and ZIP export.
- Manual retention and deletion only.
- Low disk space rejects new writes and never automatically deletes content.
- No QR codes.

### Version 2 candidates

- sanitized rich-text instructions and answers;
- saved drafts, return links, manual save, autosave, conflict handling, and link rotation;
- additional gettext translation files and a language selector;
- an optional open-task directory where teachers may explicitly list selected tasks;
- optional automatic retention and abandoned-draft cleanup;
- advanced low-disk policy;
- task cloning;
- a packaged installation route for machines that are already offline.

#### Optional open-task directory

V2 may add a subpage such as `/tasks/` for discovering currently open tasks. Listing is opt-in per task and disabled by default.

- A teacher can list or unlist a task through that task's secret administration page.
- Only tasks that are both open and explicitly listed appear.
- Closing, deleting, or unlisting a task removes it from the directory immediately.
- Passing the due date does not remove an otherwise open task; it is shown as overdue and indicates that submissions will be marked late.
- The directory may show only the task title, due date/status, and a link to its student page.
- It never shows teacher identity, student names, submission counts, filenames, answers, or administration links.
- Listing a task deliberately makes its student page discoverable to everyone on the local network. The interface must explain this before the teacher enables listing.
- Listed tasks should use a separate non-secret public identifier or slug rather than exposing or repurposing the secret administration token.
- Unlisted tasks remain accessible only through their existing student link/key.

### Version 3 and later candidates

- offline dictionaries and local writing assistance;
- QR codes and optional phone-focused conveniences;
- offline antivirus scanning;
- replacement of a submission before the deadline;
- download-rate controls;
- PostgreSQL for substantially larger installations.

Future features must not introduce permanent user accounts or required Internet services.

## 3. Permanent boundaries

- No permanent teacher or student accounts, profiles, passwords, class lists, enrolment, grades, messaging, or cross-task student history.
- A submitted name is self-reported metadata for one submission and is not identity verification.
- No cloud storage, external authentication, email, analytics, advertising, CDN, remote font, update check, or online editor dependency.
- TaskDropBox is not a public SaaS, LMS, office suite, or real-time collaboration tool.
- Creator access uses one shared installation PIN. Task administration uses a task-specific capability link/key.
- Student pages never expose submission counts, names, filenames, or other students' work.
- Uploaded files are private and served only after authorization.
- Normal operation remains functional with WAN access physically disconnected.

## 4. Privacy and deletion

TaskDropBox V1 collects only task content, task attachments, a student-entered display name, submitted plain text, uploaded files and their original names, random operational identifiers, and timestamps.

It does not collect student numbers, email addresses, class membership, analytics identifiers, source IP addresses in application records, or full user-agent strings by default.

Deleting a submission removes its name, answer, metadata, and files. Deleting a task removes the complete live task: instructions, task attachments, submissions, names, answers, and uploaded files.

Deletion cannot retroactively remove teacher-downloaded ZIP files, external copies, or older backups. Ordinary deletion also cannot promise forensic erasure of physical SSD blocks. Deployment documentation must therefore cover encrypted VM storage, restricted backups, backup expiry, SQLite secure deletion, and WAL checkpointing without describing them as guaranteed physical-media erasure.

## 5. Trust model

**Operator:** installs, configures, updates, backs up, restores, starts, and stops the VM; fully trusted.  
**Teacher:** knows the creator PIN and holds task-specific admin links/keys.  
**Student:** holds a delivery link and can view that task and submit, but cannot view submissions.

The isolated LAN is operationally trusted but may contain curious students. Plain HTTP is a deliberate rapid-deployment tradeoff: a person able to intercept or alter LAN traffic may steal links or content. Risk is reduced with a temporary isolated SSID, WPA2/WPA3, a strong temporary Wi-Fi password, no Internet bridge, and shutdown after use.

## 6. User journeys

### Create

1. Teacher opens the TaskDropBox front page and selects **Create a task**.
2. Teacher enters the shared six-digit creator PIN if no valid creator session exists.
3. Teacher supplies title, plain-text instructions, optional due date/time, optional task attachments, and allowed answer modes.
4. At least one of text or files must be enabled.
5. Server creates the task and shows a short-lived receipt with independent student and admin URLs, copy/print controls, and a warning that the admin URL cannot be recovered through the normal UI.
6. Teacher distributes only the student URL.

### Submit

1. Student opens `/d/<student-token>/`.
2. Page shows title, instructions, due date, status, task attachments, limits, and submission form.
3. Student enters a name and supplies text and/or files.
4. Student confirms submission.
5. Server rechecks task state, validates, persists atomically, calculates late state from server time, and redirects to a receipt.

V1 has no saved draft. The form must warn that unsent work is not stored and may be lost if the page closes.

### Review and export

1. Teacher opens `/a/<admin-token>/`.
2. Server exchanges the token for a task-scoped session and redirects to `/manage/<task-id>/`.
3. Teacher sees a newest-first paginated list with student name, timestamp, on-time/late status, text, filenames, sizes, and download actions.
4. Teacher downloads individual files or one ZIP containing all submissions.

### Close, reopen, and delete

- Closing immediately blocks new submissions while preserving existing work.
- Reopening permits submissions. If overdue, new submissions are marked late.
- Deleting a submission or task requires an explicit confirmation page.
- Successful deletion removes the corresponding live database rows and files.

## 7. Functional requirements

### Creator access

- The creator credential is exactly six decimal digits, including possible leading zeroes.
- Store only a Django password hash in a root-readable configuration file; Argon2 is preferred.
- Creator sessions default to eight hours.
- Failed PIN attempts return a generic error and are rate-limited per client and across the installation.
- Never commit or log a plaintext PIN.
- Changing the PIN invalidates existing creator sessions.
- The PIN authorizes task creation only. It never grants access to task administration or submissions.

### Task

- title: required, 1–200 characters;
- instructions: required normalized plain text, maximum 20,000 characters;
- due time: optional, stored in UTC and displayed in school timezone;
- attachments: optional and limited by count and size;
- answer modes: text, files, or both;
- state: `open` or `closed`.

### Submission

- student name: required, trimmed, maximum 150 characters;
- at least one permitted answer type must be present;
- duplicate names are allowed and remain unrelated;
- every submission has a long random receipt ID;
- authoritative submission time comes from the server;
- `is_late` is recorded when accepted and equals `due_at is not null and submitted_at > due_at`;
- an overdue open task accepts work;
- a closed task shows its content but rejects submission POSTs;
- a submission is not visible until records and files are consistently persisted;
- submissions are immutable through student pages.

### Teacher administration

- view task and status;
- copy/save the student URL on the one-time creation receipt; because only its hash is stored, the administration page cannot recover a lost student URL in V1;
- view/paginate submissions and late state;
- download individual files;
- export all submissions as ZIP;
- close and reopen;
- delete one submission;
- delete the task.

Task editing, grading, accounts, and an operator web dashboard are outside V1.

## 8. Architecture

| Component | Choice | Responsibility |
|---|---|---|
| Web application | pinned supported Django | routes, forms, templates, authorization, data |
| Application server | Gunicorn | run Django |
| Reverse proxy | Nginx | HTTP, limits, rate control, timeouts, static assets |
| Database | SQLite in WAL mode | metadata and transactions |
| File storage | local private filesystem | attachments and submissions |
| Front end | Django templates, local CSS, minimal JS | accessible offline UI |

```text
Browser -> isolated LAN -> Nginx :80 -> Gunicorn/Django -> SQLite
                                                  `----> private files
```

No Node build, Redis, PostgreSQL, container runtime, JavaScript framework, or external runtime service is required. Private files are authorized by Django and may use Nginx `X-Accel-Redirect`; they are never a public media directory.

## 9. GitHub repository

```text
taskdropbox/
  README.md
  LICENSE
  CHANGELOG.md
  SECURITY.md
  CONTRIBUTING.md
  install.sh
  uninstall.sh
  pyproject.toml
  manage.py
  .env.example
  config/
  drops/
  static/
  locale/
  docs/
    installation.md
    standalone-network.md
    configuration.md
    backup-and-restore.md
    upgrading.md
    privacy.md
    troubleshooting.md
  deploy/
    nginx/taskdropbox.conf.template
    systemd/taskdropbox.service.template
  .github/workflows/tests.yml
```

The repository contains no runtime database, uploads, production secrets, raw capability links, production configuration, or certificates. `.gitignore` covers those items plus virtual environments, caches, logs, build output, and test artifacts.

`LICENSE` contains AGPL-3.0-or-later. CI runs tests, lint/format checks, migration consistency checks, and installation/configuration checks. Tagged release artifacts include SHA-256 checksums. Production installation must use a tagged release, not an unpinned script from the default branch.

## 10. Data model

Use UUID primary keys.

### Task

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `title` | varchar(200) |
| `instructions_text` | normalized plain text |
| `student_token_hash` | unique indexed SHA-256 digest |
| `admin_token_hash` | unique indexed SHA-256 digest |
| `status` | `open` or `closed` |
| `allow_text`, `allow_files` | at least one true |
| `created_at` | UTC |
| `due_at` | nullable UTC soft deadline |
| `closed_at` | nullable operational timestamp |

### TaskAttachment

UUID, task foreign key with cascade, normalized `original_name`, random `storage_name`, `size_bytes`, informational claimed content type, SHA-256 checksum, and UTC creation time.

### Submission

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `task_id` | cascade foreign key |
| `receipt_id` | long random unique indexed value |
| `student_name` | varchar(150), self-reported |
| `answer_text` | normalized plain text, possibly empty |
| `submitted_at` | authoritative UTC time |
| `is_late` | immutable classification recorded on acceptance |

### SubmissionFile

UUID, submission foreign key with cascade, normalized `original_name`, random `storage_name`, `size_bytes`, informational claimed content type, SHA-256 checksum, and UTC creation time.

## 11. Capability tokens and sessions

Generate tokens independently with Python `secrets`:

```python
student_token = secrets.token_urlsafe(16)  # about 128 bits
admin_token = secrets.token_urlsafe(32)    # about 256 bits
```

Store only `sha256(raw_token).hexdigest()`. Slow password hashing is for the human creator PIN; high-entropy tokens use indexed SHA-256 digests.

Admin-token exchange resolves the token, grants only that task UUID in an HTTP-only signed session, redirects to a clean management URL, and does not display or log the token again. Grants default to eight hours. A task A grant never authorizes task B.

Student tokens remain in URLs, so Nginx and Django logs must omit or redact capability-bearing paths.

## 12. Routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | front page with create, student-open, and teacher-manage entry points |
| GET, POST | `/create/login/` | creator session |
| GET, POST | `/create/` | create task |
| POST | `/open/` | accept a student link/key and redirect to its task |
| POST | `/manage/open/` | accept an admin link/key and perform the scoped-session exchange |
| GET | `/d/<student-token>/` | task and submission form |
| POST | `/d/<student-token>/submit/` | submit final work |
| GET | `/d/<student-token>/task-file/<id>/` | authorized task attachment |
| GET | `/receipt/<receipt-id>/` | minimal submission receipt |
| GET | `/a/<admin-token>/` | exchange admin token |
| GET | `/manage/<task-id>/` | review submissions |
| POST | `/manage/<task-id>/close/` | close |
| POST | `/manage/<task-id>/reopen/` | reopen |
| GET | `/manage/<task-id>/export.zip` | ZIP export |
| GET | `/manage/<task-id>/file/<id>/` | authorized submission file |
| GET, POST | `/manage/<task-id>/submission/<id>/delete/` | confirm/delete submission |
| GET, POST | `/manage/<task-id>/delete/` | confirm/delete task |
| GET | `/healthz` | lightweight health check |

All mutations and all front-page key-entry forms use POST and CSRF protection. Keys must not be placed in query strings. GET is side-effect free except deliberate admin-token exchange. Successful task creation renders a no-store one-time receipt directly from the POST response, so raw URLs are never stored in the database or session. A single-use hashed creation nonce prevents a browser retry from creating a duplicate task. Leaving the receipt loses normal access to its raw links.

The front-page entry forms accept either the complete TaskDropBox URL or its raw task-specific key. Input is normalized conservatively; a URL is accepted only when its origin and route match the configured TaskDropBox base URL. Invalid student and admin input receives a generic error without revealing whether a task exists.

The submission receipt may show task title, submitted name, server time, late/on-time status, and accepted filenames, but never answer content. Receipt IDs are unguessable.

## 13. Uploads and transactions

Recommended defaults: 10 task attachments, 10 files per submission, 25 MiB per file, 50 MiB total submission, 55 MiB request body, and 100,000 text characters.

- Never use an uploaded filename on disk.
- Generate random storage names and retain a normalized, length-limited display name as metadata.
- Never join filesystem paths from user input.
- Store files outside static directories on a non-executable tree.
- Force attachment download with safe `Content-Disposition` and `X-Content-Type-Options: nosniff`.
- Use `application/octet-stream` when uncertain.
- Compute SHA-256 while saving.
- Enforce file, count, aggregate, body, and disk-reserve limits.
- Remove partial temporary files after failure.
- Do not trust extensions or browser MIME claims.

V1 permits ordinary school file types without an allowlist; files are never executed or rendered inline.

Submission service flow: resolve task, validate fields and free space, stream to private temporary files, begin a short transaction, lock and recheck task state, calculate late state, create records, move files to final random paths, commit when consistent, and clean up on failure. A maintenance command reports missing and orphaned files.

## 14. ZIP export

ZIP export is required in V1 and must spool or stream rather than load all content into memory.

```text
Volcano-assignment_2026-09-19/
  manifest.csv
  submissions/
    0001_Anna-Hansen/
      Anna-Hansen - webgui.txt
      Anna-Hansen - attachment - diagram.pdf
    0002_Mohammed-Ali/
      Mohammed-Ali - webgui.txt
      Mohammed-Ali - attachment - answers.docx
```

- Web text becomes UTF-8 `<student name> - webgui.txt`.
- Uploads become `<student name> - attachment - <original filename>`.
- Sequence directories prevent identical student names from colliding.
- Duplicate filenames receive deterministic numeric suffixes.
- Strip separators/control characters, normalize unsafe characters, cap lengths, and reject `..` or absolute paths.
- Never pass an original name directly to an archive member path.
- `manifest.csv` includes sequence, submission UUID, receipt ID, name, timestamp, late state, answer filename, original/exported attachment names, size, and checksum.
- Neutralize CSV fields beginning with `=`, `+`, `-`, or `@`.
- Use stable ordering.

## 15. Security controls

- independent high-entropy capabilities;
- slow creator-PIN hashing;
- Nginx rate, connection, timeout, and body limits;
- CSRF on mutations;
- normal template escaping for plain text;
- private non-executable file storage;
- generic 404 for malformed, missing, deleted, or invalid capabilities;
- no directory listing or raw tokens in logs;
- `HttpOnly`, `SameSite=Lax` signed session cookies;
- pagination and free-space checks.

Suggested rate limits: 5 creator-PIN attempts/minute/IP plus an installation-wide limit, 10 task creations/hour/IP, 10 submissions/minute/IP with burst 5, 60 capability/404 requests/minute/IP, and a concurrent download limit. Values remain configurable.

Set a local-only CSP, `nosniff`, `Referrer-Policy: no-referrer`, `frame-ancestors 'none'`, restrictive `Permissions-Policy`, and `Cache-Control: no-store` on creator, capability, receipt, and admin pages.

HTTP cookies cannot be marked `Secure`. Documentation must state this plainly and never imply that an isolated LAN provides encrypted transport.

## 16. Interface and translation readiness

- Prioritize current desktop and Chromebook browsers while remaining usable at narrow widths.
- Support keyboard operation, visible focus, programmatic labels, linked error summaries, and server-rendered validation.
- Show limits, open/closed state, deadline, and overdue state clearly.
- Explain that overdue open tasks accept work and mark it late.
- Warn that V1 does not save unsent work.
- Never reveal submission metadata on student pages.
- Use local fonts, CSS, icons, and scripts only.
- Core workflows work with JavaScript disabled.

The front page is the single memorable entry point and contains three clearly separated sections:

1. **Create a task** — asks for the system-wide creator PIN and then opens the creation form.
2. **Open a task** — accepts a complete student link or student key.
3. **Manage a task** — accepts a complete secret teacher link or administration key.

The front page never lists existing V1 tasks. It explains that the creation PIN only permits task creation, while every task has its own separate administration secret.

V1 ships only English, but every UI string uses Django gettext from the start. Future translations live in `locale/<language>/LC_MESSAGES/django.po` and compiled `.mo` files. Do not show a language selector until another complete translation is bundled. Teacher and student content is never automatically translated.

## 17. Configuration

```text
TASKDROPBOX_SECRET_KEY=<random secret>
TASKDROPBOX_CREATOR_PIN_HASH=<Django password hash>
TASKDROPBOX_ALLOWED_HOSTS=10.20.0.10
TASKDROPBOX_BASE_URL=http://10.20.0.10
TASKDROPBOX_TIME_ZONE=Europe/Oslo
TASKDROPBOX_DATA_DIR=/var/lib/taskdropbox
TASKDROPBOX_MAX_TASK_ATTACHMENTS=10
TASKDROPBOX_MAX_FILE_MIB=25
TASKDROPBOX_MAX_SUBMISSION_MIB=50
TASKDROPBOX_MAX_FILES_PER_SUBMISSION=10
TASKDROPBOX_MIN_FREE_DISK_MIB=1024
TASKDROPBOX_CREATOR_SESSION_HOURS=8
TASKDROPBOX_ADMIN_SESSION_HOURS=8
TASKDROPBOX_LANGUAGE=en
```

Use a root-readable environment file and ship a secret-free `.env.example`. Validate IPs, paths, timezone, sizes, durations, and language.

The operator sets the final static IP before creating tasks. Existing tokens survive an IP change, but previously distributed URLs containing the old IP do not reach the server.

## 18. Standalone deployment

```text
Computers -> isolated Wi-Fi/LAN -> static private IP -> Ubuntu VM
                                                     -> Nginx HTTP :80
                                                     -> TaskDropBox
```

Only a reachable static IPv4 address is required. Browsers may label HTTP as not secure, but there is no invalid-certificate warning because no certificate is used. HTTPS with an operator-provided certificate may be added later; certificates and DNS are not V1 requirements.

The operator guide covers static IP assignment, client reachability, firewall, isolated SSID, Wi-Fi password, clock verification, link copying/printing, and shutdown.

Deadlines require an accurate server clock. Installer asks for timezone; `show_status` prominently prints server time. The operator verifies it before creating tasks and can correct it with a documented local command. Standalone configuration must not depend on public NTP; the hypervisor/RTC clock is used unless an approved local time source is configured.

After installation, application pages use no external assets and TaskDropBox performs no update, telemetry, spelling, translation, or API calls. Release acceptance tests the complete workflow with outbound access blocked.

## 19. Ubuntu installer

`install.sh` targets a fresh Ubuntu Server 26.04 LTS VM. The ordinary preparation process temporarily has Internet access for Ubuntu packages and a tagged GitHub release; runtime does not.

The root-run installer:

1. verifies Ubuntu `VERSION_ID=26.04` and shows planned changes;
2. runs `apt-get update` and applies available upgrades;
3. detects `/var/run/reboot-required`, stops safely, and instructs the operator to reboot and rerun;
4. never reboots unless an explicit flag requests it;
5. installs pinned prerequisites;
6. creates locked non-login user/group `taskdropbox`;
7. installs versioned code in `/opt/taskdropbox` and a Python venv with exact-version-pinned direct dependencies;
8. creates data in `/var/lib/taskdropbox` and protected root-owned configuration in `/etc/taskdropbox`;
9. prompts for static IP/base URL, timezone, six-digit creator PIN, limits, and disk reserve;
10. accepts the PIN twice without echo and stores only its hash;
11. generates the Django secret securely;
12. applies matching Nginx/Django request limits and configures a reserved-disk threshold;
13. runs migrations and static collection;
14. installs/enables Gunicorn and Nginx services;
15. leaves firewall policy to the operator so an installer cannot accidentally cut off remote administration, and documents the required TCP port;
16. runs configuration, permission, database, service, and HTTP health checks;
17. prints URL, server time, paths, backup warning, and next steps.

It is safely rerunnable, detects existing installations, enters an explicit upgrade/reconfigure path, backs up configuration, and never deletes application data during install or upgrade. Secrets use prompts, protected file descriptors, or root-readable files—not command-line arguments.

`uninstall.sh` removes services and code but preserves `/var/lib/taskdropbox`. Data removal requires separate confirmation naming the exact path.

## 20. Operational preparation

1. Install current Ubuntu Server 26.04 point release.
2. Run the TaskDropBox installer while repositories and GitHub are reachable.
3. Apply updates/reboot and rerun if required.
4. Disconnect or block WAN.
5. Run the full offline acceptance test.
6. Create a clean VM snapshot/template or encrypted appliance export.
7. Keep the tagged release and checksum.
8. Periodically update a maintenance copy, repeat offline testing, and refresh the standby image.

During an outage: start/import the prepared VM, attach the isolated LAN, verify static IP and clock, and open `http://<server-ip>/`.

## 21. Storage, backup, and maintenance

Use SQLite WAL, busy timeout, secure deletion where supported, short transactions, local reliable storage, and 2–4 initially tested Gunicorn workers. Store `/var/lib/taskdropbox/db.sqlite3` and `/var/lib/taskdropbox/files/` together. Below the disk reserve, return HTTP 503 for new writes while preserving reads/admin where possible. Never auto-delete in V1.

Back up the database and files together using SQLite online backup or a brief write stop. Backups require restricted access, encryption where practical, expiry, and restore tests.

Management commands:

- `check_storage` — missing/orphaned files and optional checksum verification;
- `set_creator_pin` — securely prompt twice, store a new PIN hash, and invalidate existing creator sessions;
- `backup_db` — consistent SQLite backup;
- `show_status` — version, health, base URL, detected IPs, time/timezone, free space, and counts without secrets/content;
- `delete_task` — emergency UUID deletion with preview/confirmation;
- `checkpoint_database` — documented WAL checkpoint/truncation.

## 22. Logging and errors

Log startup/configuration errors, task/submission UUID events, late classification without names, close/reopen/export/delete events, limits, and storage/database failures.

Never log raw tokens, creator PINs, names, answers, file contents, full original filenames at normal level, or capability-bearing request paths. Redact Nginx and Django logs and rotate them.

Errors: generic 404 for bad capabilities; 413 for size; 429 for rate; 503 for disk reserve; 409/403 for closed submission; generic unexpected-error page with correlation ID. An overdue open task is accepted, not errored. Failed uploads never produce a success receipt.

## 23. Testing and acceptance

Tests cover token independence, creator-PIN verification/change/session invalidation, global and per-client PIN rate limits, validation, escaping, deadlines and exact boundary, close/reopen, file/archive safety, limits, scoped admin sessions, front-page link/key parsing, CSV formula protection, and deletion failures.

Integration tests cover create → submit → review → export → delete; invalid capabilities; token exchange; cross-task denial; student isolation; authorized downloads; on-time and late submission; overdue-open acceptance; closed rejection; reopen-after-deadline; POST/Redirect/GET duplicate prevention; concurrency; deletion isolation; low-disk rejection; backup/restore; Nginx deployment by IP; clean Ubuntu 26.04 installation; and the full workflow with WAN blocked.

Security inputs include traversal, absolute paths, backslashes, HTML/script text, CSV prefixes, duplicates, Unicode, very long values, malformed multipart bodies, archive separators, and truncated tokens.

V1 is accepted when:

1. it installs on clean Ubuntu Server 26.04 and safely handles updates/reboots;
2. the full workflow works with WAN blocked and no DNS;
3. the front page exposes the three defined entry points, and only the current creator PIN authorizes creation;
4. student/admin tokens are independent, high entropy, hashed, and absent from routine logs;
5. a student submits name, text, and multiple files exactly once;
6. overdue open work is accepted and marked late; closed work is rejected;
7. students cannot access any submission;
8. teachers review, download, and safely export all content;
9. export names and manifest follow this specification without traversal, collisions, or CSV injection;
10. upload/rate/disk limits work;
11. HTML entered as plain text never executes;
12. submission/task deletion removes the correct live names, content, and files only;
13. backup restores successfully;
14. English strings are translation-ready;
15. desktop/Chromebook core workflows work without JavaScript;
16. no account, profile, or cross-task identity is created;
17. TaskDropBox makes no outbound application requests at runtime.

## 24. Implementation sequence

1. Scaffold repository, license, Django settings/templates, health endpoint, and tests.
2. Implement models, migrations, token utilities, and task creation service.
3. Implement creator authentication and short-lived link receipt.
4. Implement student plain-text/file submission and private storage.
5. Implement deadline classification and close/reopen.
6. Implement admin token exchange, scoped review, and authorized downloads.
7. Implement submission/task deletion.
8. Implement safe ZIP export and manifest.
9. Add production limits, disk checks, logging redaction, and security headers.
10. Add Ubuntu installer, upgrade/reconfigure path, and preserving-data uninstaller.
11. Add networking, clock, backup/restore, privacy, and troubleshooting docs.
12. Complete accessibility, security, concurrency, offline, and clean-VM tests.

Each stage leaves tests passing. Authorization, file consistency, deletion, and export safety precede convenience styling.

## 25. Invariants

An implementation agent must not silently change: the product name or license; accountless model; three-part front page; system-wide six-digit creator PIN; self-reported per-submission name; independent hashed capabilities; V1 plain text and no drafts; soft deadline plus separate closing; V1 ZIP export; manual retention and reject-only disk behavior; complete live deletion; English-only translation-ready interface; no V1 QR; desktop/Chromebook priority; Ubuntu 26.04; static-IP HTTP without DNS/certificates; offline runtime; or SQLite/private local files.

## 26. Handoff prompt

> Implement TaskDropBox V1 from this document as a GitHub-ready AGPL-3.0-or-later project. Target Ubuntu Server 26.04 and standalone HTTP at a static private IP without DNS, certificates, cloud services, or runtime Internet. Use Django, SQLite, Gunicorn, Nginx, server-rendered templates, and minimal optional JavaScript. Do not create accounts. The front page provides Create, Open, and Manage entry points. Task creation requires a rate-limited system-wide six-digit PIN whose hash is configured at installation and safely replaceable later; changing it invalidates creator sessions. Student and admin access use separate independent hashed capability keys. V1 has plain-text instructions/answers and no drafts. A due date is soft: open tasks accept work and record late state; closing is the hard stop. Implement private file storage, individual downloads, safe ZIP export with UTF-8 web-answer files, original uploaded documents, readable collision-safe names, and CSV manifest. Manual deletion removes all live task content including names and files. Manual retention and low-disk rejection apply in V1. Make UI strings translation-ready but ship only English. Pin dependencies, test authorization and security boundaries, and provide an idempotent installer that updates a preparation-time Ubuntu VM, safely handles reboot requirements, and leaves all runtime workflows functional with WAN blocked. Do not add rich text, drafts, automatic retention, QR codes, telemetry, external assets, or online services to V1.
