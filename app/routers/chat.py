# app/routers/chat.py
import json
from fastapi import APIRouter, Request
from pydantic import BaseModel
from groq import Groq
from app.database import db
from app.config.config import GROQ_API_KEY, MODEL, tools

router = APIRouter(prefix="/chat", tags=["AI Assistant"])

client = Groq(api_key=GROQ_API_KEY)

class ChatRequest(BaseModel):
    message: str

@router.post("/")
async def chat_with_agent(request: Request, payload: ChatRequest):
    customer_id = request.state.user["sub"]
    user_name = request.state.user.get("name", "Customer")

    messages = [
        {
            "role": "system",
            "content": f"You are the friendly customer support AI for our Quick-Commerce app. The user you are talking to is named {user_name}. Be concise, exact, and helpful."
        },
        {
            "role": "user",
            "content": payload.message
        }
    ]

    # 1. First Call to Groq
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        max_tokens=500
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # 2. Process Tool Calls dynamically
    if tool_calls:
        messages.append(response_message)
        
        for tool_call in tool_calls:
            if tool_call.function.name == "query_orders":
                # Extract parameters safely extracted by Groq from the user's text
                tool_args = json.loads(tool_call.function.arguments)
                tracking_number = tool_args.get("tracking_number")
                limit = tool_args.get("limit", 5)
                
                # --- BUILD SYSTEMATIC MONGODB QUERY ---
                # Always strictly scope queries to the logged-in customer_id for total security
                mongo_query = {"customer_id": customer_id}
                
                # Dynamic addition: If Groq extracted a tracking number, find exactly that order
                if tracking_number:
                    mongo_query["tracking_number"] = tracking_number

                # Execute query against database
                cursor = db["orders"].find(mongo_query).sort("created_at", -1).limit(limit)
                orders = await cursor.to_list(length=limit)
                
                # Clean and serialize structure for LLM consumption
                clean_orders = [
                    {
                        "order_id": str(o["_id"]), 
                        "product_id": o.get("product_id"), # Added to answer "what stock/product was ordered"
                        "quantity": o.get("quantity"),     # Added to answer stock quantities
                        "status": o.get("status"), 
                        "amount": o.get("amount"), 
                        "tracking": o.get("tracking_number")
                    }
                    for o in orders
                ]
                
                # Append execution payload to chat thread context
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": "query_orders",
                    "content": json.dumps(clean_orders),
                })

        # 3. Second Call to Groq (Generates natural language response with real DB values)
        final_response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=500
        )
        return {"status": "success", "reply": final_response.choices[0].message.content}

    return {"status": "success", "reply": response_message.content}