import discord, logging, psycopg2, asyncio, logging, requests
from discord.ext import commands, tasks
from discord import app_commands, Embed, TextChannel
from config import token, db_password, api_key, db_port, MAX_USER_COUNT_PER_SERVER, TASK_LOOP_INTERVAL
from scraping import firstScrape, diaryScrape, favoriteFilmsScrape, profileImageOnReady
from helper import build_embed_message, update_last_entry, check_channel


def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="discordbotdb",
        user="postgres",
        password=db_password,
        port=db_port
    )

# Logger setup for all custom code logging
my_logger = logging.getLogger("mybot")
my_logger.setLevel(logging.DEBUG)

handler = logging.FileHandler("mybot.log", mode="w")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

my_logger.addHandler(handler)
my_logger.propagate = False

# Logger setup for only discord api logging
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    my_logger.info(f"We are ready to go in, {bot.user.name}")
    current_guild_ids = {guild.id for guild in bot.guilds}
    conn = None
    cur = None

    try:        # Checks if servers are registered in the database, incase on_guild_join() failed to initialize 
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT server_id FROM discord_servers")
        results = cur.fetchall()
        stored_ids = {row[0] for row in results}

        missing_ids = current_guild_ids - stored_ids

        for guild in bot.guilds:
            if guild.id in missing_ids:
                try:
                    insert_query = """INSERT INTO discord_servers (server_id, user_count, updated_at)
                                    VALUES (%s, %s, now())
                                    ON CONFLICT (server_id) DO NOTHING;"""
                    cur.execute(insert_query, (guild.id, 0))
                    my_logger.info(f"Added missed guild {guild.name} ({guild.id}) to database.")
                except psycopg2.Error as e:
                    my_logger.error(f"Failed to insert guild {guild.name} ({guild.id}): {e}")
                else:
                    conn.commit()

        # This section is to add profile urls to the database for users that were added before
        # I had added the 'profile_url' column to the database.
        # Any users added after this change will be added correctly in the /add command section
        # This should only need to be ran once after implementation, will possibly delete/comment out after that.
        # cur.execute("SELECT profile_name FROM diary_users")
        # results = cur.fetchall()
        # for result in results: 
        #     user = result[0] 
        #     profile_url = (f"https://letterboxd.com/{user}/")
        #     try:
        #         update_query = """UPDATE diary_users 
        #                         SET updated_at = now(), profile_url = %s
        #                         WHERE profile_name = %s"""
        #         cur.execute(update_query, (profile_url, user))
        #     except psycopg2.Error as e:
        #         my_logger.error(f"Failed to insert profile_url for {user}: {e}")
        #     else:
        #         conn.commit()

        # This section is to add profile images to the database for users that were added before
        # I had added the 'profile_image' column to the database.
        # Any users added after this change will be added correctly in the /add command section
        # This should only need to be ran once after implementation, will possibly delete/comment out after that.
        # cur.execute("SELECT profile_name FROM diary_users")
        # results = cur.fetchall()
        # for result in results: 
        #     user = result[0] 
        #     profile_image = profileImageOnReady(user)
        #     if profile_image:
        #         try:
        #             update_query = """UPDATE diary_users 
        #                             SET updated_at = now(), profile_image = %s
        #                             WHERE profile_name = %s"""
        #             cur.execute(update_query, (profile_image, user))
        #         except psycopg2.Error as e:
        #             my_logger.error(f"Failed to insert profile_image for {user}: {e}")
        #         else:
        #             conn.commit()
        #     else:
        #         my_logger.error(f"Failed to grab profile image for {user}")

        synced = await bot.tree.sync()
        my_logger.info(f"Synced {len(synced)} command(s)")
        if not diary_loop.is_running():
            diary_loop.start()
    
    except Exception as e:
        my_logger.error(f"Error in on_ready event: {e}")

    finally:
        if cur: cur.close()
        if conn: conn.close()


# Initialize server info into database when joining a new server
# Can fail if the bot joins a server while offline, on_ready() is used as a backup in this scenario
@bot.event
async def on_guild_join(guild):
    guild_id = guild.id
    conn = None
    cur = None
    my_logger.info(f"Joined new server: {guild.name} - {guild_id}")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = """INSERT INTO discord_servers (server_id, user_count, updated_at)
        VALUES (%s, %s, now())
        ON CONFLICT (server_id) DO NOTHING;"""
        cur.execute(query, (guild_id, 0))
        conn.commit()

    except psycopg2.Error as e:
        my_logger.error(f"Failed to add server {guild.name}, {guild_id} to database: {e}")

    finally:
        if cur: cur.close()
        if conn: conn.close()


