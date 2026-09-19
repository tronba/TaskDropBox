# Backup and restore

Back up the database and private files together:

```text
/var/lib/taskdropbox/db.sqlite3
/var/lib/taskdropbox/files/
```

Do not copy a changing SQLite database file directly. Create a consistent database copy first:

```text
sudo taskdropbox-manage backup_db /path/to/backup/db.sqlite3
```

Then copy that database backup and `/var/lib/taskdropbox/files/` into the same protected backup set. Alternatively, stop TaskDropBox briefly before copying the complete data directory.

Backups may contain names and submitted school work that has since been deleted from the live system. Restrict access, encrypt backup media where practical, set an expiry schedule, and delete expired backup sets separately.

## Restore outline

1. Install the same TaskDropBox release on a separate clean VM.
2. Stop `taskdropbox.service`.
3. Restore the database and files together with owner/group `taskdropbox:taskdropbox`.
4. Run database migrations for the installed release.
5. Start the service and run `show_status`.
6. Test task administration, a file download, and a ZIP export.

A backup is not proven until this process succeeds on a separate instance.
