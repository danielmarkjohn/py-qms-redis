import asyncio
import os
import json
import math
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import re

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "order_management")
OLLAMA_URL = "http://localhost:11434/api/generate"

def generate_catalog_batch(count: int) -> list:
    prompt = f"""
    Generate a JSON array containing exactly {count} distinct product objects for an online marketplace catalog.
    Distribute the items naturally across these categories: Food, Electronics, Toiletries, Medicine.
    
    Follow this exact JSON schema for each object:
    [
        {{
            "product_id": "unique-lowercase-slug-string",
            "name": "Full Product Display Name",
            "category": "Category Name",
            "price": 499.99,
            "stock": 150,
            "vendor": "Name of Manufacturer or Supplier"
        }}
    ]
    
    Return ONLY the raw JSON array. Do not include markdown wraps or styling elements.
    """

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": "llama3.1",
            "prompt": prompt,
            "stream": False,
            "format": "json" 
        })
        response.raise_for_status()
        
        generated_text = response.json().get("response", "[]")
        data = json.loads(generated_text)
        
        # Defensive flattening if model returns a parent object block
        if isinstance(data, dict):
            for val in data.values():
                if isinstance(val, list):
                    return val
            return list(data.values())
            
        return data if isinstance(data, list) else []
        
    except Exception as e:
        print(f"      ⚠️ Batch failed parsing sequence: {e}")
        return []

def run_ai_generator(total_count: int) -> list:
    batch_size = 10 
    batches = math.ceil(total_count / batch_size)
    compiled_catalog = []
    
    print(f"\n🧠 Asking local Llama 3.1 to construct {total_count} catalog products...")
    print(f"📦 Splitting operations into {batches} standard processing loops...\n")
    
    for i in range(batches):
        current_count = min(batch_size, total_count - (i * batch_size))
        print(f"⏳ Processing production tier {i+1}/{batches} ({current_count} items)...")
        
        batch_data = generate_catalog_batch(current_count)
        
        if batch_data:
            compiled_catalog.extend(batch_data)
            print(f"   ✅ Tier {i+1} compiled successfully.")
        else:
            print(f"   ❌ Tier {i+1} execution dropped. Moving forward.")
            
    return compiled_catalog

async def save_to_database(raw_items: list):
    # --- NEW: Aggressive Recursive Flattener ---
    clean_items = []
    def extract_dicts(element):
        if isinstance(element, dict):
            # Only keep dicts that look like actual products (have a product_id)
            if "product_id" in element:
                clean_items.append(element)
        elif isinstance(element, list):
            for sub_element in element:
                extract_dicts(sub_element)
                
    # Run the raw LLM output through the sanitizer
    extract_dicts(raw_items)
    # -------------------------------------------

    if not clean_items:
        print("\n❌ No valid product objects extracted. Database injection aborted.")
        return

    print(f"\n🧹 Sanitized payload: Extracted {len(clean_items)} perfectly formatted product documents.")
    print("🔌 Linking into local MongoDB cluster...")
    
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    catalogue_collection = db["catalogue"]

    print("🗑️ Resetting existing 'catalogue' storage collections...")
    await catalogue_collection.delete_many({})

    print(f"🌱 Writing {len(clean_items)} clean data entries...")
    result = await catalogue_collection.insert_many(clean_items)
    print(f"✅ Successfully written {len(result.inserted_ids)} items into database record storage.")

    print("🔍 Generating standard performance index patterns...")
    # Index product_id for O(1) order validation lookups, and category for filtering
    await catalogue_collection.create_index("product_id", unique=True)
    await catalogue_collection.create_index("category")
    
    print("🚀 Standard Catalog configuration pipeline complete!")
    client.close()

if __name__ == "__main__":
    try:
        user_input = input("How many raw products should your local Llama model construct? (e.g., 50): ")
        total_items = int(user_input.strip())
        
        if total_items <= 0:
            print("Please declare an index scope greater than 0.")
            exit(1)
            
        final_dataset = run_ai_generator(total_items)
        asyncio.run(save_to_database(final_dataset))
            
    except ValueError:
        print("❌ Invalid entry value detected. Process terminated.")