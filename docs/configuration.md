# Configuration

Production configuration is stored in `/etc/taskdropbox/taskdropbox.env`, owned by `root:taskdropbox` with mode `0640`. Never commit this file.

Use the SSH-only administration command:

```text
sudo taskdropbox-admin help
```

Common operations include:

```text
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
sudo taskdropbox-admin flush-data
```

The installer and all SSH administration prompts remain in English. `set-language` changes the default web-interface language for browsers that have not made their own choice. A pupil or teacher can override the default with the language control in the page header; that preference remains in that browser only.

The configuration command uses the installer to change supported settings:

```text
sudo taskdropbox-admin configure
```

Configuration is preserved when application data is flushed. `flush-data` permanently removes all tasks, submissions, uploaded files, and browser sessions after requiring the exact confirmation phrase. It does not make a recovery copy.

Changing the creator PIN invalidates existing creator sessions. It does not affect task-specific student or administration keys.

After any change:

```text
sudo systemctl restart taskdropbox
sudo systemctl status taskdropbox
```

The maximum request size in Nginx must remain at least five MiB larger than the configured total submission size.
