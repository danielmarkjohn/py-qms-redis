from fastapi import APIRouter, Request, HTTPException
from bson import ObjectId
import json
from app import database # Clean import

router = APIRouter(prefix="/orders", tags=["Orders"])

def serialize_mongo_doc(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

async def verify_user_exists(customer_id: str):
    if not customer_id or not ObjectId.is_valid(customer_id):
        raise HTTPException(status_code=400, detail="Invalid or missing customer_id format")
        
    user = await database.users_collection.find_one({"_id": ObjectId(customer_id)})
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {customer_id} does not exist")

# --- CREATE (Publishes to Kafka) ---
@router.post("/", status_code=202)
async def create_order(request: Request):
    order_data = await request.json()
    
    customer_id = order_data.get("customer_id")
    await verify_user_exists(customer_id)
    
    new_order_id = str(ObjectId())
    order_data["_id"] = new_order_id
    order_data["status"] = "processing"
    
    event_payload = {
        "event_type": "CreateOrder",
        "order_data": order_data
    }
    
    await database.kafka_producer.send_and_wait(
        topic="orders.create",
        value=json.dumps(event_payload).encode("utf-8")
    )
    
    return {"status": "accepted", "message": "Order is being processed", "order_id": new_order_id}

# --- READ SINGLE (Uses Redis) ---
@router.get("/{order_id}")
async def get_order(order_id: str):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid Order ID format")
    
    redis_key = f"order:{order_id}"
    cached_order = await database.redis_client.get(redis_key)
    
    if cached_order:
        return {"status": "success", "data": json.loads(cached_order), "source": "cache"}
        
    order = await database.orders_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    serialized_order = serialize_mongo_doc(order)
    await database.redis_client.setex(redis_key, 3600, json.dumps(serialized_order))
    
    return {"status": "success", "data": serialized_order, "source": "mongodb"}

# --- READ ALL ---
@router.get("/")
async def get_all_orders():
    cursor = database.orders_collection.find({})
    orders = await cursor.to_list(length=100)
    return {"status": "success", "data": [serialize_mongo_doc(order) for order in orders]}

# --- UPDATE ---
@router.put("/{order_id}")
async def update_order(order_id: str, request: Request):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid Order ID format")
        
    update_data = await request.json()
    
    if "customer_id" in update_data:
        await verify_user_exists(update_data["customer_id"])
    
    result = await database.orders_collection.update_one(
        {"_id": ObjectId(order_id)}, 
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
        
    await database.redis_client.delete(f"order:{order_id}")
    return {"status": "success", "message": "Order updated"}

# --- DELETE ---
@router.delete("/{order_id}")
async def delete_order(order_id: str):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid Order ID format")
        
    result = await database.orders_collection.delete_one({"_id": ObjectId(order_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
        
    await database.redis_client.delete(f"order:{order_id}")
    return {"status": "success", "message": "Order deleted"}