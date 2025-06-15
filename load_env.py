import os
from pathlib import Path

def load_dotenv():
    """Load environment variables from .env file"""
    try:
        env_path = Path('.') / '.env'
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=', 1)
                os.environ[key] = value
    except Exception as e:
        print(f"Warning: Failed to load .env file: {e}")

load_dotenv()