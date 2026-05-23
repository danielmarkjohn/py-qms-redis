# app/routers/orders.py
import json # <-- Need this to convert Mongo dicts to JSON strings for Redis
from fastapi import APIRouter, Request, HTTPException
from bson import ObjectId
from app.database import orders_collection, users_collection, redis_client, kafka_producer

router = APIRouter(prefix="/orders", tags=["Orders"])

def serialize_mongo_doc(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

# --- NEW HELPER FUNCTION ---
async def verify_user_exists(customer_id: str):
    """Checks if a customer_id is a valid Mongo ID and exists in the users collection."""
    if not customer_id or not ObjectId.is_valid(customer_id):
        raise HTTPException(status_code=400, detail="Invalid or missing customer_id format")
        
    user = await users_collection.find_one({"_id": ObjectId(customer_id)})
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {customer_id} does not exist")

# --- CREATE DROP OFF TO KAFKA---
@router.post("/", status_code=202) # 202 Accepted is the standard for async creation
async def create_order(request: Request):
    order_data = await request.json()
    
    # 1. Enforce user existence (Reads are fast, keep this here)
    customer_id = order_data.get("customer_id")
    await verify_user_exists(customer_id)
    
    # 2. Generate a new MongoDB ID instantly
    new_order_id = str(ObjectId())
    order_data["_id"] = new_order_id
    order_data["status"] = "processing" # Tell the user it's queued
    
    # 3. Publish creation task to Kafka
    event_payload = {
        "event_type": "CreateOrder",
        "order_data": order_data
    }
    
    await kafka_producer.send_and_wait(
        topic="orders.create", # Note the new topic name
        value=json.dumps(event_payload).encode("utf-8")
    )
    
    # 4. Respond instantly
    return {"status": "accepted", "message": "Order is being processed", "order_id": new_order_id}

# --- READ ALL ---
@router.get("/")
async def get_all_orders():
    cursor = orders_collection.find({})
    orders = await cursor.to_list(length=100)
    return {"status": "success", "data": [serialize_mongo_doc(order) for order in orders]}

# --- READ SINGLE ---
@router.get("/{order_id}")
async def get_order(order_id: str):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid Order ID format")
    
    redis_key = f"order:{order_id}"
    
    # 1. Check Redis Cache First
    cached_order = await redis_client.get(redis_key)
    if cached_order:
        # We add "source": "cache" so you can visually see Redis is working
        return {"status": "success", "data": json.loads(cached_order), "source": "cache"}
        
    # 2. Cache Miss: Fetch from MongoDB
    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    serialized_order = serialize_mongo_doc(order)
    
    # 3. Save to Redis for next time. setex = Set with Expiration (Time To Live)
    # We set it to expire in 3600 seconds (1 hour) to prevent infinite memory usage.
    await redis_client.setex(redis_key, 3600, json.dumps(serialized_order))
    
    return {"status": "success", "data": serialized_order, "source": "mongodb"}

# --- UPDATE ---
@router.put("/{order_id}")
async def update_order(order_id: str, request: Request):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid Order ID format")
        
    update_data = await request.json()
    
    if "customer_id" in update_data:
        await verify_user_exists(update_data["customer_id"])
    
    result = await orders_collection.update_one(
        {"_id": ObjectId(order_id)}, 
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # NEW: Delete the old, stale data from Redis!
    await redis_client.delete(f"order:{order_id}")
        
    return {"status": "success", "message": "Order updated"}

# --- DELETE ---
@router.delete("/{order_id}")
async def delete_order(order_id: str):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid Order ID format")
        
    result = await orders_collection.delete_one({"_id": ObjectId(order_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # NEW: Delete from Redis!
    await redis_client.delete(f"order:{order_id}")
        
    return {"status": "success", "message": "Order deleted"}