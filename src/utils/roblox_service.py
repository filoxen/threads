import json
import os
import xml.etree.ElementTree

import httpx
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

CSRF_HEADERS = {
    "X-CSRF-TOKEN": "",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
    "Referer": "https://create.roblox.com/",
    "Origin": "https://create.roblox.com",
}

CSRF_COOKIES = {".ROBLOSECURITY": ROBLOSECURITY}

CSRF_URL = "https://apis.roblox.com/assets/user-auth/v1/assets"

ASSET_DELIVERY_BASE_URL = "https://assetdelivery.roblox.com/v1/asset/?id={asset_id}"

ECONOMY_BASE_URL = "https://economy.roblox.com/v2/assets/{asset_id}/details"

UPLOAD_URL = "https://apis.roblox.com/assets/user-auth/v1/assets"

# Client instance for connection pooling
_client = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient()
    return _client


# Internal methods


async def _economy_request(asset_id: int) -> httpx.Response:
    client = _get_client()
    return await client.get(
        ECONOMY_BASE_URL.format(asset_id=asset_id), headers=FETCH_HEADERS
    )


async def _asset_delivery_request(asset_id: int) -> httpx.Response:
    client = _get_client()
    return await client.get(
        ASSET_DELIVERY_BASE_URL.format(asset_id=asset_id), headers=FETCH_HEADERS, follow_redirects=True
    )


async def _get_asset_xml(asset: models.RbxAsset) -> xml.etree.ElementTree.Element:
    response = await _asset_delivery_request(asset.asset_id)
    response.raise_for_status()
    content = response.content.decode("utf-8")
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


async def _get_csrf_token() -> str:
    client = _get_client()
    response = await client.post(CSRF_URL, cookies=CSRF_COOKIES, headers=CSRF_HEADERS)
    csrf = response.headers.get("X-CSRF-TOKEN")
    if not csrf:
        raise httpx.HTTPStatusError(
            "Failed to retrieve X-CSRF-TOKEN.",
            request=response.request,
            response=response,
        )
    return csrf


# External methods


async def asset_from_id(id: int) -> models.RbxAsset:
    response = await _economy_request(id)
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


async def fetch_clothing_image(asset: models.ClothingAsset) -> bytes:
    try:
        xml = await _get_asset_xml(asset)
        template_id = _get_shirt_template_id_from_xml(xml)
        image = await _asset_delivery_request(template_id)
        image.raise_for_status()
        return image.content
    except Exception:
        raise  # TODO add logging


async def upload_clothing_image(
    image: bytes,
    name: str,
    description: str,
    asset_type: models.RbxAssetType,
    target: models.RbxCreator,
) -> dict:
    csrf = await _get_csrf_token()
    meta = {
        "displayName": name,
        "description": description,
        "assetType": asset_type,
        # TODO add support for user creation context
        "creationContext": {
            "creator": {"groupId": target.creator_id},
            "expectedPrice": 10,
        },
    }
    client = _get_client()
    response = await client.post(
        UPLOAD_URL,
        files={
            "request": (None, json.dumps(meta), "application/json"),
            "fileContent": ("clothing_upload", image, "image/png"),
        },
        headers={
            "X-CSRF-TOKEN": csrf,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://create.roblox.com/",
            "Origin": "https://create.roblox.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        },
        cookies=CSRF_COOKIES,
    )
    response.raise_for_status()
    data = response.json()
    return data
