# Upgrading

Fetch the reviewed TaskDropBox revision while Internet access is available, then run the upgrade from the checkout:

```text
cd ~/TaskDropBox
git pull --ff-only
sudo bash install.sh --upgrade
sudo taskdropbox-admin doctor
```

For a controlled deployment, record and review the exact commit being installed rather than upgrading blindly from an unknown branch state.

The upgrade path applies Ubuntu updates, stops for a required reboot, stops TaskDropBox cleanly, preserves configuration and live data, replaces application code, builds a clean virtual environment, runs migrations, tests, and static collection, validates Nginx, restarts services, and performs an HTTP health check.

It does not remove `/var/lib/taskdropbox`, but it is not a backup system. Upgrade the prepared image before an emergency, or only after teachers have exported required work. Afterward, block WAN access and repeat the offline acceptance workflow before refreshing the standby VM snapshot.

If `git pull --ff-only` reports local changes or a divergent branch, stop and inspect the checkout instead of forcing it.

The concurrency fixes add migration `0003_task_creation_nonce_hash` and an Nginx
limit allowing one export at a time. Use the full upgrade procedure so both the
database and Nginx configuration are updated; copying Python files alone is not
sufficient. Existing task keys and submissions are preserved.

Verification for this change must be performed on a disposable server/test VM:

```text
sudo taskdropbox-manage check
sudo taskdropbox-manage makemigrations --check --dry-run
sudo taskdropbox-manage test drops.tests --noinput
sudo nginx -t
```

Also request a large export from two teacher browsers at once. One should proceed
and the other receive HTTP 429, while a pupil can still submit work. Confirm the ZIP
contents and manifest, and repeat a successful pupil submission after closing its
task: the original submission key should still return its receipt. The source edits
include regression tests, but these fixes have not been executed on the coding machine.

On the disposable VM, run `python scripts/review_edge_cases.py` from a source checkout
using its prepared Python environment for the file-backed concurrent-request probes.
This uses temporary data, but still does not replace the Nginx/browser checks above.
