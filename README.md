# TaskDropBox V1.1

TaskDropBox is an accountless assignment hand-in box for an isolated school LAN. It is prepared before an Internet outage and then runs from a standalone Ubuntu Server VM without DNS, cloud services, external assets, or runtime Internet access.

Repository: [github.com/tronba/TaskDropBox](https://github.com/tronba/TaskDropBox)

## What V1.1 provides

- Pupil-focused front page with a separate teacher area.
- System-wide six-digit PIN for creating tasks.
- Readable three-word pupil keys and independent high-entropy teacher keys.
- Rich-text instructions and answers with bold, italic, and lists.
- Multiple private file attachments and safe in-browser previews where possible.
- Optional soft deadlines, late marking, and explicit close/reopen controls.
- Teacher review, individual downloads, ZIP export, and deletion.
- English and Norwegian Bokmål web interfaces.
- SSH-only interactive administration menu and scriptable subcommands.
- No accounts, profiles, class lists, telemetry, external services, or runtime AI.

TaskDropBox is temporary emergency infrastructure. Teachers should export required work promptly. The server deliberately has no operational backup workflow.

## Requirements

- Ubuntu Server 26.04 LTS on an AMD64 VM
- Static private IPv4 address or fixed DHCP reservation
- Temporary Internet access during installation and upgrades
- Recommended minimum: 2 CPU cores, 4 GiB RAM, and 40 GiB local storage
- An isolated or appropriately restricted school LAN for runtime use

## Install from GitHub

On a clean Ubuntu Server 26.04 VM:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/tronba/TaskDropBox.git
cd TaskDropBox
sudo bash install.sh
```

The English-language installer asks for the static URL, school timezone, a six-digit creator PIN entered twice, upload limits, and the free-disk reserve.

If the installer exits with status 20, reboot and rerun it:

```bash
sudo reboot
```

After reconnecting:

```bash
cd TaskDropBox
sudo bash install.sh
```

When installation succeeds, open the displayed URL from another computer on the LAN.

## Non-interactive installation

Store the PIN temporarily in a root-readable file:

```bash
printf '%s\n' '123456' | sudo tee /root/taskdropbox-pin >/dev/null
sudo chmod 600 /root/taskdropbox-pin
```

Then install:

```bash
sudo bash install.sh \
  --non-interactive \
  --base-url http://10.20.0.10 \
  --timezone Europe/Oslo \
  --creator-pin-file /root/taskdropbox-pin \
  --max-file-mib 25 \
  --max-submission-mib 50 \
  --min-free-mib 1024
sudo rm -f /root/taskdropbox-pin
```

Do not place the creator PIN directly on the command line.

## Verify the installation

```bash
sudo taskdropbox-admin doctor
curl --fail http://127.0.0.1/healthz
```

Then create a disposable task, submit text and a file from another browser, export it, and delete it. Block WAN access and repeat the workflow before treating the VM as ready for an emergency.

## SSH administration

Open the interactive menu:

```bash
sudo taskdropbox-admin
```

The menu covers status, diagnostics, configuration, security, task operations, storage maintenance, and confirmed full-data erasure.

Every function also remains available as a direct command:

```bash
sudo taskdropbox-admin status
sudo taskdropbox-admin doctor
sudo taskdropbox-admin set-pin
sudo taskdropbox-admin set-language en
sudo taskdropbox-admin set-language nb
sudo taskdropbox-admin configure
sudo taskdropbox-admin list-tasks
sudo taskdropbox-admin delete-task TASK-UUID
sudo taskdropbox-admin close-all
sudo taskdropbox-admin revoke-sessions
sudo taskdropbox-admin check-storage --checksums
sudo taskdropbox-admin checkpoint-database
sudo taskdropbox-admin flush-data
```

`flush-data` permanently removes every live task, submission, upload, and browser authorization session. It preserves system configuration and requires typing `DELETE ALL TASKDROPBOX DATA` exactly. It does not create a recovery copy.

## Language behavior

The installer and SSH administration interface are always English. The operator controls the default web language from the administration menu or with `set-language`. Pupils and teachers can change language from the page header; their choice stays in that browser only.

Teacher-written instructions and pupil answers are not automatically translated.

## Rich text and files

The bundled editor supports paragraphs, bold, italic, bulleted lists, and numbered lists. Submitted markup is rebuilt on the server from a strict allowlist with no attributes, scripts, styles, links, images, or embedded content.

ZIP exports contain both a formatted `.html` copy and a portable UTF-8 `.txt` copy of each web answer, plus original uploaded files and a CSV manifest.

## Upgrade

Update the source checkout and run the explicit upgrade mode:

```bash
cd TaskDropBox
git pull --ff-only
sudo bash install.sh --upgrade
sudo taskdropbox-admin doctor
```

The upgrade preserves configuration and live task data, rebuilds the Python virtual environment cleanly, applies database migrations, recompiles translations and static files, runs the test suite, and restarts the services.

Perform planned upgrades before an emergency or after teachers have exported required work.

## Reconfigure

Use the administration menu, or run:

```bash
sudo taskdropbox-admin configure
```

Existing task-specific pupil and teacher keys survive configuration changes. If the static IP changes, previously distributed URLs still contain the old address and must be redistributed.

## Data locations

```text
/opt/taskdropbox       application code and virtual environment
/etc/taskdropbox       protected configuration
/var/lib/taskdropbox   SQLite database and private uploaded files
```

Uploaded files are never served directly by Nginx. The `www-data` account is deliberately unable to read the configuration, database, or private file directory.

## Uninstall

From the source checkout:

```bash
sudo bash uninstall.sh
```

Uninstalling removes services and application code but preserves `/etc/taskdropbox` and `/var/lib/taskdropbox`. To erase live application data before uninstalling, first run:

```bash
sudo taskdropbox-admin flush-data
```

## Development checks

With Python 3.12 or newer:

```bash
python -m pip install -e ".[dev]"
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test drops.tests
python -m ruff check .
```

## Security boundaries

TaskDropBox uses plain HTTP by design for a rapidly deployable isolated LAN. HTTP does not protect traffic from someone able to intercept that LAN. Do not expose the service directly to the public Internet.

Capability links grant access. Treat teacher links as secrets, restrict SSH to operators, use a temporary protected network, and shut down or flush the server after the event.

Security reports are described in [SECURITY.md](SECURITY.md). The detailed implementation specification is in [TaskDropBox_Design_Document.md](TaskDropBox_Design_Document.md), and the disposable-VM acceptance procedure is in [docs/first-test.md](docs/first-test.md).

## License and development disclosure

TaskDropBox is licensed under the GNU Affero General Public License, version 3 or later (`AGPL-3.0-or-later`). The complete license is in [LICENSE](LICENSE). An installed server provides its installed source archive at `/source/` for offline access.

The initial design and implementation were generated by OpenAI Codex under human direction and review. TaskDropBox does not use AI at runtime or send application data to an AI provider. See [AI_DISCLOSURE.md](AI_DISCLOSURE.md).
