# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers.orders import router as orders_router
from app.database import init_kafka_producer, close_kafka_producer # <-- Import the new functions

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize and connect
    await init_kafka_producer()
    print("Kafka Producer started")
    yield
    # Shutdown: Flush and disconnect
    await close_kafka_producer()
    print("Kafka Producer stopped")

app = FastAPI(title="Order Management API", lifespan=lifespan)

app.include_router(orders_router)

@app.get("/")
async def root():
    return {"message": "Order Management Service is running"}