import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

async def send_telegram_alert(latitude, longitude, risk_level, route=None, travel_time=None, driving_factors=None):
    """
    Sends a critical wildfire threat alert to a specified Telegram chat.
    """
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Warning: TELEGRAM_TOKEN or CHAT_ID is not configured. Alert aborted.")
        return

    message = (
        f"🚨 CRITICAL WILDFIRE THREAT 🚨\n"
        f"Sector: {latitude}, {longitude}\n"
        f"AI Threat Level: {risk_level}%"
    )
    
    if driving_factors:
        message += f"\n⚠️ Threat driven primarily by: {driving_factors}"
    
    if route and travel_time is not None:
        route_str = " ➔ ".join(route)
        message += f"\n\n🚒 EVACUATION LOGISTICS 🚒\nOptimal Route: {route_str}\nEst. Time: {travel_time} mins"

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=5.0)
            response.raise_for_status()
            print("Telegram alert dispatched successfully.")
    except Exception as e:
        print(f"Failed to dispatch Telegram alert: {e}")
