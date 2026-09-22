# Edge-case and concurrency review — 2026-09-20

> Historical review of the code before the subsequent fixes. Source changes now
> address the findings below, and the probes have been adjusted to use a separate
> connection for the deletion race. The updated code and tests have not been run
> on the coding machine. Follow `docs/upgrading.md` for server-side verification.

## Outcome

The existing checks pass, and small concurrent uploads work well in isolated application tests. Three reproducible edge-case defects remain. Production capacity is not established by these results: the tests ran on Windows with Python 3.12 and Django 5.2.17, without the Ubuntu VM, Nginx, Gunicorn, or a real network.

No application behavior was changed. Added `scripts/review_edge_cases.py` to reproduce the findings using a temporary, file-backed SQLite database and private files. It overrides the data directory before loading Django, closes connections, and removes its disposable data afterward. Its JSON reports observations; exit status zero means the probe completed, not that every observed behavior is correct.

## Reproduced findings

### P1: Task deletion can leave private pupil files behind

Location: `drops/services.py:162–173`.

Deletion enumerates filenames and stages them before starting its database transaction. A submission can commit between that enumeration and the transaction. The subsequent cascading database deletion removes the new submission and file record, but the newly uploaded file was absent from the deletion list and remains on disk.

The probe deterministically inserts an upload at this boundary: deletion finishes with one orphaned private file. This violates the complete live-content deletion expectation and consumes disk indefinitely. `check-storage` can report the orphan but does not remove it.

Recommendation: acquire the SQLite write transaction before enumerating related files, and keep enumeration, staging, and row deletion coordinated under that transaction. Preserve file restoration on rollback and handle submissions whose task disappears while their uploads are being prepared. Add a regression test with controlled interleaving.

### P2: Simultaneous task creation bypasses single-use nonce protection

Location: `drops/views.py:120–136`.

The nonce is checked in each request's session snapshot, then removed only after task creation. Two requests with the same cookie and nonce can both pass the check. The probe synchronizes two requests after validation and observes two HTTP 200 responses and two distinct tasks.

The existing `test_creation_form_cannot_be_reused` tests sequential requests only. Disabling a browser button would reduce accidental triggers but would not enforce this server-side invariant.

Recommendation: atomically claim the nonce in persistent storage with a uniqueness constraint as part of task creation. Define recovery behavior when task creation succeeds but its response is lost, since generated capability keys are only shown in that response.

### P2: Retrying an accepted submission can incorrectly report failure

Locations: `drops/views.py:196`; `drops/services.py:75–87`.

A submission commits, but its response is lost. If the teacher closes the task before the pupil retries, the view returns HTTP 409 before looking up the existing submission. If the disk reserve is reached instead, storage checks return HTTP 503 before the idempotency lookup. The existing receipt still exists in both cases.

Both outcomes were reproduced with the same task and idempotency key. This can make a pupil think accepted work was not handed in.

Recommendation: resolve a task-scoped existing idempotency key before checking eligibility for a new submission or preparing files. Keep the check inside the write transaction too, to protect simultaneous first attempts. A new key must still be rejected on a closed task or when space is insufficient.

## Many-user risks identified in configuration and code

These are source-based risks, not measured production failures.

- **Shared client IP:** Nginx throttles by `$binary_remote_addr`. Pupils behind one NAT or proxy share 10 submissions/minute with burst 5, 60 general requests/minute with burst 20, and a six-connection limit on the general location. A classroom burst through one address can receive HTTP 429 even when the application has spare capacity. Test both distinct source addresses and the actual school's shared-address topology before changing limits.
- **Large exports occupy scarce workers:** deployment starts three synchronous Gunicorn workers. ZIP generation completes before returning a response, so three active exports can occupy all application workers. The export queryset caches all submissions, including answer text, and prefetches all file records; only the ZIP payload spills to disk. Memory therefore grows with task size. Use chunked iteration and measure export concurrency before selecting a mitigation such as a global export limit or separate export processing.
- **Temporary disk use is outside the reserve check:** upload parsing, Nginx request buffering, and export spooling can use temporary storage. `ensure_space` checks only the data filesystem, and checks do not reserve bytes against concurrent requests. Validate the actual filesystem layout, export sizes, and low-space behavior. A 1 GiB reserve is not a hard reservation across these operations.
- **Lock and proxy timeouts need testing:** SQLite waits up to 20 seconds for a write lock; unhandled database/storage errors become generic failures. Gunicorn has a 120-second timeout, while the Nginx template does not explicitly set a matching proxy read timeout. Test slow exports and write-lock contention through the installed stack.

