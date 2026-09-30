# YouTrack

YouTrack is JetBrains' project management and issue tracking platform. It combines issue tracking, agile boards (Scrum and Kanban), Gantt charts, a knowledge base, customizable workflows, time tracking and reporting in a single tool.

## First start — Configuration Wizard

On the first launch YouTrack asks for a **wizard token**. You can find it in either of these places:

- the container logs: `docker logs youtrack_<app-id>` (look for the token URL near the end of startup), or
- the file `conf/internal/services/configurationWizard/wizard_token.txt` inside the app's data directory.

Paste the token into the wizard, then follow the setup steps (create the admin account, set the base URL).

## Notes

- If you expose YouTrack on a domain via runtipi, set that URL as the **Base URL** in the wizard (or later under *Administration → Settings*) so links and notifications are generated correctly.
- Data, configuration, logs and backups are persisted in separate volumes under the app data directory. Backups created from *Administration → Backup* land in the `backups` volume.
- The container runs as the unprivileged user `13001`; an init container fixes volume ownership automatically on every start.
