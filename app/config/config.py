# app/config/config.py
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# --- AI ASSISTANT CONFIGURATION ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Change this centrally whenever Groq releases a new model
MODEL = "llama-3.1-8b-instant"

# This tells Groq what your backend is capable of doing

tools = [
    {
        "type": "function",
        "function": {
            "name": "query_orders",
            "description": "Query the customer's orders from the database. Can search broadly or filter specifically by a tracking number if provided by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_number": {
                        "type": "string",
                        "description": "The specific tracking number mentioned by the user (e.g., 'TRK-123456'). Leave empty if looking for broad history."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of orders to return. Defaults to 5.",
                        "default": 5
                    }
                },
                "required": []
            }
        }
    }
]
