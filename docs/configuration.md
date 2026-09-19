# Configuration

Production configuration is stored in `/etc/taskdropbox/taskdropbox.env`, owned by `root:taskdropbox` with mode `0640`. Never commit this file.

Use the installer to reconfigure supported settings:

```text
sudo bash install.sh --reconfigure
```

The installer backs up the previous environment file before replacing it and preserves `/var/lib/taskdropbox`.

To generate a replacement creator-PIN hash without placing the PIN in shell history:

```text
sudo taskdropbox-manage create_creator_pin_hash
```

Place the resulting hash in `TASKDROPBOX_CREATOR_PIN_HASH`, restart `taskdropbox.service`, and protect the environment file. Changing the hash invalidates existing creator sessions. It does not affect task-specific student or administration keys.

After any change:

```text
sudo systemctl restart taskdropbox
sudo systemctl status taskdropbox
```

The maximum request size in Nginx must remain at least five MiB larger than the configured total submission size.
