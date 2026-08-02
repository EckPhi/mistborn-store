# Leistungsbot

Telegram bot that organises the recurring **Leistungstag** of a chat group. It posts the location poll, keeps a curated location list backed by the Google Places API, reminds the group, closes finished polls and backs its own database up into a chat.

This is a headless service: there is no web UI. It is operated entirely from Telegram, and its output is visible in the container logs.

## What it does

- `/leistungspoll`, `/zusatzpoll`, `/konkurrenzpoll` — create the location polls (with a date picker).
- `/add_location`, `/remove_location`, `/show_locations`, `/location_info`, `/rate_location` — manage the location list; opening hours, address and ratings come from Google Places.
- `/show_participants`, `/reminde_me`, `/purge`, `/help`, `/version` — everyday commands.
- `/backup` — admin-only database dump into the backup chat.
- Scheduled by the bot itself: daily reminder at 12:00, reservation nudge every Monday 12:00, previous poll closed daily at 19:00, weekly backup Sunday 04:00. These follow the app's **timezone**, which runtipi passes in as `TZ`.

## Configuration

All settings are passed as environment variables; no config file is needed.

- **Bot token** — from [@BotFather](https://t.me/BotFather).
- **API ID / API hash** — from [my.telegram.org](https://my.telegram.org).
- **Google Maps API key** — a Places-enabled key.
- **Chat IDs** — `Leistungschat` is where polls go, `Leistungsadmin` receives scheduler reports, the *log chat* receives errors. Add the bot to the chat and use `/showIds` to read the numeric IDs.
- **Operator usernames** — space-separated Telegram usernames (no `@`) allowed to run the privileged commands.
- **Backup chat ID** — optional; leave empty to skip the weekly backup upload.
- **Config file** — optional. Set it to `/config/BotConfig.yml` to additionally read `app-data/data/config/BotConfig.yml` (same keys as `BotConfig.example` upstream). The form fields still take precedence over the file.

## Data

State is a single SQLite file at `app-data/data/storage/leistungs_db.sqlite` — no database container. Back it up by copying that file, or let the bot mail it to the backup chat every Sunday.

To inspect it, stop the app and open the file with any SQLite browser. The upstream repository ships a `sqlitebrowser` dev profile for this; it is deliberately **not** part of this app, because that image runs a full desktop with passwordless sudo and must never be reachable over the network.
