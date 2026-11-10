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

The app runs entirely through Telegram. It uses outbound HTTPS and has no web
UI or published ports. Run one instance per bot token. Runtipi keeps active
polls and RSVPs in `data/lunch-state.json` under the app's data directory.
