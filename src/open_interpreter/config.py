"""
Configuration center for environment variables and global constants
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Global configuration class"""
    
    # LLM Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    MODEL = os.getenv("MODEL", "gpt-4o")
    
    # Execution settings
    MAX_OUTPUT_LENGTH = int(os.getenv("MAX_OUTPUT_LENGTH", "1000"))
    TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "30"))
    
    # Display settings
    THEME = os.getenv("THEME", "dark")
    SHOW_TIMESTAMPS = os.getenv("SHOW_TIMESTAMPS", "true").lower() == "true"
    
    @classmethod
    def validate(cls):
        """Validate configuration values"""
        if not cls.OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY is not set in environment variables")
        
        if cls.TIMEOUT_SECONDS <= 0:
            raise ValueError("TIMEOUT_SECONDS must be positive")
        
        if cls.MAX_OUTPUT_LENGTH <= 0:
            raise ValueError("MAX_OUTPUT_LENGTH must be positive")