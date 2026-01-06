import asyncio
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import APIKeyHeader

import models
from utils import roblox_service, hashing, discord
import database

load_dotenv()

TARGET = os.getenv("TARGET_ID")
VALID_API_KEY = os.getenv("VALID_API_KEY")

if TARGET is None:
    raise EnvironmentError("TARGET_ID is missing from environment.")
if not VALID_API_KEY:
    raise EnvironmentError("VALID_API_KEY is missing from environment.")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background task
    task = asyncio.create_task(process_onsale_queue())
    yield
    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

# Retry Configuration
RETRY_INTERVAL = int(os.getenv("RETRY_INTERVAL_SECONDS", 60))
RETRY_DELAY = int(os.getenv("RETRY_DELAY_SECONDS", 300))

async def process_onsale_queue():
    """Background task to retry failed onsale attempts."""
    while True:
        try:
            pending_items = database.get_pending_onsale_items()
            for item in pending_items:
                print(f"Retrying onsale for asset {item['asset_id']} (Attempt {item['retry_count'] + 1})")
                try:
                    await roblox_service.onsale_asset(
                        item["asset_id"],
                        item["name"],
                        item["description"],
                        item["group_id"],
                    )
                    database.remove_from_onsale_queue(item["id"])
                    print(f"Successfully put asset {item['asset_id']} on sale via queue.")
                    
                    # Send Discord notification on successful retry
                    await discord.send_upload_webhook(
                        item["name"], 
                        item["original_asset_id"], 
                        item["asset_id"], 
                        item["asset_type"]
                    )
                except roblox_service.RateLimitError:
                    print(f"Rate limit hit again for asset {item['asset_id']}, backing off.")
                    database.increment_retry_onsale(item["id"], delay_seconds=RETRY_DELAY)
                except Exception as e:
                    print(f"Unexpected error retrying asset {item['asset_id']}: {e}")
                    database.increment_retry_onsale(item["id"], delay_seconds=RETRY_DELAY * 2)
            
            await asyncio.sleep(RETRY_INTERVAL)
        except Exception as e:
            print(f"Error in background queue task: {e}")
            await asyncio.sleep(RETRY_INTERVAL)

api_key_header = APIKeyHeader(name="x-api-key")


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != VALID_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key"
        )
    return api_key


@app.get("/asset/{asset_id}")
async def get_asset_info(asset_id: int, _: str = Depends(verify_api_key)):
    asset = await roblox_service.asset_from_id(asset_id)
    final_dict = {asset}
    if isinstance(asset, models.ClothingAsset):
        print("clothing asset found")
        image = await roblox_service.fetch_clothing_image(asset)
        with open(f"tests/{asset.asset_id}.png", "wb") as output:
            output.write(image)
    return final_dict


# Global dictionary to store locks per image hash
upload_locks: dict[str, asyncio.Lock] = {}

@app.post("/create/")
async def reupload_asset(asset_id: int, _: str = Depends(verify_api_key)):
    asset = await roblox_service.asset_from_id(asset_id)
    if isinstance(asset, models.ClothingAsset):
        print(f"Clothing asset found: {asset.name}")
        image = await roblox_service.fetch_clothing_image(asset)
        
        # Check for duplicates using hash
        image_hash = hashing.get_image_hash(image)
        
        # Get or create a lock for this specific hash
        if image_hash not in upload_locks:
            upload_locks[image_hash] = asyncio.Lock()
        
        async with upload_locks[image_hash]:
            # Double-check database inside the lock
            existing_new_id = database.get_uploaded_asset(image_hash)
            
            if existing_new_id:
                print(f"Asset already uploaded (hash match): {existing_new_id}")
                return {"uploaded": {"asset_id": existing_new_id}}

            # Prepare description with original URL
            original_url = f"https://www.roblox.com/catalog/{asset_id}"
            new_description = f"{asset.description}\n\nOriginal: {original_url}"

            uploaded = await roblox_service.upload_clothing_image(
                image,
                asset.name,
                new_description,
                asset.asset_type,
                models.RbxCreator(int(TARGET), "Upload_Group", "Group"),
            )
            new_asset_id = uploaded.get("asset_id")
            if new_asset_id:
                # Save to database
                database.save_uploaded_asset(image_hash, asset_id, new_asset_id)
                
                try:
                    onsale = await roblox_service.onsale_asset(
                        new_asset_id,
                        asset.name,
                        new_description,
                        int(TARGET),
                    )
                except roblox_service.RateLimitError:
                    print(f"Rate limit hit for asset {new_asset_id}, adding to retry queue.")
                    asset_type_name = "Shirt" if asset.asset_type == models.RbxAssetType.SHIRT else "Pants"
                    database.add_to_onsale_queue(
                        new_asset_id,
                        asset_id, # original
                        asset.name,
                        new_description,
                        int(TARGET),
                        asset_type_name
                    )
                    return {
                        "uploaded": uploaded,
                        "onsale": "queued",
                        "info": "Rate limit hit, item will be put on sale automatically later."
                    }
                
                # Send Discord notification (only for successful initial onsale)
                asset_type_name = "Shirt" if asset.asset_type == models.RbxAssetType.SHIRT else "Pants"
                await discord.send_upload_webhook(
                    asset.name, asset_id, new_asset_id, asset_type_name
                )
                
                return {"uploaded": uploaded}
            return uploaded
    raise HTTPException(status_code=400, detail="Asset is not a clothing asset.")
