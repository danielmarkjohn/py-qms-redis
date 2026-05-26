import os
import datetime
import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from app.database import db

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Secret key for JWT signing (In production, this must be in your .env)
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-qms-key-change-me")
FIXED_OTP = "1234"

class RegisterRequest(BaseModel):
    name: str
    phone: str
    otp: str

class LoginRequest(BaseModel):
    phone: str
    otp: str

@router.post("/register")
async def register(request: RegisterRequest):
    if request.otp != FIXED_OTP:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Check if user already exists
    existing_user = await db["users"].find_one({"phone": request.phone})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this phone number already exists")

    # Create new user
    new_user = {
        "name": request.name,
        "phone": request.phone,
        "created_at": datetime.datetime.now(datetime.timezone.utc)
    }
    
    result = await db["users"].insert_one(new_user)
    
    return {
        "status": "success", 
        "message": "User registered successfully", 
        "customer_id": str(result.inserted_id)
    }

@router.post("/login")
async def login(request: LoginRequest):
    if request.otp != FIXED_OTP:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user = await db["users"].find_one({"phone": request.phone})
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")

    # Generate JWT (Valid for 1 week)
    expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    
    payload = {
        "sub": str(user["_id"]), # Subject (User ID)
        "phone": user["phone"],
        "name": user["name"],
        "exp": expiration
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
    return {
        "status": "success",
        "access_token": token,
        "token_type": "Bearer"
    }