from discord import Embed
import psycopg2, os, logging
from dotenv import load_dotenv
from google.cloud import secretmanager

my_logger = logging.getLogger("mybot")

# load_dotenv()
# db_password = os.getenv("DB_PASSWORD")

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="discordbotdb",
        user="postgres",
        password=db_password,
        port='5432' #Change 5433 testing
    )

# Pulls private variables from Google Cloud hosted in their Secrets Manager
def access_secret(project_id: str, secret_id: str, version: str = "latest") -> str:
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"

        response = client.access_secret_version(name=name)
        secret_value = response.payload.data.decode("UTF-8")
        return secret_value
    except Exception as e:
        my_logger.error(f"Error in 'access_secret' function: {e}")


project_id = "discord-bit-468008"   
db_password = access_secret(project_id, "BotDatabasePassword")


def build_embed_message(data, profile_url, profile_name, profile_image):
    try:
        #my_logger.debug(data, profile_url, profile_name)
        _, film_title, film_release, film_rating, film_review, diary_url, film_rewatch, throwaway_var = data
        embed_list = []
        profile_url = profile_url
        profile_name = profile_name
        profile_image = profile_image

        if isinstance(film_title, str):
            film_title = [film_title]
            film_release = [film_release]
            film_rating = [film_rating]
            film_review = [film_review]
            diary_url = [diary_url]
            film_rewatch = [film_rewatch]

        latest_entry = film_title[0]

        for i in range(len(film_title)):
            title = film_title[i]
            release = film_release[i]
            rating = film_rating[i]
            review = film_review[i]
            diary = diary_url[i]
            rewatch = film_rewatch[i]

            if rating == '0':
                rating_embeded = "*No rating provided.*"
            else:
                try:
                    float_rating = float(rating) / 2
                    stars = int(float_rating)
                    half_star = float_rating % 1 >= 0.5
                    
                    string_rating = "<:47925letterboxd1star:1400770061404340234>" * stars
                    if half_star:
                        string_rating += "<:79899letterboxdhalfstar:1400770001237184575>"

                    rating_embeded = string_rating
                except ValueError:
                    rating_embeded = "*Invalid rating format.*"


            embed = Embed(
                    title=f"{title} ({release})",
                    description=rating_embeded,
                    url=diary,
                    color=0x1DB954
                )
            
            if not rewatch:
                embed.set_author(
                    name=f"{profile_name} Watched 🎦",
                    url=profile_url,
                    icon_url=profile_image
                )
            else:
                embed.set_author(
                    name=f"{profile_name} Rewatched 🔁",
                    url=profile_url,
                    icon_url=profile_image
                )
            
            if review:
                embed.add_field(
                    name="Review",
                    value=review,
                    inline=False
                )
            
            embed_list.append(embed)
        return embed_list, latest_entry
    except Exception as e:
        my_logger.error(f"Error in 'build_embed_message': {e}")

# Used to check if the server user performed the bot commands in the correct channel
# Verifies with the channel stored from the `/setchannel` command
def check_channel(channel_id, guild_id):
    conn = None
    cur = None
    try:
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
    except psycopg2.Error as e:
        my_logger.error(f"Error in 'check channel' function: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()

# Stores the users' most recent entry in their letterboxd diary into the database
# This function solely used with the task loop currently to handle updates
def update_last_entry(server_id, profile_name, film_title):
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """UPDATE diary_users
            SET last_entry = %s, updated_at = now()
            WHERE profile_name = %s AND server_id = %s""",
            (film_title, profile_name, server_id)
        )
        conn.commit()
    except psycopg2.Error as e:
        my_logger.error(f"Error in diary loop update query: {e}")
        conn.rollback()
    finally:
        if cur: cur.close()
        if conn: conn.close()