# Deletes server info in database with cascading to other data tables when removed from a server
@bot.event
async def on_guild_remove(guild):
    guild_id = guild.id
    conn = None
    cur = None
    my_logger.info(f"Removed from server: {guild.name} - {guild_id}")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        delete_query = """DELETE FROM discord_servers
        WHERE server_id = %s;"""
        cur.execute(delete_query, (guild_id,))
        conn.commit()
    
    except psycopg2.Error as e:
        my_logger.error(f"Failed to remove server {guild.name}, {guild_id} to database: {e}")

    finally:
        if cur: cur.close()
        if conn: conn.close()


@bot.tree.command(name="help", description="List all bot commands and their descriptions.")
async def help_command(interaction: discord.Interaction):
    embed = Embed(
        title="🎬 Letterboxd Bot Help",
        description="Here's a list of commands you can use with this bot:",
        color=0x1DB954
    )

    embed.add_field(
        name="`/add <username>`",
        value=f"Add a Letterboxd profile to this server's diary list (max {MAX_USER_COUNT_PER_SERVER} users).",
        inline=False
    )

    embed.add_field(
        name="`/remove <username>`",
        value="Remove a Letterboxd profile from the server's diary list.",
        inline=False
    )

    embed.add_field(
        name="`/list`",
        value="List all usernames currently being tracked in this server.",
        inline=False
    )

    embed.add_field(
        name="`/setchannel <#channel>`",
        value="Set the default text channel where the bot can send messages and accept commands.",
        inline=False
    )

    embed.add_field(
        name="`/updatechannel <#channel>`",
        value="Change the default text channel where the bot can send messages and accept commands.",
        inline=False
    )

    embed.add_field(
        name="`/favorites <username>`",
        value="List a Letterboxd profiles favorite films.",
        inline=False
    )

    embed.add_field(
        name="`/film <filmname>`",
        value="Post a film's data. Film name must be spelt correctly, include accents but not special characters.",
        inline=False
    )

    embed.add_field(
        name="`/help`",
        value="Display this help message.",
        inline=False
    )

    embed.set_footer(text="Note: Bot commands will only work in the configured channel.")

    await interaction.response.send_message(embed=embed, ephemeral=True)


# Perfroms multiple checks when adding a user to the bot's list
# Confirms the entered username is a valid Letterboxd profile and the profile exists
# If exist, stores it into the database, and sends the profile's most recent entry in chat
@bot.tree.command(name="add", description="Add a user")
@app_commands.describe(arg = "Username:")
async def add(interaction: discord.Interaction, arg: str):
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id
    conn = None
    cur = None
    profile_name = arg.lower()
    profile_url = f"https://letterboxd.com/{profile_name}/"
    
    channel_check, stored_channel_id = check_channel(channel_id, guild_id)
    if channel_check == "no_exist":
        await interaction.response.send_message("❗ Bot is not configured for this server yet. Use `/setchannel` first.", ephemeral=True)
        return
    elif channel_check == "no_match":
        await interaction.response.send_message(f"❌ Bot commands must be used in <#{stored_channel_id}>.", ephemeral=True)
        return
    
    if len(profile_name) > 15 or len(profile_name) < 2:
        await interaction.response.send_message(f"❌ Failed to get {profile_name} Letterboxd data, make sure input is a valid profile.")
        return
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        get_query = """SELECT user_count
        FROM discord_servers
        WHERE server_id = %s"""
        cur.execute(get_query, (guild_id,))
        
        users_count = cur.fetchone()
        if users_count[0] >= MAX_USER_COUNT_PER_SERVER:
            cur.close()
            conn.close()
            await interaction.response.send_message(f"❌ Failed to add {profile_name} to list. List exceeds maximum limit ({MAX_USER_COUNT_PER_SERVER}). First remove a user with `/remove`")
            return
        
        insert_query = """INSERT INTO diary_users (profile_name, server_id, updated_at, profile_url)
        VALUES (%s, %s, now(), %s)
        ON CONFLICT (profile_name, server_id) DO NOTHING;"""
        cur.execute(insert_query, (profile_name, guild_id, profile_url))

        if cur.rowcount > 0:    # Checks if the insert_query execute before updating
            result = firstScrape(profile_name)
            if not result or result[0] is False:
                conn.rollback()
                cur.close()
                conn.close()
                await interaction.response.send_message(f"❌ Failed to get {profile_name} Letterboxd data, make sure input is a valid profile.")
                return
            else:
                if result[0] is True:
                    profile_image = result[7]
                    embed, film_title = build_embed_message(result, profile_url, profile_name, profile_image)
                else:
                    film_title = result
            try:
                server_update_query = """UPDATE discord_servers
                SET user_count = user_count + 1, updated_at = now()
                WHERE server_id = %s;"""
                cur.execute(server_update_query, (guild_id,))
                user_update_query = """UPDATE diary_users
                SET last_entry = %s, updated_at = now(), profile_image = %s
                WHERE profile_name = %s AND server_id = %s"""
                cur.execute(user_update_query, (film_title, profile_image, profile_name, guild_id))
            except psycopg2.Error as e:
                my_logger.error(f"Error during /add transaction: {e}")
                conn.rollback()
            else:
                conn.commit()

            if film_title == "no_entry":
                await interaction.response.send_message(f"✅ {arg} has been added to the list\n{arg} has no current entries.")
            else:
                await interaction.response.send_message(f"✅ {arg} has been added to the list\n{arg}'s most recent entry:\n",embed=embed[0])
        else:
            await interaction.response.send_message(f"{arg} is already in the list")

    except Exception as e:
        my_logger.error(f"Error in /add command: {e}")
        await interaction.response.send_message("❌ Failed to add user: " + arg, ephemeral= True)

    finally:
        if cur: cur.close()
        if conn: conn.close()

