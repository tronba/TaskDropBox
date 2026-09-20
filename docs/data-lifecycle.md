# Data lifecycle

TaskDropBox is temporary emergency infrastructure, not a long-term document store. Teachers should export required submissions as soon as practical and verify the downloaded ZIP before relying on it.

The server does not create operational backups. An export is the supported way to retain submitted work outside TaskDropBox.

During use, an authorized teacher can delete an individual submission or a complete task. After the emergency period, the operator should close submissions, confirm teachers have completed their exports, and erase all live application data:

```text
sudo taskdropbox-admin close-all
sudo taskdropbox-admin flush-data
```

`flush-data` displays the live task and submission counts, stops the application service, and requires the exact phrase `DELETE ALL TASKDROPBOX DATA`. It permanently removes tasks, submissions, uploaded files, and browser authorization sessions. Configuration and installed application files remain available for the next event.

Downloaded exports and copies made outside TaskDropBox are not affected. Ordinary deletion also cannot guarantee forensic erasure from physical storage; use encrypted VM storage and dispose of VM images according to the school's policy.
