import os
from dotenv import load_dotenv
from google.cloud import secretmanager
import logging

my_logger = logging.getLogger("mybot")

MAX_USER_COUNT_PER_SERVER = 50
TASK_LOOP_INTERVAL = 30  # in minutes

# Comment out the load_dotenv and os.getenv lines when deploying to Google Cloud
# Soley used for local testing with a .env file
# load_dotenv(dotenv_path="./local_files/.env")
# token = os.getenv("DISCORD_TOKEN_TEST")
# db_password = os.getenv("DB_PASSWORD")
# api_key = os.getenv("OMDb_API_KEY")
# db_port = 5433  # Change to 5433 for local testing if needed

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

# Uncomment and set your Google Cloud project ID and secret names when deploying
project_id = "discord-bit-468008"
token = access_secret(project_id, "BotToken")   
db_password = access_secret(project_id, "BotDatabasePassword")
api_key = access_secret(project_id, "OMDb_API_KEY")
db_port = 5432  # Default PostgreSQL port for production