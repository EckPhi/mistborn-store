# JDownloader 2

JDownloader 2 is a download manager with link collection, download queues, file-hosting account support and automatic archive extraction. This package uses the jlesage container to provide the full desktop application in your browser.

## Getting started

Open the app in Runtipi, or visit `http://<host-ip>:5800`, and sign in with the web username and password configured during installation. The default username is `admin`. Complete JDownloader's first-run dialogs in the browser desktop. Initial startup can take several minutes while JDownloader downloads its updates.

Use Runtipi's HTTPS exposure for encrypted remote access. The container serves HTTP internally so Runtipi can terminate HTTPS; web authentication is explicitly enabled for this setup. Direct HTTP access does not encrypt your login or desktop session.

## Downloads and backups

Keep JDownloader's download directory set to `/output`. Downloads are stored in `downloads/` under this app's Runtipi app-data directory. Settings, accounts and download queues are stored in `config/`. Back up both directories to preserve the complete installation. The container initializes permissions itself and runs JDownloader as UID/GID 1000 by default.

## Optional MyJDownloader access

You can configure a MyJDownloader account in JDownloader's settings to use its mobile apps and browser extensions. An account is not needed for the browser desktop. This package does not publish raw VNC or MyJDownloader Direct Connection ports; use the browser desktop or MyJDownloader's normal remote connection.

The store version follows the container release tag. JDownloader also updates its own application and plugins inside the persistent configuration directory.

[JDownloader website](https://jdownloader.org) · [Container documentation](https://github.com/jlesage/docker-jdownloader-2)
