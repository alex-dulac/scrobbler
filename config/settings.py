import os

from dotenv import load_dotenv

load_dotenv()

LASTFM_API_KEY = os.getenv('LASTFM_API_KEY')
LASTFM_API_SECRET = os.getenv('LASTFM_API_SECRET')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
WEB_APP_URL = os.getenv('WEB_APP_URL')
APP_TOKEN = os.getenv('APP_TOKEN')
