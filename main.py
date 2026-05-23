# app/main.py
from fastapi import FastAPI
from app.routers.orders import router as orders_router

app = FastAPI(title="Order API")

# Register the orders router so the app knows about the endpoints
app.include_router(orders_router)

@app.get("/")
async def root():
    return {"message": "Order Service is running"}