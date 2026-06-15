# API Key Rotation logic
import os
from dotenv import load_dotenv
from groq import Groq

# Load keys from the .env file once
load_dotenv()

class APIKeyRotator:
    def __init__(self, key_names, swap_limit=10):
        # Fetch the actual keys from environment variables
        self.keys = [os.getenv(name) for name in key_names]
        self.swap_limit = swap_limit
        self.current_idx = 0
        self.counter = 0

    def get_client(self):
        if self.counter >= self.swap_limit:
            self.current_idx = (self.current_idx + 1) % len(self.keys)
            self.counter = 0
        
        active_key = self.keys[self.current_idx]
        if not active_key:
            raise ValueError(f"Key #{self.current_idx + 1} not found in .env file!")
            
        self.counter += 1
        return Groq(api_key=active_key)