# Remove a user from the list/database if it exist
@bot.tree.command(name="remove", description="Remove a user")
@app_commands.describe(arg="Username: ")
async def remove(interaction: discord.interactions, arg: str):
    guild_id = interaction.guild_id
    channel_id = interaction.channel.id
    conn = None
    cur = None
    profile_name = arg.lower()

    channel_check, stored_channel_id = check_channel(channel_id, guild_id)
    if channel_check == "no_exist":
        await interaction.response.send_message("❗ Bot is not configured for this server yet. Use `/setchannel` first.", ephemeral=True)
        return
    elif channel_check == "no_match":
        await interaction.response.send_message(f"❌ Bot commands must be used in <#{stored_channel_id}>.", ephemeral=True)
        return

    if len(profile_name) > 15 or len(profile_name) < 2:
        await interaction.response.send_message(f"{arg} is not in the list")
        return
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        delete_query = """DELETE FROM diary_users
        WHERE profile_name = %s AND server_id = %s"""
        cur.execute(delete_query, (profile_name, guild_id))

        if cur.rowcount > 0:    # Checks if the insert_query execute before updating
            try:
                update_query = """UPDATE discord_servers SET
                user_count = user_count - 1, updated_at = now()
                WHERE server_id = %s;"""
                cur.execute(update_query, (guild_id,))
            except psycopg2.Error as e:
                my_logger.error(f"Error in /remove transaction: {e}")
                conn.rollback()
            else:
                conn.commit()
            finally:
                await interaction.response.send_message(f"✅ {arg} has been removed from the list")
        else:
            await interaction.response.send_message(f"{arg} is not in the list")

    except Exception as e:
        my_logger.error(f"Error in /remove: {e}")
        await interaction.response.send_message("❌ An error occurred while removing the user.", ephemeral=True)

    finally:
        if cur: cur.close()
        if conn: conn.close()

# Prints all users in the database for that server to the channel chat
@bot.tree.command(name="list", description="List all users")
@app_commands.describe()
async def list(interaction: discord.interactions):
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id
    conn = None
    cur = None
    user_list = []

    channel_check, stored_channel_id = check_channel(channel_id, guild_id)
    if channel_check == "no_exist":
        await interaction.response.send_message("❗ Bot is not configured for this server yet. Use `/setchannel` first.", ephemeral=True)
        return
    elif channel_check == "no_match":
        await interaction.response.send_message(f"❌ Bot commands must be used in <#{stored_channel_id}>.", ephemeral=True)
        return

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        get_query = """SELECT profile_name, profile_url
        FROM diary_users
        WHERE server_id = %s"""
        cur.execute(get_query, (guild_id,))
        users = cur.fetchall()
        count_query = """SELECT COUNT(profile_name)
        FROM diary_users
        WHERE server_id = %s"""
        cur.execute(count_query, (guild_id,))
        users_count = cur.fetchone()

        if not users:
            await interaction.response.send_message("No users have been added yet. Use `/add` to add users.")
        else:
            user_list = []
            for user in users:
                user_list.append(f"• [{user[0]}](<{user[1]}>)")
            join_user_list = "\n".join(user_list)

            embed = Embed(
            title=f"Users In This Server ({users_count[0]}/{MAX_USER_COUNT_PER_SERVER})",
            description=join_user_list,
            color=0x1DB954
            )
        
            await interaction.response.send_message(embed = embed)
    except Exception as e:
        my_logger.error(f"Error printing list in: {e}")
        await interaction.response.send_message("❌ An error occurred while retrieving user list.", ephemeral=True)

    finally:
        if cur: cur.close()
        if conn: conn.close()

