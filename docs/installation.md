# Installation on Ubuntu Server 26.04

TaskDropBox is prepared while Internet access is available and then tested with WAN access blocked. Use a current Ubuntu Server 26.04 LTS point-release image on an AMD64 VM.

Recommended minimum for a small school deployment: 2 CPU cores, 4 GiB RAM, and 40 GiB dynamically allocated local storage. Increase storage for large media submissions.

## Before running the installer

1. Assign the VM a static private IP or a DHCP reservation that will not change.
2. Verify the VM clock and timezone.
3. Download a tagged TaskDropBox release and verify its published SHA-256 checksum.
4. Extract the release locally on the VM.
5. Choose a six-digit creator PIN and store it temporarily in a root-readable file if using unattended mode.

## Interactive installation

```text
cd /path/to/extracted/taskdropbox
sudo bash install.sh
```

The installer previews its changes, updates Ubuntu packages, and stops with exit code 20 if Ubuntu requires a reboot. Reboot and run the same command again. It never automatically reboots unless a future explicitly documented option says otherwise.

The installer creates:

```text
/opt/taskdropbox
/etc/taskdropbox/taskdropbox.env
/var/lib/taskdropbox/db.sqlite3
/var/lib/taskdropbox/files
/etc/systemd/system/taskdropbox.service
/etc/nginx/sites-available/taskdropbox
/usr/local/sbin/taskdropbox-admin
```

## Unattended installation

```text
sudo bash install.sh \
  --non-interactive \
  --base-url http://10.20.0.10 \
  --timezone Europe/Oslo \
  --creator-pin-file /root/taskdropbox-pin
```

The PIN file must contain exactly six digits. Delete the plaintext PIN file after successful installation. Do not provide secrets as command-line values.

## Verification

1. Run `sudo systemctl status taskdropbox nginx`.
2. Run `sudo taskdropbox-admin doctor`.
3. Open `http://<static-ip>/` from another computer on the isolated LAN.
4. Create a disposable task, submit text and a file, export it, and delete it.
5. Block WAN access and repeat the workflow.
6. Create a clean VM snapshot only after the offline test passes.

TaskDropBox uses HTTP at a literal IPv4 address. Browsers may label it “Not secure,” but it does not show an invalid-certificate warning. HTTP does not protect traffic from interception on the LAN.
