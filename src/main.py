import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import APIKeyHeader

import models
from utils import roblox_service

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


@app.post("/create/")
async def reupload_asset(asset_id: int, _: str = Depends(verify_api_key)):
    asset = await roblox_service.asset_from_id(asset_id)
    if isinstance(asset, models.ClothingAsset):
        print("clothing asset found")
        image = await roblox_service.fetch_clothing_image(asset)
        uploaded = await roblox_service.upload_clothing_image(
            image,
            asset.name,
            asset.description,
            asset.asset_type,
            models.RbxCreator(int(TARGET), "Upload_Group", "Group"),
        )
        new_asset_id = uploaded.get("asset_id")
        if new_asset_id:
            onsale = await roblox_service.onsale_asset(
                new_asset_id,
                asset.name,
                asset.description,
                int(TARGET),
            )
            return {"uploaded": uploaded}
        return uploaded
