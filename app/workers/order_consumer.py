# app/workers/order_consumer.py
import asyncio
import json
import os
from bson import ObjectId
from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv

# Import the database functions from your main app
from app.database import orders_collection, get_kafka_ssl_context

load_dotenv()

async def consume():
    consumer = AIOKafkaConsumer(
        "orders.create",
        bootstrap_servers=os.getenv("KAFKA_BROKER"),
        security_protocol="SSL",
        ssl_context=get_kafka_ssl_context(),
        group_id="db_writer_group"
    )
    
    await consumer.start()
    print("🎧 Kafka Consumer started. Listening for 'orders.create' to update MongoDB...")
    
    try:
        async for msg in consumer:
            event = json.loads(msg.value.decode("utf-8"))
            
            if event.get("event_type") == "CreateOrder":
                order_data = event["order_data"]
                order_id_str = order_data.pop("_id") # Remove string ID
                order_data["_id"] = ObjectId(order_id_str) # Convert back to Mongo Object
                
                # Write to MongoDB!
                await orders_collection.insert_one(order_data)
                print(f"✅ MongoDB Inserted: Order {order_id_str}")
                
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume())