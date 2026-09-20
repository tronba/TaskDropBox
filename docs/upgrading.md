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
