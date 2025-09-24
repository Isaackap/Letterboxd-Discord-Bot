from discord import Embed
import psycopg2, logging, requests
from config import db_password, api_key, db_port

my_logger = logging.getLogger("mybot")


def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="discordbotdb",
        user="postgres",
        password=db_password,
        port=db_port
    )


# project_id = "discord-bit-468008"   
# db_password = access_secret(project_id, "BotDatabasePassword")
# api_key = access_secret(project_id, "OMDb_API_KEY")


def build_embed_message(data, profile_url, profile_name, profile_image):
    url = f"http://www.omdbapi.com/?apikey={api_key}&"
    headers = {
        "X-API-Key": api_key,
        "Accept": "applications/json"
    }
    
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
            
            params = {
                "t": title,
                "y": release,
                "type": "movie"
            }

            try:
                response = requests.get(url, headers=headers, params=params)
                #print(response.json())
                data = response.json()

                if response.ok:
                    movie_poster = data["Poster"]
                else:
                    movie_poster = False
                    my_logger.error(f"build_embed_message() API call response returned false. Status Code: {response.status_code}")
                    try:
                        error_json = response.json()
                        my_logger.error(f"Error Message: {error_json.get("message", "No message provided.")}")
                    except ValueError:
                        my_logger.error(f"Raw Error: {response.text}")   

            except Exception as e:
                my_logger.error(f"Error in build_embed_message() API call: {e}")
                movie_poster = False

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
            
            if movie_poster:
                embed.set_thumbnail(url=movie_poster)
            
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