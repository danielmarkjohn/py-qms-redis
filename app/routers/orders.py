# app/routers/orders.py
from fastapi import APIRouter, Request, HTTPException
from bson import ObjectId
from app.database import orders_collection

# Prefix groups all these endpoints under /orders
router = APIRouter(prefix="/orders", tags=["Orders"])

# Helper function to convert MongoDB's ObjectId to a string 
# because standard JSON cannot serialize an ObjectId object.
def serialize_mongo_doc(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

@router.post("/")
async def create_order(request: Request):
    # Parse the raw JSON body
    order_data = await request.json()
    
    # Insert the dictionary directly into MongoDB
    result = await orders_collection.insert_one(order_data)
    
    # Return the newly created ID along with the data
    order_data["_id"] = str(result.inserted_id)
    return {"status": "success", "data": order_data}

@router.get("/")
async def get_all_orders():
    # Retrieve all documents in the collection
    cursor = orders_collection.find({})
    orders = await cursor.to_list(length=100) # Limit to 100 for safety
    
    # Serialize the ObjectIds to strings
    return {"status": "success", "data": [serialize_mongo_doc(order) for order in orders]}

@router.get("/{order_id}")
async def get_order(order_id: str):
    # Validate if the string is a valid MongoDB ObjectId
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid Order ID format")
        
    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    return {"status": "success", "data": serialize_mongo_doc(order)}

@router.put("/{order_id}")
async def update_order(order_id: str, request: Request):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid Order ID format")
        
    update_data = await request.json()
    
    # Update the document. $set ensures we only update the provided fields.
    result = await orders_collection.update_one(
        {"_id": ObjectId(order_id)}, 
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
        
    return {"status": "success", "message": "Order updated"}

@router.delete("/{order_id}")
async def delete_order(order_id: str):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid Order ID format")
        
    result = await orders_collection.delete_one({"_id": ObjectId(order_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
        
    return {"status": "success", "message": "Order deleted"}