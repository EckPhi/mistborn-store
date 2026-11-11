# 🍕 Pizza Lunch Bot

Pizza Lunch Bot runs a weekly Telegram poll for Tuesday through Friday. Friends
can select every day they can make. At 20:00 on Monday in the configured time
zone, the bot picks the day with the most votes and breaks ties in favor of the
earliest day. The meetup starts at 13:00 by default. The organizer can change
the time, and the card shows who is going and which voters did not select the
winning day. One hour after lunch starts, the next poll opens.

## Setup

1. Create a Telegram bot with [@BotFather](https://t.me/BotFather).
2. Enter the token in Runtipi and choose your time zone. The default is
   `Europe/Vienna`.
3. Add your bot to the group as a regular member. Send `/weekly@your_bot`, using
   its actual username, to start the weekly cycle.

Run one instance per bot token. Runtipi keeps active polls and RSVPs in
`data/lunch-state.json` under the app's data directory.

## Admin website

Use **Open** in Runtipi to manage Telegram group and user access. For remote
access, enable HTTPS exposure in Runtipi and open the configured domain.
Sign in with the generated `PIZZA_LUNCH_BOT_ADMIN_TOKEN` from the app's
`app.env` in its Runtipi app-data directory.

Back up `data/lunch-state.access.json` along with the weekly state file to
preserve the access rules and directory.

## Telegram Mini App

The optional Mini App shows the weekly poll, confirmed lunch, and RSVP list.
It shares the same saved state as the chat bot. Leave the short name blank to
disable the Mini App.

1. If you use the Mini App, configure a separate HTTPS reverse proxy route
   from a domain reachable by group members to port 8080 on the bot container.
   The app checks Telegram identity and group membership.
2. In BotFather, use `/newapp` to register the HTTPS URL and choose a short name.
   Enter the same short name in Runtipi's **Telegram Mini App short name** field
   and restart the app. This starts the bot's built-in web server.
3. Make the bot an administrator in the Telegram group so it can verify
   membership. Open the Mini App from the weekly poll card or send
   `/pizza@your_bot` with the actual bot username.
