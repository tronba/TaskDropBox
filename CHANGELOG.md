# Changelog

## Unreleased

- Fix creator PIN hashing during installation by initializing Django settings.
- Make test discovery independent of the installer's inaccessible working directory.
- Preserve the origin on same-origin form posts so Django CSRF validation succeeds.
- Group student submission warnings into one panel.
- Make the front page pupil-focused and move teacher entry points to `/teacher/`.
- Generate readable three-word student links while retaining strong teacher administration tokens.
- Preview safe images, media, PDFs, and text in new tabs while forcing risky formats to download.
- Suppress expected SQLite checkpoint and authorization noise during tests.
- Remove the AI disclosure from the application footer and silence the Nginx proxy-header warning.
- Initial TaskDropBox V1 project structure.
- Accountless task creation, submission, review, export, and deletion foundation.
- Standalone Ubuntu 26.04 deployment templates and preparation documentation.
