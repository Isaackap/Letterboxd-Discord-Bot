import discord, os, logging, psycopg2, math
from discord.ext import commands, tasks
from discord import app_commands, Embed, TextChannel
from dotenv import load_dotenv
from scraping import firstScrape, diaryScrape

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
db_password = os.getenv("DB_PASSWORD")

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="discordbotdb",
        user="postgres",
        password=db_password,
        port='5433'
    )

def build_embed_message(data):
    _, film_title, film_release, film_rating, film_review = data
    embed_list = []

    if isinstance(film_title, str):
        film_title = [film_title]
        film_release = [film_release]
        film_rating = [film_rating]
        film_review = [film_review]

    latest_entry = film_title[0]

    for i in range(len(film_title)):
        title = film_title[i]
        release = film_release[i]
        rating = film_rating[i]
        review = film_review[i]

        if rating:
            try:
                float_rating = float(rating) / 2
                stars = int(float_rating)
                half_star = float_rating % 1 >= 0.5
                
                string_rating = "<:47925letterboxd1star:1400770061404340234>" * stars
                if half_star:
                    string_rating += "<:79899letterboxdhalfstar:1400770001237184575>"

                rating_embeded = f"Rating: {string_rating}"
            except ValueError:
                rating_embeded = "*Invalid rating format.*"
        else:
            rating_embeded = "*No rating provided.*"

        embed = Embed(
            title=f"{title} ({release})",
            description=rating_embeded,
            color=0x1DB954
        )

        embed.add_field(
            name="Review",
            value=review if review else "*No review provided.*",
            inline=False
        )
        
        embed_list.append(embed)
    return embed_list, latest_entry

def check_channel(channel_id, guild_id):
    conn = get_db_connection()
    cur = conn.cursor()
    select_query = """SELECT channel_id
    FROM server_channels
    WHERE server_id = %s"""
    cur.execute(select_query, (guild_id,))
    channel = cur.fetchone()
    cur.close()
    conn.close()

    if not channel:
        return "no_exist", None
    
    stored_channel_id = channel[0]
    if  channel_id != stored_channel_id:
        return "no_match", stored_channel_id
    
    return "ok", stored_channel_id


handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
        if not diary_loop.is_running():
            diary_loop.start()
    except Exception as e:
        print(e)


@bot.event
async def on_guild_join(guild):
    guild_id = guild.id
    print(f"Joined new server: {guild.name} - {guild_id}")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = """INSERT INTO discord_servers (server_id, user_count, updated_at)
        VALUES (%s, %s, now())
        ON CONFLICT (server_id) DO NOTHING;"""
        cur.execute(query, (guild_id, 0))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Failed to add server {guild.name}, {guild_id} to database",e)


