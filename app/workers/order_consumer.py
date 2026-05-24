import asyncio
import json
import os
import logging
from bson import ObjectId
from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv

# Import the database functions from your main app
from app.database import orders_collection, get_kafka_ssl_context

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_consumer")

async def consume():
    consumer = AIOKafkaConsumer(
        "orders.create",
        bootstrap_servers=os.getenv("KAFKA_BROKER"),
        security_protocol="SSL",
        ssl_context=get_kafka_ssl_context(),
        group_id="db_writer_group"
    )
    
    await consumer.start()
    logger.info("🎧 Kafka Consumer started. Listening...")
    
    try:
        async for msg in consumer:
            try:
                event = json.loads(msg.value.decode("utf-8"))
                
                if event.get("event_type") == "CreateOrder":
                    # UPDATED: Accessing "data" instead of "order_data"
                    order_data = event.get("data")
                    
                    if not order_data:
                        logger.warning(f"Malformed event received (missing 'data' key): {event}")
                        continue
                    
                    # Ensure _id is correctly formatted for MongoDB
                    order_id_str = order_data.pop("_id")
                    order_data["_id"] = ObjectId(order_id_str)
                    
                    # Write to MongoDB
                    await orders_collection.insert_one(order_data)
                    logger.info(f"✅ MongoDB Inserted: Order {order_id_str}")
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                
    finally:
        await consumer.stop()

if __name__ == "__main__":
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        pass