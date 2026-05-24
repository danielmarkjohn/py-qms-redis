# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routers.orders import router as orders_router
from app.routers.catalog import router as catalog_router
from app.routers.general import router as general_router
from app.database import (
    init_kafka_producer,
    close_kafka_producer,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_kafka_producer()
    print("Kafka Producer started")

    yield

    # Shutdown
    await close_kafka_producer()
    print("Kafka Producer stopped")


app = FastAPI(
    title="Order Management API",
    lifespan=lifespan,
)

# CORS CONFIG
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ROUTERS
app.include_router(general_router)
app.include_router(orders_router)
app.include_router(catalog_router)


@app.get("/")
async def root():
    return {
        "message": "Order Management Service is running"
    }