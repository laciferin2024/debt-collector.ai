"""
Configuration settings for the Debt Collection Agent.
All sensitive data should be loaded from environment variables.
"""
import os
from typing import Optional

from dotenv import  load_dotenv

load_dotenv()
# Twilio Configuration
TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER: Optional[str] = os.getenv("TWILIO_NUMBER")
TWILIO_WEBHOOK_URL: Optional[str] = os.getenv("TWILIO_WEBHOOK_URL")

# Deepgram Configuration for Speech-to-Text
DEEPGRAM_API_KEY: Optional[str] = os.getenv("DEEPGRAM_API_KEY")
DEEPGRAM_MODEL: str = os.getenv("DEEPGRAM_MODEL", "nova-3")

# OpenAI Configuration for LLM
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Cartesia Configuration for Text-to-Speech
CARTESIA_API_KEY: Optional[str] = os.getenv("CARTESIA_API_KEY")
CARTESIA_VOICE: str = os.getenv("CARTESIA_VOICE", "en-US-Standard-D")

LIVEKIT_API_KEY= os.getenv("LIVEKIT_API_KEY")
LIVEKIT_URL= os.getenv("LIVEKIT_URL")
LIVEKIT_API_SECRET= os.getenv("LIVEKIT_API_SECRET")

# Application Settings
RECORDINGS_DIR: str = os.getenv("RECORDINGS_DIR", "recordings")
TRANSCRIPTS_DIR: str = os.getenv("TRANSCRIPTS_DIR", "transcripts")
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


# Validate required configurations
REQUIRED_KEYS = [
    ("TWILIO_ACCOUNT_SID", TWILIO_ACCOUNT_SID),
    ("TWILIO_AUTH_TOKEN", TWILIO_AUTH_TOKEN),
    ("TWILIO_NUMBER", TWILIO_NUMBER),
    ("DEEPGRAM_API_KEY", DEEPGRAM_API_KEY),
    ("OPENAI_API_KEY", OPENAI_API_KEY),
    ("CARTESIA_API_KEY", CARTESIA_API_KEY),
    ("LIVEKIT_API_KEY", LIVEKIT_API_KEY),
    ("LIVEKIT_URL", LIVEKIT_URL),
    ("LIVEKIT_API_SECRET", LIVEKIT_API_SECRET),
]

for key, value in REQUIRED_KEYS:
    if not value:
        raise ValueError(f"Missing required environment variable: {key}")

# Create directories if they don't exist
os.makedirs(RECORDINGS_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
TWILIO_URL = os.getenv("TWILIO_URL")