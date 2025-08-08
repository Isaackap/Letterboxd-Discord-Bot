# Letterboxd Diary Discord Bot

This Discord bot brings Letterboxd diary activity directly to your server. It automatically checks and announces users' new diary entries, including ratings, reviews, and film info, in a designated channel. This is a great way for film discussion communities to stay updated on what their members are watching.

## Bot Invite Link

### Status: Online
### [Letterbotd](https://discord.com/oauth2/authorize?client_id=1402450006077870160&permissions=277025703936&integration_type=0&scope=bot)

## Bot Purpose

- Tracks Letterboxd diary entries for selected users.
-  Posts diary updates in a server-specific default channel.
-  Provides commands to manage users and configurations.
-  Runs automatically on a timer — no manual refreshing required.

---

##  Required Discord Permissions

The bot needs the following permissions in the server:

-  **Send Messages**
-  **Send Messages in Threads**
-  **Embed Links**
-  **Attach Files**
-  **Use External Emojis**
-  **Use Application Commands** (for slash commands)

Be sure to grant these when inviting the bot or adjusting channel-specific permissions.

---

##  Slash Commands

### `/setchannel <#channel>`
Sets the default channel where the bot will send updates. Only one channel per server can be set.

### `/updatechannel <#channel>`
Changes the default channel where the bot will send updates. Only one channel per server can be set.

### `/add <profile_name>`
Adds a Letterboxd user to the tracking list for the server. Up to 10 users can be tracked per server.

### `/remove <profile_name>`
Removes a user from the tracking list.

### `/list`
Displays the list of currently tracked Letterboxd users in the server.

### `/favorites <profile_name>`
Post the Letterboxd users' favorite films listed on their profile page.

### `/help`
Displays a short help message outlining the commands and their use.

---

##  Task Scheduling

The bot runs a background task every 30 minutes (Subject to change based on server load) to check for new diary entries and will post new activity if found.

---

## Disclaimer

### This bot is unofficial and not affiliated with Letterboxd in any way. It is a free tool intended for community use and does not monetize or interact with Letterboxd's API directly.

### Please Note:
- This bot has no guarantee of uptime or continued support
- It may be taken down or discontinued at any time due to maintenance, cost, or project deprecation.
- This will be updated when/if it is taken down

---

## Future Updates

### Future updates currently planned. No guarantee they are added

- `/watchlistpick <profile_name>` - grabs a users' watchlist and randomly selects one film from the list.
- Movie images. Currently images cannot be scraped from Letterboxd, will look into getting them some other way to include in posts.
- `/film <film_name>` - grabs the info such as name, year, synopsis, director, or actors for a specified film.

---

##  Notes

- The bot can only be used in the channel specified with `/setchannel`.
- It only tracks users' **Diary** activity, not other types of interactions (e.g., likes or reviews outside of diary entries).
- The `/add` command verifies that the Letterboxd profile exists. Make sure the profile name matches the profiles full name, not a display name (Can verify based on the url when viewing their profile).
- Dockerfile was initialized, but never finished.

---





