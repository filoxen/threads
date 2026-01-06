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

app = FastAPI()

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
                
                onsale = await roblox_service.onsale_asset(
                    new_asset_id,
                    asset.name,
                    new_description,
                    int(TARGET),
                )
                
                # Send Discord notification
                asset_type_name = "Shirt" if asset.asset_type == models.RbxAssetType.SHIRT else "Pants"
                await discord.send_upload_webhook(
                    asset.name, asset_id, new_asset_id, asset_type_name
                )
                
                return {"uploaded": uploaded}
            return uploaded
    raise HTTPException(status_code=400, detail="Asset is not a clothing asset.")
