import os
import datetime
import jwt
from fastapi import APIRouter, HTTPException, Depends # <-- Added Depends
from pydantic import BaseModel
from app.database import db

# Import your new Rate Limiter
from app.config.rate_limit import RateLimiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-qms-key-change-me")
FIXED_OTP = os.getenv("FIXED_OTP", "1234") 

class RegisterRequest(BaseModel):
    name: str
    phone: str
    otp: str

class LoginRequest(BaseModel):
    phone: str
    otp: str

# Inject the RateLimiter as a dependency
@router.post("/register", dependencies=[Depends(RateLimiter("register"))])
async def register(request: RegisterRequest):
    if request.otp != FIXED_OTP:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    existing_user = await db["users"].find_one({"phone": request.phone})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = {
        "name": request.name,
        "phone": request.phone,
        "created_at": datetime.datetime.now(datetime.timezone.utc)
    }
    result = await db["users"].insert_one(new_user)
    
    return {"status": "success", "customer_id": str(result.inserted_id)}

# Inject the RateLimiter as a dependency
@router.post("/login", dependencies=[Depends(RateLimiter("login"))])
async def login(request: LoginRequest):
    if request.otp != FIXED_OTP:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user = await db["users"].find_one({"phone": request.phone})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    payload = {
        "sub": str(user["_id"]),
        "phone": user["phone"],
        "name": user["name"],
        "exp": expiration
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
    return {"status": "success", "access_token": token, "token_type": "Bearer"}