@bot.event
async def on_guild_remove(guild):
    guild_id = guild.id
    print(f"Removed from server: {guild.name} - {guild_id}")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        delete_query = """DELETE FROM discord_servers
        WHERE server_id = %s;"""
        cur.execute(delete_query, (guild_id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Failed to remove server {guild.name}, {guild_id} to database",e)


@bot.tree.command(name="help", description="List all bot commands and their descriptions.")
async def help_command(interaction: discord.Interaction):
    embed = Embed(
        title="🎬 Letterboxd Bot Help",
        description="Here's a list of commands you can use with this bot:",
        color=0x1DB954  # Letterboxd green
    )

    embed.add_field(
        name="`/add <username>`",
        value="Add a Letterboxd profile to this server's diary list (max 10 users).",
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
        name="`/help`",
        value="Display this help message.",
        inline=False
    )

    embed.set_footer(text="Note: Bot commands will only work in the configured channel.")

    await interaction.response.send_message(embed=embed, ephemeral=True)



@bot.tree.command(name="add", description="Add a user")
@app_commands.describe(arg = "Username:")
async def add(interaction: discord.Interaction, arg: str):
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id
    profile_name = arg.lower()
    
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
        get_query = """SELECT COUNT(profile_name)
        FROM diary_users
        WHERE server_id = %s"""
        cur.execute(get_query, (guild_id,))
        
        users_count = cur.fetchone()
        if users_count[0] >= 10:
            await interaction.response.send_message(f"❌ Failed to add {profile_name} to list. List exceeds maximum limit (10). First remove a user with `/remove`")
            return
        
        insert_query = """INSERT INTO diary_users (profile_name, server_id, updated_at)
        VALUES (%s, %s, now())
        ON CONFLICT (profile_name, server_id) DO NOTHING;"""
        cur.execute(insert_query, (profile_name, guild_id))

        if cur.rowcount > 0:    # Checks if the insert_query execute before updating
            result = firstScrape(profile_name)
            if not result or result[0] is False:
                conn.rollback()
                await interaction.response.send_message(f"❌ Failed to get {profile_name} Letterboxd data, make sure input is a valid profile.")
                cur.close()
                conn.close()
                return
            else:
                if result[0] is True:
                    embed, film_title = build_embed_message(result)
                else:
                    film_title = result

            server_update_query = """UPDATE discord_servers
            SET user_count = user_count + 1, updated_at = now()
            WHERE server_id = %s;"""
            cur.execute(server_update_query, (guild_id,))
            user_update_query = """UPDATE diary_users
            SET last_entry = %s
            WHERE profile_name = %s AND server_id = %s"""
            cur.execute(user_update_query, (film_title, profile_name, guild_id))
            conn.commit()
            if film_title == "no_entry":
                await interaction.response.send_message(f"✅ {arg} has been added to the list\n{arg} has no current entries.")
            else:
                await interaction.response.send_message(f"✅ {arg} has been added to the list\n{arg}'s most recent entry:\n",embed=embed[0])
        else:
            await interaction.response.send_message(f"{arg} is already in the list")
        cur.close()
        conn.close()

    except Exception as e:
        print("Error in /add command: ", e)
        await interaction.response.send_message("❌ Failed to add user: " + arg, ephemeral= True)


@bot.tree.command(name="remove", description="Remove a user")
@app_commands.describe(arg="Username: ")
async def remove(interaction: discord.interactions, arg: str):
    guild_id = interaction.guild_id
    channel_id = interaction.channel.id
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
            update_query = """UPDATE discord_servers SET
            user_count = user_count - 1, updated_at = now()
            WHERE server_id = %s;"""
            cur.execute(update_query, (guild_id,))
            conn.commit()
            await interaction.response.send_message(f"✅ {arg} has been removed from the list")
        else:
            await interaction.response.send_message(f"{arg} is not in the list")

        cur.close()
        conn.close()
    except Exception as e:
        print("Error in /remove: ", e)
        await interaction.response.send_message("❌ An error occurred while removing the user.", ephemeral=True)


@bot.tree.command(name="list", description="List all users")
@app_commands.describe()
async def list(interaction: discord.interactions):
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id
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
        get_query = """SELECT profile_name
        FROM diary_users
        WHERE server_id = %s"""
        cur.execute(get_query, (guild_id,))
        users = cur.fetchall()
        count_query = """SELECT COUNT(profile_name)
        FROM diary_users
        WHERE server_id = %s"""
        cur.execute(count_query, (guild_id,))
        users_count = cur.fetchone()
        cur.close()
        conn.close()

        if not users:
            await interaction.response.send_message("No users have been added yet. Use `/add` to add users.")
        else:
            user_list = "\n".join(user[0] for user in users)
            await interaction.response.send_message(f"**Users in this server ({users_count[0]}):**\n{user_list}")
    except Exception as e:
        print("Error printing list in ", e)
        await interaction.response.send_message("❌ An error occurred while retrieving user list.", ephemeral=True)


@bot.tree.command(name="setchannel", description="Set the default channel (Text)")
@app_commands.describe(arg="Channel name")
async def set_channel(interaction: discord.interactions, arg: TextChannel):
    guild_id = interaction.guild_id
    channel_id = arg.id
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
                await interaction.response.send_message(f"{arg} is already set as the default channel.")
        cur.close()
        conn.close()
    except Exception as e:
        print("Error setting channel in ", guild_id, e)
        await interaction.response.send_message(f"❌ Failed to set {arg} as default channel.")


@bot.tree.command(name="updatechannel", description="Change the default channel (Text)")
@app_commands.describe(arg="Channel name")
async def update_channel(interaction: discord.interactions, arg: TextChannel):
    guild_id = interaction.guild_id
    channel_id = arg.id
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        update_query = """UPDATE server_channels
        SET channel_id = %s, updated_at = now()
        WHERE server_id = %s"""
        cur.execute(update_query, (channel_id, guild_id))

        if cur.rowcount > 0:
            conn.commit()
            await interaction.response.send_message(f"✅ Default channel has be updated to {arg}")
        else:
            await interaction.response.send_message(f"No channel is set currently. Use `/setchannel` first.", ephemeral=True)

        cur.close()
        conn.close()
    except Exception as e:
        print("Error updating channel in ", guild_id, e)
        await interaction.response.send_message(f"❌ Failed to update default channel to {arg}.")

### WORK IN PROGRESS ###
@bot.tree.command(name="watchlistpick", description="Pick random film from watchlist")
@app_commands.describe(arg="Username: ")
async def watchlist_pick(interaction: discord.interactions, arg: str):
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id

    channel_check, stored_channel_id = check_channel(channel_id, guild_id)
    if channel_check == "no_exist":
        await interaction.response.send_message("❗ Bot is not configured for this server yet. Use `/setchannel` first.", ephemeral=True)
        return
    elif channel_check == "no_match":
        await interaction.response.send_message(f"❌ Bot commands must be used in <#{stored_channel_id}>.", ephemeral=True)
        return

    await interaction.response.send_message("This command is currently a work in progress")


@tasks.loop(minutes=20)
async def diary_loop():
    print("Task loop has began")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""SELECT sc.channel_id, sc.server_id, du.profile_name, du.last_entry
                    FROM server_channels sc
                    JOIN diary_users du ON sc.server_id = du.server_id""")
        results = cur.fetchall()

        for channel_id, server_id, profile_name, last_entry in results:
            try:
                channel = await bot.fetch_channel(channel_id)
                if isinstance(channel, discord.TextChannel):
                    result = diaryScrape(profile_name, last_entry)
                    if not result or result[0] is False:
                        continue
                    else:
                        embed, film_title = build_embed_message(result)
                        user_update_query = """UPDATE diary_users
                        SET last_entry = %s
                        WHERE profile_name = %s AND server_id = %s"""
                        cur.execute(user_update_query, (film_title, profile_name, server_id))
                        conn.commit()

                        await channel.send(f"{profile_name}'s New Diary Entries:")
                        for message in embed:
                            await channel.send(embed=message)
            except discord.NotFound:
                print(f"Channel {channel_id} not found.")
            except discord.Forbidden:
                print(f"Missing permissions to send in channel {channel_id} of server {server_id}")
            except Exception as e:
                print(f"Error sending message to {channel_id}: {e}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Scheduled task failed: {e}")


@diary_loop.before_loop
async def before_diary_loop():
    print("Waiting until bot is ready for task startup")
    await bot.wait_until_ready()

bot.run(token, log_handler=handler, log_level=logging.DEBUG)