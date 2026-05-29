import os
import logging
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("finova-backend")

# API Keys
FINNHUB_API_KEYS = [
    key for key in [
        os.getenv("FINNHUB_API_KEY"),
        os.getenv("FINNHUB_API_KEY_2"),
    ] if key
]

ALPHA_VANTAGE_API_KEYS = [
    key for key in [
        os.getenv("ALPHA_VANTAGE_API_KEY"),
        os.getenv("ALPHA_VANTAGE_API_KEY_2"),
        os.getenv("ALPHA_VANTAGE_API_KEY_3"),
        os.getenv("ALPHA_VANTAGE_API_KEY_4"),
    ] if key
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# App parameters
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "127.0.0.1")
