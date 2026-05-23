import os
import ssl
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv

load_dotenv()

# --- MongoDB Setup ---
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "order_management")
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
orders_collection = db["orders"]
users_collection = db["users"]

# --- Redis Setup ---
REDIS_URI = os.getenv("REDIS_URI")
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

# CRITICAL: Start with None. Do not instantiate AIOKafkaProducer here.
kafka_producer = None

async def init_kafka_producer():
    global kafka_producer
    kafka_producer = AIOKafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BROKER"),
        security_protocol="SSL",
        ssl_context=get_kafka_ssl_context()
    )
    await kafka_producer.start()

async def close_kafka_producer():
    global kafka_producer
    if kafka_producer:
        await kafka_producer.stop()