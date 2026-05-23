# app/database.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import redis.asyncio as redis
import ssl
from aiokafka import AIOKafkaProducer

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

# --- NEW: Redis Setup ---
REDIS_URI = os.getenv("REDIS_URI")
# Because we imported redis.asyncio, this now creates an ASYNC client
redis_client = redis.from_url(REDIS_URI, decode_responses=True)

# --- Aiven Kafka mTLS Setup ---
def get_kafka_ssl_context():
    context = ssl.create_default_context(
        purpose=ssl.Purpose.SERVER_AUTH,
        cafile=os.getenv("KAFKA_CA_PATH")
    )
    context.load_cert_chain(
        certfile=os.getenv("KAFKA_CERT_PATH"),
        keyfile=os.getenv("KAFKA_KEY_PATH")
    )
    return context

kafka_producer = AIOKafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BROKER"),
    security_protocol="SSL",
    ssl_context=get_kafka_ssl_context()
)