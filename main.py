import discord, os, logging, psycopg2
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

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
    try:
        guild_id = guild.id
        print(f"Joined new server: {guild.name} - {guild_id}")

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
        print(e)
    

# NEED TO UPDATE server_id.user_count AS WELL!!!!!!!!
@bot.tree.command(name="add", description="Add a user")
@app_commands.describe(arg = "Username:")
async def add(interaction: discord.Interaction, arg: str):
    try:
        guild_id = interaction.guild.id

        conn = get_db_connection()
        cur = conn.cursor()
        query = """INSERT INTO diary_users (profile_name, server_id, updated_at)
        VALUES (%s, %s, now())
        ON CONFLICT (profile_name, server_id) DO NOTHING;"""
        cur.execute(query, (arg, guild_id))
        conn.commit()
        cur.close()
        conn.close()

        await interaction.response.send_message(f"{arg} has been added to the list")
    except Exception as e:
        print("Error in /add command: ", e)
        await interaction.response.send_message("Failed to add user: " + arg, ephemeral= True)


bot.run(token, log_handler=handler, log_level=logging.DEBUG)