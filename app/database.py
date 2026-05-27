import os
import ssl
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv

load_dotenv()

# --- MongoDB Setup (Connection Pooled) ---
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "order_management")

# Industry standard Motor/MongoDB pooling
client = AsyncIOMotorClient(
    MONGO_URI,
    minPoolSize=10,                 # Keep 10 connections warm permanently (Fixes the 300ms cold start)
    maxPoolSize=100,                # Cap at 100 to prevent overwhelming the DB during traffic spikes
    maxIdleTimeMS=50000,            # Close idle connections after 50 seconds to free up DB memory
    serverSelectionTimeoutMS=5000,  # Fail fast (5s) if DB is down, rather than hanging the API for 30s
)

db = client[DB_NAME]
orders_collection = db["orders"]
users_collection = db["users"]
catalogue_collection = db["catalogue"]

# --- Redis Setup (Connection Pooled) ---
REDIS_URI = os.getenv("REDIS_URI")

# Asyncio Redis automatically manages a pool, but we enforce strict limits
redis_client = redis.from_url(
    REDIS_URI, 
    decode_responses=True,
    max_connections=50,             # Max concurrent Redis commands
    socket_timeout=5,               # Don't let queries hang forever
    socket_connect_timeout=5,       # Fast connection failure
)

# --- Aiven Kafka mTLS Setup (Optimized for Throughput) ---
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
        ssl_context=get_kafka_ssl_context(),
        
        # Enterprise Performance Settings
        acks="all",             # Guarantees no data loss if a broker crashes
        linger_ms=5,            # Wait 5ms before sending a batch (Massively increases throughput)
        max_batch_size=16384,       # Standard 16KB batch size
        connections_max_idle_ms=540000 # Keep broker connections alive longer (9 mins)
    )
    await kafka_producer.start()

async def close_kafka_producer():
    global kafka_producer
    if kafka_producer:
        await kafka_producer.stop()