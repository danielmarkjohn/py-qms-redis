import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load database config from .env
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "order_management")

async def push_to_mongo():
    # 1. Dynamically find the JSON file next to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "catalog_data.json")
    
    print(f"📂 Reading {json_path}...")
    
    try:
        with open(json_path, "r") as file:
            items = json.load(file)
    except FileNotFoundError:
        print(f"❌ Error: Could not find catalog_data.json at {json_path}")
        print("Please make sure you saved the JSON file in the same folder as this script.")
        return

    # 2. Connect to MongoDB
    print(f"🔌 Connecting to MongoDB: {MONGO_URI}")
    client = AsyncIOMotorClient(MONGO_URI)
    collection = client[DB_NAME]["catalogue"]

    # 3. Wipe old data and insert new data
    print("🗑️ Clearing old catalogue data...")
    await collection.delete_many({})
    
    print(f"🌱 Inserting {len(items)} items...")
    await collection.insert_many(items)

    # 4. Create indexes for fast querying
    print("🔍 Creating indexes for product_id and category...")
    await collection.create_index("product_id", unique=True)
    await collection.create_index("category")

    print(f"✅ Done! Data is live in the '{DB_NAME}' database.")
    client.close()

if __name__ == "__main__":
    asyncio.run(push_to_mongo())