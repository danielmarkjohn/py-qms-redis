import json
from app import database

class CacheService:
    @staticmethod
    async def get_json(key: str) -> dict | None:
        """Fetches and deserializes a JSON object from Redis."""
        data = await database.redis_client.get(key)
        return json.loads(data) if data else None

    @staticmethod
    async def set_json(key: str, data: dict, ttl_seconds: int = 3600):
        """Serializes and saves a dictionary to Redis with a TTL."""
        await database.redis_client.setex(key, ttl_seconds, json.dumps(data))

    @staticmethod
    async def invalidate(key: str):
        """Removes a key from Redis."""
        await database.redis_client.delete(key)

class EventPublisher:
    @staticmethod
    async def publish(topic: str, event_type: str, payload: dict):
        """Wraps standard event metadata and publishes to Kafka."""
        event_wrapper = {
            "event_type": event_type,
            "data": payload
        }
        await database.kafka_producer.send_and_wait(
            topic=topic,
            value=json.dumps(event_wrapper).encode("utf-8")
        )