# Set the default channel for the bot's commands in the server
# Stores channel id in the database
@bot.tree.command(name="setchannel", description="Set the default channel (Text)")
@app_commands.describe(arg="Channel name")
async def set_channel(interaction: discord.interactions, arg: TextChannel):
    guild_id = interaction.guild_id
    channel_id = arg.id
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        check_query = """SELECT 1 FROM server_channels WHERE server_id = %s"""
        cur.execute(check_query, (guild_id,))
        exists = cur.fetchone()
        if exists:
            await interaction.response.send_message("❌ A default channel is already set for this server. Use `/updatechannel` to change it.", ephemeral=True)
        else:
            insert_query = """INSERT INTO server_channels (channel_id, server_id, updated_at)
            VALUES (%s, %s, now())
            ON CONFLICT (channel_id, server_id) DO NOTHING"""
            cur.execute(insert_query, (channel_id, guild_id))
            if cur.rowcount > 0:
                conn.commit()
                await interaction.response.send_message(f"✅ {arg} has been set as the default channel.")
            else:
                conn.rollback()
                await interaction.response.send_message(f"{arg} is already set as the default channel.")
        
    except Exception as e:
        my_logger.error(f"Error setting channel in {guild_id}: {e}")
        await interaction.response.send_message(f"❌ Failed to set {arg} as default channel.")
    
    finally:
        if cur: cur.close()
        if conn: conn.close()

# Updates the stored channel to a different one
@bot.tree.command(name="updatechannel", description="Change the default channel (Text)")
@app_commands.describe(arg="Channel name")
async def update_channel(interaction: discord.interactions, arg: TextChannel):
    guild_id = interaction.guild_id
    channel_id = arg.id
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        update_query = """UPDATE server_channels
        SET channel_id = %s, updated_at = now()
        WHERE server_id = %s"""
        cur.execute(update_query, (channel_id, guild_id))

        if cur.rowcount > 0:
            conn.commit()
            await interaction.response.send_message(f"✅ Default channel has been updated to {arg}")
        else:
            conn.rollback()
            await interaction.response.send_message(f"No channel is set currently. Use `/setchannel` first.", ephemeral=True)

    except Exception as e:
        my_logger.error(f"Error updating channel in {guild_id}: {e}")
        await interaction.response.send_message(f"❌ Failed to update default channel to {arg}.")

    finally:
        if cur: cur.close()
        if conn: conn.close()

