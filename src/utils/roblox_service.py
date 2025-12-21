import json
import os
import xml.etree.ElementTree

import requests
from dotenv import load_dotenv

import models

load_dotenv()

# Constants

ROBLOSECURITY = os.getenv("ROBLOSECURITY_TOKEN")

if not ROBLOSECURITY:
    raise EnvironmentError("ROBLOSECURITY_TOKEN is missing from environment.")

FETCH_HEADERS = {
    "Cookie": f".ROBLOSECURITY={ROBLOSECURITY}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Economy is an unauthed API; we should minimize cookie use where possible

ANONYMIZED_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

ASSET_DELIVERY_BASE_URL = "https://assetdelivery.roblox.com/v1/asset/?id={asset_id}"

ECONOMY_BASE_URL = "https://economy.roblox.com/v2/assets/{asset_id}/details"

# Internal methods


def _economy_request(asset_id: int) -> requests.Response:
    return requests.get(
        ECONOMY_BASE_URL.format(asset_id=asset_id), headers=FETCH_HEADERS
    )


def _asset_delivery_request(asset_id: int) -> requests.Response:
    return requests.get(
        ASSET_DELIVERY_BASE_URL.format(asset_id=asset_id), headers=FETCH_HEADERS
    )


def _get_asset_xml(asset: models.RbxAsset) -> xml.etree.ElementTree.Element:
    response = _asset_delivery_request(asset.asset_id)
    content = response.content.decode("utf-8")
    response.raise_for_status()
    xml_root = xml.etree.ElementTree.fromstring(content)
    return xml_root


def _get_shirt_template_id_from_xml(root: xml.etree.ElementTree.Element) -> int:
    url_element = root.find(".//url")
    if url_element is None:
        raise ValueError("XML did not contain a <url> tag.")
    url = url_element.text
    if not url:
        raise ValueError("<url> tag did not contain any text.")
    template_id = url.split("id=")[1]
    return int(template_id)


# External methods


def asset_from_id(id: int) -> models.RbxAsset:
    response = _economy_request(id)
    response.raise_for_status()
    asset_info = json.loads(response.content)
    creator_info = asset_info["Creator"]
    asset_creator = models.RbxCreator(
        creator_id=creator_info["Id"],
        username=creator_info["Name"],
        creator_type=creator_info["CreatorType"],
    )
    asset_type_id = asset_info["AssetTypeId"]
    if (
        asset_type_id == models.RbxAssetType.SHIRT
        or asset_type_id == models.RbxAssetType.PANTS
    ):
        return models.ClothingAsset(
            asset_id=asset_info["AssetId"],
            creator=asset_creator,
            name=asset_info["Name"],
            description=asset_info["Description"],
            asset_type=asset_info["AssetTypeId"],
        )
    return models.RbxAsset(
        asset_id=asset_info["AssetId"],
        creator=asset_creator,
        name=asset_info["Name"],
        description=asset_info["Description"],
        asset_type=asset_info["AssetTypeId"],
    )


def fetch_clothing_image(asset: models.ClothingAsset) -> bytes:
    try:
        xml = _get_asset_xml(asset)
        template_id = _get_shirt_template_id_from_xml(xml)
        image = _asset_delivery_request(template_id)
        image.raise_for_status()
        return image.content
    except Exception:
        raise  # TODO add logging


# def upload_clothing_image(image: bytes, target: models.RbxCreator) -> models.RbxAsset:
