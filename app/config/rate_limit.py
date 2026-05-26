from fastapi import Request, HTTPException
from app.database import redis_client

# --- RATE LIMIT CONFIGURATION ---
# Format: "action_name": {"limit": max_requests, "window": seconds}
RATE_LIMITS = {
    "login": {"limit": 5, "window": 60},      # 5 attempts per minute
    "register": {"limit": 3, "window": 3600}, # 3 attempts per hour
    "default": {"limit": 100, "window": 60}   # 100 requests per minute
}

class RateLimiter:
    def __init__(self, action: str):
        self.action = action
        self.config = RATE_LIMITS.get(action, RATE_LIMITS["default"])
        
    async def __call__(self, request: Request):
        """
        FastAPI Dependency that checks Redis to see if the IP has exceeded its limit.
        """
        # Get the user's IP address (fallback to 'unknown' if running locally without headers)
        client_ip = request.client.host if request.client else "127.0.0.1"
        
        limit = self.config["limit"]
        window = self.config["window"]
        
        # Create a unique Redis key: e.g., "rate_limit:login:192.168.1.5"
        redis_key = f"rate_limit:{self.action}:{client_ip}"
        
        # 1. Check current usage
        current_usage = await redis_client.get(redis_key)
        
        if current_usage and int(current_usage) >= limit:
            raise HTTPException(
                status_code=429, 
                detail=f"Too many requests for {self.action}. Please try again later."
            )
            
        # 2. Increment the counter
        new_count = await redis_client.incr(redis_key)
        
        # 3. If it's their first request, start the countdown timer (window)
        if new_count == 1:
            await redis_client.expire(redis_key, window)