# Grabs the users' favorite films setup on their profile page
@bot.tree.command(name="favorites", description="Grab users favorite films")
@app_commands.describe(arg="Username: ")
async def favorite_films(interaction: discord.interactions, arg: str):
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id
    profile_name = arg.lower()
    profile_url = f"https://letterboxd.com/{profile_name}/"

    url = f"http://www.omdbapi.com/?apikey={api_key}&"
    headers = {
        "X-API-Key": api_key,
        "Accept": "applications/json"
    }

    channel_check, stored_channel_id = check_channel(channel_id, guild_id)
    if channel_check == "no_exist":
        await interaction.response.send_message("❗ Bot is not configured for this server yet. Use `/setchannel` first.", ephemeral=True)
        return
    elif channel_check == "no_match":
        await interaction.response.send_message(f"❌ Bot commands must be used in <#{stored_channel_id}>.", ephemeral=True)
        return

    try:
        results = favoriteFilmsScrape(arg)

        if results == "No favorites":
            await interaction.response.send_message(f"{arg} currently has no favorite films.")
            return
        elif not results:
            await interaction.response.send_message("Failed to find users favorite films. Check spelling or try again later.", ephemeral=True)
            return
        
        titles = []
        years = []
        movie_posters = []
        movie_titles = []
        for movie in results:
            split_movie = movie.split('(')
            title = split_movie[0].strip()
            titles.append(title)
            year = split_movie[1].strip(')')
            years.append(year)

        try:    
                for i in range(len(titles)):
                    params = {
                        "t": titles[i],
                        "y": years[i],
                        "type": "movie"
                    }
                    response = requests.get(url, headers=headers, params=params)
                    data = response.json()

                    if response.ok:
                        movie_posters.append(data["Poster"])
                    else:
                        movie_titles.append(f"{titles[i]} ({years[i]})")
                        my_logger.error(f"'/favorite' API call response returned false. Status Code: {response.status_code}")
                        try:
                            error_json = response.json()
                            my_logger.error(f"Error Message: {error_json.get("message", "No message provided.")}")
                        except ValueError:
                            my_logger.error(f"Raw Error: {response.text}")   

        except Exception as e:
            my_logger.error(f"Error in '/favorite' API call: {e}")
            for i in range(len(titles)):
                movie_titles.append(f"{titles[i]} ({years[i]})")
        
        embeds = []
        for poster in movie_posters:
            embed = Embed(title=f"{arg}'s Favorite Films", url=profile_url, color=0x1DB954).set_image(url=poster)
            embeds.append(embed)

        # Fallback if api calls failed, send message with only titles+years and no images/posters
        if movie_titles:
            description = "\n".join(f"• {title}" for title in movie_titles)
            title_embed = Embed(
                title=f"{arg}'s Favorite Films",
                url=profile_url,
                description=description,
                color=0x1DB954
            )
            embeds.append(title_embed)



        # description = "\n".join(f"• {title}" for title in results)
        # embed = Embed(
        #     title=f"{arg}'s Favorite Films",
        #     description=description,
        #     color=0x1DB954
        # )
        
        await interaction.response.send_message(embeds=embeds)

    except Exception as e:
        my_logger.error(f"Error in /favorites: {e}")
        await interaction.response.send_message("Failed to find users favorite films. Check spelling or try again later.", ephemeral=True)


@bot.tree.command(name="film", description="Get a film's info")
@app_commands.describe(arg="FilmName: ")
async def film_search(interaction: discord.interactions, arg: str):
    url = f"http://www.omdbapi.com/?apikey={api_key}&"
    headers = {
        "X-API-Key": api_key,
        "Accept": "applications/json"
    }
    params = {
        "t": arg,
        "type": "movie"
    }

    # Currently not restricing this command to the set channel
    # since I would like to be able to use this command anywhere.
    # May change later
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id

    channel_check, stored_channel_id = check_channel(channel_id, guild_id)
    if channel_check == "no_exist":
        await interaction.response.send_message("❗ Bot is not configured for this server yet. Use `/setchannel` first.", ephemeral=True)
        return
    elif channel_check == "no_match":
        await interaction.response.send_message(f"❌ Bot commands must be used in <#{stored_channel_id}>.", ephemeral=True)
        return

    try:
        response = requests.get(url, headers=headers, params=params)
        #print(response.json())
        data = response.json()

        if response.ok:
            embed = Embed(
                title=f"{data["Title"]} ({data["Year"]})",
                description=data["Plot"],
                color=0x1DB954
            )

            embed.set_thumbnail(url=data["Poster"])

            embed.add_field(name="Runtime", value=data["Runtime"], inline=True)
            embed.add_field(name="Genre", value=data["Genre"], inline=True)
            embed.add_field(name="Rated", value=data["Rated"], inline=True)
            embed.add_field(name="Director", value=data["Director"], inline=True)
            embed.add_field(name="Main Cast", value=data["Actors"], inline=True)

            embed.set_footer(text=f"IMDb Rating: {data['imdbRating']}")
            
            await interaction.response.send_message(embed=embed)
        else:
            my_logger.error(f"'/film' API call response returned false. Status Code: {response.status_code}")
            try:
                error_json = response.json()
                my_logger.error(f"Error Message: {error_json.get("message", "No message provided.")}")
            except ValueError:
                my_logger.error(f"Raw Error: {response.text}")
            finally:
                await interaction.response.send_message("Failed to get film data. Check spelling or try again later.", ephemeral=True)

    except Exception as e:
        my_logger.error(f"Error in /film: {e}")
        await interaction.response.send_message("Failed to get film data. Check spelling or try again later.", ephemeral=True)


### WORK IN PROGRESS ### Might not be possible
# @bot.tree.command(name="watchlistpick", description="Pick random film from watchlist")
# @app_commands.describe(arg="Username: ")
# async def watchlist_pick(interaction: discord.interactions, arg: str):
#     guild_id = interaction.guild.id
#     channel_id = interaction.channel.id

