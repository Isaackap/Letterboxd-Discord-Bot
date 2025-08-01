import discord, os, logging, psycopg2, math
from discord.ext import commands
from discord import app_commands, Embed
from dotenv import load_dotenv
from scraping import firstScrape

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


    

@bot.tree.command(name="add", description="Add a user")
@app_commands.describe(arg = "Username:")
async def add(interaction: discord.Interaction, arg: str):
    guild_id = interaction.guild.id
    profile_name = arg.lower()
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        insert_query = """INSERT INTO diary_users (profile_name, server_id, updated_at)
        VALUES (%s, %s, now())
        ON CONFLICT (profile_name, server_id) DO NOTHING;"""
        cur.execute(insert_query, (profile_name, guild_id))

        if cur.rowcount > 0:    # Checks if the insert_query execute before updating
            result = firstScrape(profile_name)
            if not result or result[0] is False:
                conn.rollback()
                await interaction.response.send_message(f"Failed to get {profile_name} Letterboxd data, make sure input is a valid profile.")
                cur.close()
                conn.close()
                return
            _, film_title, film_release, film_rating, film_review = result
            #print(film_title, film_release, film_rating, film_review)

            server_update_query = """UPDATE discord_servers
            SET user_count = user_count + 1, updated_at = now()
            WHERE server_id = %s;"""
            cur.execute(server_update_query, (guild_id,))
            user_update_query = """UPDATE diary_users
            SET last_entry = %s
            WHERE profile_name = %s AND server_id = %s"""
            cur.execute(user_update_query, (film_title, profile_name, guild_id))
            conn.commit()

            if film_rating:
                float_rating = float(film_rating)
                string_rating = ""
                if isinstance(float_rating, int):
                    for i in range(float_rating):
                        string_rating = string_rating + "<:47925letterboxd1star:1400770061404340234>"
                else:
                    int_rating = math.floor(float_rating)
                    for i in range(int_rating // 2):
                        string_rating = string_rating + "<:47925letterboxd1star:1400770061404340234>"
                    string_rating = string_rating + "<:79899letterboxdhalfstar:1400770001237184575>"

            embed = Embed(
                title=f"{film_title} ({film_release})",
                description=f"Rating: {string_rating}",
                color=0x1DB954  # Spotify green-ish, or choose any HEX color
            )

            if film_review:
                embed.add_field(name="Review", value=film_review, inline=False)
            else:
                embed.add_field(name="Review", value="*No review provided.*", inline=False)

            await interaction.response.send_message(f"{arg} has been added to the list\n{arg}'s most recent entry:\n",embed=embed)
        else:
            await interaction.response.send_message(f"{arg} is already in the list")
        cur.close()
        conn.close()

    except Exception as e:
        print("Error in /add command: ", e)
        await interaction.response.send_message("Failed to add user: " + arg, ephemeral= True)

@bot.tree.command(name="remove", description="Remove a user")
@app_commands.describe(arg="Username: ")
async def remove(interaction: discord.interactions, arg: str):
    guild_id = interaction.guild_id
    profile_name = arg.lower()
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
            await interaction.response.send_message(f"{arg} has been removed from the list")
        else:
            await interaction.response.send_message(f"{arg} is not in the list")

        cur.close()
        conn.close()
    except Exception as e:
        print("Error in /remove: ", e)
        await interaction.response.send_message("An error occurred while removing the user.", ephemeral=True)

@bot.tree.command(name="list", description="list all users")
@app_commands.describe()
async def list(interaction: discord.interactions):
    guild_id = interaction.guild.id
    user_list = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        get_query = """SELECT profile_name
        FROM diary_users
        WHERE server_id = %s"""
        cur.execute(get_query, (guild_id,))
        users = cur.fetchall()
        cur.close()
        conn.close()

        if not users:
            await interaction.response.send_message("No users have been added yet.")
        else:
            user_list = "\n".join(user[0] for user in users)
            await interaction.response.send_message(f"**Users in this server:**\n{user_list}")
    except Exception as e:
        print("Error printing list in ", e)
        await interaction.response.send_message("An error occurred while retrieving user list.", ephemeral=True)

bot.run(token, log_handler=handler, log_level=logging.DEBUG)