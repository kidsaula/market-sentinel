import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
USERS_FILE = "users.json"

WATCHLIST = [
    "NVDA", "TSLA", "AMZN", "AAPL", "PLTR"
]