#     channel_check, stored_channel_id = check_channel(channel_id, guild_id)
#     if channel_check == "no_exist":
#         await interaction.response.send_message("❗ Bot is not configured for this server yet. Use `/setchannel` first.", ephemeral=True)
#         return
#     elif channel_check == "no_match":
#         await interaction.response.send_message(f"❌ Bot commands must be used in <#{stored_channel_id}>.", ephemeral=True)
#         return
    
#     #results = await asyncio.to_thread(watchlistScrape, arg)

#     await interaction.response.send_message("This command is currently a work in progress")

# Task loop set to perform every set interval
# Grabs all users in the database and loops through each one to scrape their diary info
# Scraping function is setup to scrape the 5 most recent entries, but will stop early if the stored 'last_entry'
# is reached in the diary, so it will only return new entries compared to the 'last_entry'
# Then will call update_last_entry() to update the 'last_entry' with the new title
@tasks.loop(minutes=TASK_LOOP_INTERVAL)
async def diary_loop():
    my_logger.info("Task loop has began.")

    no_entry_users = {}
    new_entry_users = {}
    channel_cache = {}

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""SELECT sc.channel_id, sc.server_id, du.profile_name, du.last_entry, du.profile_url, du.profile_image
                    FROM server_channels sc
                    JOIN diary_users du ON sc.server_id = du.server_id""")
        results = cur.fetchall()
        cur.close()
        conn.close()

        for channel_id, server_id, profile_name, last_entry, profile_url, profile_image in results:
            if profile_name in no_entry_users:
                continue
            
            if channel_id in channel_cache:
                channel = channel_cache[channel_id]
            else:
                try:
                    channel = await bot.fetch_channel(channel_id)
                    channel_cache[channel_id] = channel
                except discord.NotFound:
                    my_logger.warning(f"Channel {channel_id} not found.")
                    continue
                except discord.Forbidden:
                    my_logger.warning(f"Missing permissions to access channel {channel_id} of server {server_id}")
                    continue
                except Exception as e:
                    my_logger.error(f"Error fetching channel {channel_id}: {e}")
                    continue
            
            if not isinstance(channel, discord.TextChannel):
                my_logger.warning(f"Channel {channel_id} is not a text channel.")
                continue

            if profile_name not in new_entry_users:
                await asyncio.sleep(1.0)  # To help with rate limiting issues, only when scraping

                try:
                    result = await asyncio.to_thread(diaryScrape, profile_name, last_entry)
                    if not result[0]:
                        no_entry_users[profile_name] = server_id
                        continue

                    embed, film_title = await asyncio.to_thread(build_embed_message, result, profile_url, profile_name, profile_image)
                    await asyncio.to_thread(update_last_entry, server_id, profile_name, film_title)
                    new_entry_users[profile_name] = (embed, film_title)
              
                    for message in embed:
                        await channel.send(embed=message)
                        await asyncio.sleep(0.5)

                except discord.NotFound:
                    my_logger.warning(f"Channel {channel_id} not found.")
                except discord.Forbidden:
                    my_logger.warning(f"Missing permissions to send in channel {channel_id} of server {server_id}")
                except Exception as e:
                    my_logger.error(f"Error sending Task Loop message to {channel_id}, {profile_name}: {e}")
            else:
                try:
                    embed, film_title = new_entry_users[profile_name]
                    await asyncio.to_thread(update_last_entry, server_id, profile_name, film_title)
                        
                    for message in embed:
                        await channel.send(embed=message)
                        await asyncio.sleep(0.5)

                except discord.NotFound:
                    my_logger.warning(f"Channel {channel_id} not found.")
                except discord.Forbidden:
                    my_logger.warning(f"Missing permissions to send in channel {channel_id} of server {server_id}")
                except Exception as e:
                    my_logger.error(f"Error sending Task Loop message to {channel_id}, {profile_name}: {e}")

    except Exception as e:
        my_logger.error(f"Scheduled task failed: {e}")

    my_logger.info("Task loop has finished.")
    my_logger.debug(f"Users with no new entries this loop: {no_entry_users.keys()}")
    my_logger.debug(f"Users with new entries this loop: {new_entry_users.keys()}")


@diary_loop.before_loop
async def before_diary_loop():
    my_logger.info("Waiting until bot is ready for task startup")
    await bot.wait_until_ready()

bot.run(token, log_handler=handler, log_level=logging.DEBUG)