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

