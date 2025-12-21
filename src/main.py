from fastapi import FastAPI

import models
from utils import roblox_service

app = FastAPI()


@app.get("/asset/{asset_id}")
def get_asset_info(asset_id: int):
    asset = roblox_service.asset_from_id(asset_id)
    final_dict = {asset}
    if isinstance(asset, models.ClothingAsset):
        print("clothing asset found")
        image = roblox_service.fetch_clothing_image(asset)
        with open(f"tests/{asset.asset_id}.png", "wb") as output:
            output.write(image)
    return final_dict
