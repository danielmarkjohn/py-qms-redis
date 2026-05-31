import os
import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager

# Import Routers
from app.routers.orders import router as orders_router
from app.routers.catalog import router as catalog_router
from app.routers.general import router as general_router
from app.routers.auth import router as auth_router  # <-- NEW AUTH ROUTER
from app.routers.chat import router as chat_router

from app.database import (
    init_kafka_producer,
    close_kafka_producer,
)
from app.config.config import origins

# Secret key for JWT signing
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-qms-key-change-me")

# --- GLOBAL JWT MIDDLEWARE ---
class JWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Allow CORS Preflight requests to pass without a token
        if request.method == "OPTIONS":
            return await call_next(request)

        # 2. Define routes that do NOT need authentication
        public_paths = ["/", "/docs", "/openapi.json", "/health", "/auth/login", "/auth/register"]
        
        # Allow public routes
        if request.url.path in public_paths:
            return await call_next(request)
            
        # 3. Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid token. Format: 'Bearer <token>'"})
            
        token = auth_header.split(" ")[1]
        
        # 4. Verify Token
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            # Attach the user payload to the request state so routers can use it later
            request.state.user = payload 
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Token has expired"})
        except jwt.InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})
            
        # 5. Proceed to the router
        return await call_next(request)


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
    title="QMS Order Management API",
    description="Order Management API",
    version="1.0.0", # <--- UPDATE THIS NUMBER ON EVERY RELEASE
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REGISTER AUTH MIDDLEWARE
app.add_middleware(JWTMiddleware)

# ROUTERS
app.include_router(general_router)
app.include_router(auth_router)  # <-- REGISTER AUTH ROUTER
app.include_router(orders_router)
app.include_router(catalog_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    return {
        "message": "Service is running securely"
    }