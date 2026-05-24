# app/routers/catalog.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.database import db # <-- Change this line

router = APIRouter(prefix="/catalog", tags=["Catalog"])

@router.get("/")
async def get_catalog_items(category: Optional[str] = Query(None), limit: int = Query(20)):
    query = {}
    if category:
        query["category"] = {"$regex": f"^{category}$", "$options": "i"}

    try:
        # Use db directly here instead of database.db
        cursor = db["catalogue"].find(query).limit(limit) 
        items = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            items.append(doc)
        return {"status": "success", "count": len(items), "data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))