## Checks completed

| Check | Result |
|---|---|
| Existing Django suite | 44/44 passed |
| Application statement coverage, excluding tests | 81%; services 70% |
| Django system check | No errors; expected warning for absent local creator PIN |
| Migration drift | No changes detected |
| Ruff | Passed |
| 30 uploads, up to 30 active threads | 30 accepted; 0 exceptions; p95 0.733 s |
| 100 uploads, up to 32 active threads | 100 accepted; 0 exceptions; p95 0.674 s |
| 300 uploads, up to 32 active threads | 300 accepted; 0 exceptions; p95 1.044 s |
| 30 requests with the same submission key | One submission and one receipt |
| Database failure after moving an uploaded file | No saved submission or leftover new file |
| Missing CSRF token with enforcement enabled | HTTP 403 |
| Empty answer, oversize file, oversize total, excessive file count | HTTP 400; no submission saved |
| Reusing another task's submission key | HTTP 404 |
| SQLite integrity and foreign-key checks after probes | `ok`; no foreign-key violations |

Upload probes used a 64 KiB attachment per request and Django's test client with independent thread-local database connections. Most test clients intentionally bypass CSRF; the separate CSRF probe enables enforcement. These are in-process request timings from one run, not network latency or supported user-count guarantees. Race reproductions use controlled hooks/barriers to make the problematic interleaving deterministic.

Run the isolated probes after installing the project's development dependencies:

```text
python scripts/review_edge_cases.py
```

For the standard suite, set a disposable `TASKDROPBOX_DATA_DIR`, a test `TASKDROPBOX_SECRET_KEY`, and `TASKDROPBOX_BASE_URL=http://127.0.0.1`. The default settings otherwise fail the production-secret/origin checks; the Django test runner forces DEBUG off.

## Next acceptance tests on a disposable Ubuntu VM

1. Run 30, 100, and 300 pupil workflows through Nginx, including page load, CSRF, attachment download, submission, and receipt. Use both distinct source IPs and shared-IP clients. Record HTTP status counts, p50/p95/p99 latency, queueing, CPU, RAM, disk space, and database lock errors. Compare accepted receipts against stored rows and checksums.
2. Repeat with typical documents and near-limit uploads: defaults allow 25 MiB per file and 50 MiB total per submission. Use incompressible content as well as text. Three hundred maximum-size submissions represent about 14.6 GiB of uploaded content before temporary copies and exports.
3. Mix submissions with one and three simultaneous exports; include large text answers and thousands of submissions. Measure worker availability, export memory, temporary disk use, and timeout behavior. Do not infer capacity from the small-upload probe.
4. After fixing the reproduced defects, test close/reopen/delete during uploads, simultaneous creation, response loss and retry, and export during deletion. Require consistent receipts and no missing/orphaned files.
5. Inject low space on both data and temporary filesystems, a write lock exceeding 20 seconds, and a worker termination between file movement and transaction completion. Run integrity and storage checks after restart. Verify useful user feedback and a documented operator recovery procedure.
6. Complete the existing `docs/first-test.md` browser/offline acceptance procedure, including supported browsers, Norwegian UI, permissions, upgrade, and WAN-disconnected restart. These deployment/browser checks were not run in this review.
