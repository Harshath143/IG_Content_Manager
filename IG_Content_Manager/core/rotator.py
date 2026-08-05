# API Key Rotation logic
import os
from dotenv import load_dotenv
from groq import Groq

# Load keys from the .env file once
load_dotenv()

class APIKeyRotator:
    def __init__(self, key_names, swap_limit=10):
        # Fetch only valid non-empty keys from environment variables
        valid_keys = []
        for name in key_names:
            val = os.getenv(name)
            if val and val.strip():
                valid_keys.append(val.strip())
        
        self.keys = valid_keys
        self.swap_limit = swap_limit
        self.current_idx = 0
        self.counter = 0

    def get_client(self):
        if not self.keys:
            raise ValueError("No valid Groq API keys found in .env file!")
            
        if self.counter >= self.swap_limit:
            self.current_idx = (self.current_idx + 1) % len(self.keys)
            self.counter = 0
        
        active_key = self.keys[self.current_idx]
        self.counter += 1
        return Groq(api_key=active_key)