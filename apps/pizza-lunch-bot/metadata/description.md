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

## Telegram Mini App

The Mini App shows the weekly poll, confirmed lunch, and RSVP list. It shares
the same saved state as the chat bot.

1. In Runtipi, expose the app on a domain with HTTPS that group members can
   reach. Serve it at the domain root and leave Runtipi's proxy authentication
   disabled for this route so Telegram can load it. The app checks Telegram
   identity and group membership.
2. In BotFather, use `/newapp` to register the HTTPS URL and choose a short name.
   Enter the same short name in Runtipi's **Telegram Mini App short name** field
   and restart the app. This starts the bot's built-in web server.
3. Make the bot an administrator in the Telegram group so it can verify
   membership. Open the Mini App from the weekly poll card or send
   `/pizza@your_bot` with the actual bot username.

Leave the short name blank to use Telegram chat commands and buttons only.
