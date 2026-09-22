# Runtipi Companion

Runtipi Companion creates verified local backups of installed Runtipi apps
and transfers successful archives through the authenticated Remote Control
API of the **Rclone Mount** app. The backup remote is never mounted: uploads,
listings, retention pruning and restore downloads use rclone directly.

Install and configure **Rclone Mount** first, then copy its GUI username and
generated password into this app's install form. The selected target, for
example `encrypted:runtipi-backups`, must exist in rclone.

The container mounts the Runtipi installation and Docker socket so it can
archive app data and stop/restart applications consistently. Docker socket
access is effectively root access to the host. Host security hardening and
Runtipi setup remain available only through the standalone Companion CLI.

Daily backups run at the configured local hour. Weekly backups run Sunday;
monthly backups on the first day; yearly backups on January 1. Archives are
created and fully verified locally before upload. The uploaded object size is
also checked before retention pruning. Rclone and Companion remain running so
the pipeline cannot stop itself.

The app page is a health endpoint, not a management UI. Configuration is
rendered from the Runtipi install form whenever the container starts.
