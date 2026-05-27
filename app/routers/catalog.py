from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.database import db

router = APIRouter(prefix="/catalog", tags=["Catalog"])

# --- Pydantic Models for Validation ---
class ProductCreate(BaseModel):
    product_id: str
    name: str
    category: str
    price: float
    stock: int
    vendor: Optional[str] = "Internal"

class StockUpdate(BaseModel):
    quantity_to_add: int  # Can be negative to remove stock

# --- READ ALL / FILTER ---
@router.get("/")
async def get_catalog_items(category: Optional[str] = Query(None), limit: int = Query(20)):
    query = {}
    if category:
        query["category"] = {"$regex": f"^{category}$", "$options": "i"}

    try:
        cursor = db["catalogue"].find(query).limit(limit) 
        items = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            items.append(doc)
        return {"status": "success", "count": len(items), "data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- SEARCH ---
@router.get("/search")
async def search_catalog(q: str = Query(..., min_length=2, description="Search term"), limit: int = Query(20)):
    """Search products by name, category, or product_id."""
    # Uses $or to check multiple fields, with case-insensitive regex
    query = {
        "$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"category": {"$regex": q, "$options": "i"}},
            {"product_id": {"$regex": q, "$options": "i"}}
        ]
    }
    
    cursor = db["catalogue"].find(query).limit(limit)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
        
    return {"status": "success", "count": len(items), "data": items}

# --- GET SINGLE PRODUCT ---
@router.get("/{product_id}")
async def get_product(product_id: str):
    """Fetch a single product's details by its string product_id."""
    product = await db["catalogue"].find_one({"product_id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
        
    product["_id"] = str(product["_id"])
    return {"status": "success", "data": product}

# --- ADMIN: CREATE PRODUCT ---
@router.post("/", status_code=201)
async def create_product(product: ProductCreate):
    """Add a new product to the catalog."""
    # Ensure it doesn't already exist
    existing = await db["catalogue"].find_one({"product_id": product.product_id})
    if existing:
        raise HTTPException(status_code=400, detail=f"Product '{product.product_id}' already exists")
        
    new_product = product.model_dump()
    result = await db["catalogue"].insert_one(new_product)
    
    return {"status": "success", "message": "Product created", "id": str(result.inserted_id)}

# --- ADMIN: UPDATE STOCK ---
@router.patch("/{product_id}/stock")
async def update_stock(product_id: str, payload: StockUpdate):
    """Quickly increment or decrement stock for a product."""
    # Use $inc to atomically change the stock number, preventing race conditions
    result = await db["catalogue"].update_one(
        {"product_id": product_id},
        {"$inc": {"stock": payload.quantity_to_add}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
        
    return {"status": "success", "message": f"Stock updated by {payload.quantity_to_add}"}