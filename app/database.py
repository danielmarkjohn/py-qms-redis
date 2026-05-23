# app/database.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "food_delivery")

# Create the async MongoDB client
client = AsyncIOMotorClient(MONGO_URI)

# Access the specific database
db = client[DB_NAME]

# Access the 'orders' collection (it will be created automatically upon first insert)
orders_collection = db["orders"]
users_collection = db["users"]