# Troubleshooting

## Front page does not open

- Verify the VM IP with `ip address`.
- Verify `systemctl status taskdropbox nginx`.
- Run `nginx -t`.
- From the VM, request `curl http://127.0.0.1/healthz`.
- Check the VM and network firewall for TCP port 80.

## Links use the wrong IP

Run the installer with `--reconfigure`, set the correct static-IP base URL, and restart. Previously distributed URLs containing the old IP must be redistributed.

## New submissions return 503

TaskDropBox is protecting its configured free-space reserve. Existing content is not automatically deleted. Export and manually delete eligible tasks or expand the VM disk, then verify free space.

## Deadlines look wrong

Run the status command and compare server time/timezone with a trusted clock. Correct the VM clock before creating further tasks. Existing recorded submission timestamps are not rewritten automatically.

## Installer exits with code 20

Ubuntu installed updates that require a reboot. Reboot the VM and rerun the same installer command.

## Upgrade reports that `venv` directories cannot be deleted

An older installer allowed source synchronization to enter the installed Python virtual environment while excluding its bytecode files. This could produce many `cannot delete non-empty directory: venv/...` messages and leave the service stopped, but it did not touch `/var/lib/taskdropbox` or any task data.

Update the source checkout to a release containing the virtual-environment upgrade fix and rerun:

```text
sudo bash install.sh --upgrade
sudo taskdropbox-admin doctor
```

The corrected installer excludes the old environment from synchronization, constructs a clean replacement, and restores the previous environment if construction fails. Do not manually delete `/var/lib/taskdropbox` while recovering.
