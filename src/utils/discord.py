import os
import httpx
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

async def send_upload_webhook(name: str, original_id: int, new_id: int, asset_type: str):
    """
    Sends a Discord webhook notification with an embed for the successful upload.
    """
    if not DISCORD_WEBHOOK_URL:
        print("Discord Webhook URL not configured, skipping notification.")
        return

    original_url = f"https://www.roblox.com/catalog/{original_id}"
    new_url = f"https://www.roblox.com/catalog/{new_id}"

    embed = {
        "title": "New Clothing Uploaded",
        "color": 3066993,  # Green
        "fields": [
            {"name": "Name", "value": name, "inline": False},
            {"name": "Type", "value": asset_type, "inline": True},
            {"name": "Original Asset", "value": f"[Link]({original_url})", "inline": True},
            {"name": "New Asset", "value": f"[Link]({new_url})", "inline": True},
        ],
        "footer": {"text": "Filoxen Labs"},
    }

    payload = {"embeds": [embed]}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(DISCORD_WEBHOOK_URL, json=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send Discord webhook: {e}")
