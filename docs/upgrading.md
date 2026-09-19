# Upgrading

Download and verify a tagged release while Internet access is available, then extract it on the VM and run:

```text
sudo bash install.sh --upgrade
```

The upgrade path applies Ubuntu updates, stops for a required reboot, stops TaskDropBox cleanly, backs up configuration and the SQLite database, replaces application code, updates the virtual environment, runs migrations, tests, and static collection, validates Nginx, restarts services, and performs an HTTP health check.

It does not remove `/var/lib/taskdropbox`. Take a verified backup before upgrading. Afterward, block WAN access and repeat the offline acceptance workflow before refreshing the standby VM snapshot.

Do not deploy from an unpinned default branch or use `git pull` as a production upgrade procedure.
