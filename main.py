import discord, os, logging, psycopg2
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
db_password = os.getenv("DB_PASSWORD")

conn = psycopg2.connect(
    host="localhost",
    database="discordbotdb",
    user="postgres",
    password=db_password,
    port='5433'
)
cur = conn.cursor()

cur.close()
conn.close()


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

@bot.tree.command(name="add", description="Add a user")
@app_commands.describe(arg = "Username:")
async def add(interaction: discord.Interaction, arg: str):
    await interaction.response.send_message(f"{arg} has been added to the list")


bot.run(token, log_handler=handler, log_level=logging.DEBUG)