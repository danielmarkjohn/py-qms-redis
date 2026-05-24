from fastapi import APIRouter, Request, HTTPException
from bson import ObjectId
from app import database
from app.utils.services import CacheService, EventPublisher

router = APIRouter(prefix="/orders", tags=["Orders"])

def serialize_mongo_doc(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

# --- VALIDATORS ---
async def verify_user_exists(customer_id: str):
    if not customer_id or not ObjectId.is_valid(customer_id):
        raise HTTPException(status_code=400, detail="Invalid or missing customer_id format")
        
    user = await database.users_collection.find_one({"_id": ObjectId(customer_id)})
    if not user:
        raise HTTPException(status_code=404, detail=f"User {customer_id} does not exist")

async def get_and_verify_product(product_id: str, quantity: int) -> dict:
    if not product_id:
        raise HTTPException(status_code=400, detail="Missing product_id")
        
    product = await database.db["catalogue"].find_one({"product_id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found in catalogue")
        
    if product.get("stock", 0) < quantity:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient stock for '{product_id}'. Available: {product.get('stock', 0)}"
        )
        
    return product

# --- CREATE (Publishes to Kafka via Service) ---
@router.post("/", status_code=202)
async def create_order(request: Request):
    order_data = await request.json()
    
    quantity = int(order_data.get("quantity", 1))
    product_id = order_data.get("product_id")
    customer_id = order_data.get("customer_id")
    
    # 1. Run validations
    await verify_user_exists(customer_id)
    product = await get_and_verify_product(product_id, quantity)
    
    # 2. Calculate the secure amount server-side
    total_amount = product.get("price", 0.0) * quantity
    
    # 3. Atomically deduct stock from the catalog to prevent overselling
    await database.db["catalogue"].update_one(
        {"product_id": product_id},
        {"$inc": {"stock": -quantity}}
    )
    
    # 4. Finalize order payload
    new_order_id = str(ObjectId())
    order_data["_id"] = new_order_id
    order_data["amount"] = total_amount  # Set secure amount
    order_data["status"] = "processing"
    
    # Use standard Event Publisher
    await EventPublisher.publish(
        topic="orders.create",
        event_type="CreateOrder",
        payload=order_data
    )
    
    return {
        "status": "accepted", 
        "message": "Order is being processed", 
        "order_id": new_order_id,
        "calculated_amount": total_amount
    }

# --- READ SINGLE (Uses Redis via Service) ---
@router.get("/{order_id}")
async def get_order(order_id: str):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid Order ID format")
    
    redis_key = f"order:{order_id}"
    
    # Check cache via Service
    cached_order = await CacheService.get_json(redis_key)
    if cached_order:
        return {"status": "success", "data": cached_order, "source": "cache"}
        
    # Fallback to DB
    order = await database.orders_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    serialized_order = serialize_mongo_doc(order)
    
    # Update cache via Service
    await CacheService.set_json(redis_key, serialized_order)
    
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
    if "product_id" in update_data:
        await verify_product_exists(update_data["product_id"])
    
    result = await database.orders_collection.update_one(
        {"_id": ObjectId(order_id)}, 
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Invalidate cache via Service
    await CacheService.invalidate(f"order:{order_id}")
    
    return {"status": "success", "message": "Order updated"}

# --- DELETE ---
@router.delete("/{order_id}")
async def delete_order(order_id: str):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid Order ID format")
        
    result = await database.orders_collection.delete_one({"_id": ObjectId(order_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Invalidate cache via Service
    await CacheService.invalidate(f"order:{order_id}")
    
    return {"status": "success", "message": "Order deleted"}