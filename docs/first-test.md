# First disposable-VM test

Use a new Ubuntu Server 26.04 LTS VM with a snapshot. Do not use the intended emergency VM for this first run.

Record each command, unexpected message, browser error, and screenshot. If the installer fails, stop and preserve its complete terminal output rather than manually repairing the installation.

## 1. Prepare

- 2 CPU cores, 4 GiB RAM, and at least 40 GiB local disk.
- Current Ubuntu Server 26.04 point release.
- Temporary Internet access during preparation.
- Static private IP assigned to the VM.
- A client computer on the same LAN.
- A six-digit test creator PIN that is not used elsewhere.
- A VM snapshot before running TaskDropBox installation.

Copy a tagged source archive or the complete repository checkout to the VM. Confirm that it contains `LICENSE`, `AI_DISCLOSURE.md`, `install.sh`, `pyproject.toml`, `manage.py`, `config/`, `drops/`, `templates/`, `static/`, and `deploy/`.

## 2. Install

From the extracted source directory:

```text
sudo bash install.sh
```

Expected behavior:

1. It confirms Ubuntu 26.04.
2. It prompts for static HTTP URL, timezone, PIN, and configuration.
3. It displays a summary before changing the VM.
4. It applies Ubuntu updates.
5. If it exits with code 20, reboot and run the same command again.
6. It installs dependencies, migrates the database, collects static files, runs checks/tests, validates Nginx, starts services, and completes an HTTP health check.
7. It prints the service URL and data/configuration paths.

Do not continue if the embedded Django tests fail.

## 3. Verify services and configuration

```text
sudo systemctl status taskdropbox nginx --no-pager
sudo taskdropbox-admin status
sudo taskdropbox-admin check-storage --checksums
curl --fail http://127.0.0.1/healthz
```

Expected: both services active, database OK, correct timezone/base URL, no missing/orphaned files, and `ok` health response.

Check permissions without displaying secrets:

```text
sudo stat -c '%U %G %a %n' /etc/taskdropbox/taskdropbox.env /var/lib/taskdropbox
```

Expected:

```text
root taskdropbox 640 /etc/taskdropbox/taskdropbox.env
taskdropbox taskdropbox 750 /var/lib/taskdropbox
```

## 4. Browser workflow

From a second computer, open the static-IP URL.

1. Confirm the front page prominently offers **Open a task** and links to **Teacher tools**, without showing teacher forms.
2. Open **Teacher tools** and confirm it has **Create a task** and **Manage a task**. Enter two incorrect creator PINs, then the correct PIN. Confirm the correct PIN succeeds.
3. Create a task with:
   - a title;
   - rich-text instructions using bold, italic, and a list;
   - pasted HTML containing a script, styled element, link, and image;
   - a due time five minutes in the future;
   - text and file answers enabled;
   - one harmless task attachment.
4. Confirm the student key contains three readable words, then save both generated links outside the browser.
5. Confirm supported formatting remains, unsupported markup is removed, and nothing executes.
6. Open the student task from its full link.
7. Open the task attachment. Confirm browser-safe images, media, PDFs, or plain text open in a new tab, while other formats download.
8. Submit a student name, formatted web answer, and two harmless files. Include another unsupported pasted HTML sample.
9. Confirm one receipt appears with name, time, filenames, and on-time status but not answer text.
10. Refresh the receipt and confirm no second submission is created.
11. Open the teacher administration link and confirm exactly one submission appears.
12. Download each file.
13. Export the ZIP and inspect its manifest, formatted HTML answer, plain-text answer, filenames, and original uploaded content.

## 5. Deadline, close, and isolation

1. Create a second task whose due time is already past.
2. Submit work and confirm it is accepted and marked **Late**.
3. Close that task and confirm a new submission receives a closed-task message.
4. Reopen it, submit again, and confirm the new work is marked late.
5. In a private/incognito browser without the admin link, try the clean `/manage/<task UUID>/` URL copied from the authorized browser. Expect a generic 404.
6. Enter an invalid student key on the front page and an invalid admin key on the teacher page. Confirm neither reveals whether a similar task exists.
7. Confirm student pages never show names, counts, or files from other submissions.

## 6. Delete and storage verification

1. Delete one submission and confirm its text, name, and files disappear while other work remains.
2. Run `sudo taskdropbox-admin check-storage --checksums`; expect no errors.
3. Delete the complete task and confirm its student/admin/receipt links return generic 404 pages.
4. Run storage checking again; expect no missing or orphaned files.

## 7. SSH administration and language

1. Run `sudo taskdropbox-admin`, navigate every menu and submenu, and exit without changing data.
2. Run `sudo taskdropbox-admin status` and `sudo taskdropbox-admin doctor` directly.
3. Change the default to Norwegian Bokmål through the menu, open a new private browser window, and confirm the web interface defaults to Norwegian Bokmål.
4. Change that browser to English using the page header and confirm the selection follows the browser through the pupil workflow.
5. Restore English as the default and confirm a different new private browser defaults to English.
6. Test task listing, close-all, session revocation, and single-task deletion from the menu with disposable tasks.
7. Export all work that must be retained, then test full data erasure. Confirm all task links stop working and the configuration remains intact.

## 8. Offline operation

1. Disconnect/block the VM's WAN route while preserving the local LAN.
2. Restart the VM.
3. Verify clock and status.
4. Repeat create → submit → review → export → delete.
5. In browser developer tools, confirm pages make no requests to Internet hosts.
6. Open `/source/` and confirm the installed source archive downloads locally.

## 9. Reconfigure and upgrade safety

Take another VM snapshot, then run:

```text
sudo bash install.sh --reconfigure
```

Change the creator PIN. Confirm the old PIN and any old creator session stop working, while task-specific links still work.

Run `--upgrade` from the same source as an idempotence test. Confirm all tests pass and existing tasks remain. Operational upgrades should occur before an emergency or after teachers have exported required work.

## 10. Uninstall preservation

Only after the other tests and a snapshot:

```text
sudo bash uninstall.sh
```

Confirm services and `/opt/taskdropbox` are removed, while `/var/lib/taskdropbox` and `/etc/taskdropbox` remain. Do not manually delete the preserved paths during this test.
