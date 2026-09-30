# Leistungsbot

Telegram bot that organises the recurring **Leistungstag** of a chat group. It posts the location poll, keeps a curated location list backed by the Google Places API, reminds the group, closes finished polls and backs its own database up into a chat.

This is a headless service: there is no web UI. It is operated entirely from Telegram, and its output is visible in the container logs.

## What it does

- `/leistungspoll`, `/zusatzpoll`, `/konkurrenzpoll` — create the location polls (with a date picker).
- `/add_location`, `/remove_location`, `/show_locations`, `/location_info`, `/rate_location` — manage the location list; opening hours, address and ratings come from Google Places.
- `/show_participants`, `/reminde_me`, `/purge`, `/help`, `/version` — everyday commands.
- `/backup` — admin-only database dump into the backup chat.
- Keeps a Google Calendar in step with the leistungstage, if one is configured — see below.
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
- **Calendar** — optional, see below. Leave the calendar ID empty to keep no calendar.

## Calendar

Publishing a leistungstag creates a calendar entry, closing its poll or moving it to another location updates that entry, and purging it takes the entry away again. At every start the bot also walks its whole database into the calendar, so the leistungstage that predate the calendar end up in there too — that pass is safe to repeat and never duplicates an entry.

Setting it up:

1. In the Google Cloud console, **enable the Google Calendar API** for a project.
2. Create a **service account** and download its JSON key. No OAuth client ID and no consent screen — the bot has nobody to click "Allow".
3. Put the key in `app-data/data/config/` and point the **Google service account key** field at it, e.g. `/config/google-service-account.json`.
4. Create a **secondary** calendar (not your primary one) and share it with the service account's email address, `…@….iam.gserviceaccount.com`, as **"Make changes to events"**. Without this step every call answers `404` and it looks like a wrong calendar ID.
5. Copy the calendar ID from the calendar's settings page, "Integrate calendar", into the **Google Calendar ID** field.

The **calendar timezone** field may stay empty, in which case the app's timezone is used. Entries go in as wall clock time plus that zone, so a leistungstag stays at seven in the evening across a daylight saving change.

Entries are created *by* the service account, so it shows up as the organiser and cannot invite anyone.

## Data

State is a single SQLite file at `app-data/data/storage/leistungs_db.sqlite` — no database container. Back it up by copying that file, or let the bot mail it to the backup chat every Sunday.

To inspect it, stop the app and open the file with any SQLite browser. The upstream repository ships a `sqlitebrowser` dev profile for this; it is deliberately **not** part of this app, because that image runs a full desktop with passwordless sudo and must never be reachable over the network.
