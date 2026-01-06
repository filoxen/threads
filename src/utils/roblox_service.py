import asyncio
import json
import os
import uuid
import xml.etree.ElementTree

import httpx
from dotenv import load_dotenv

import models

load_dotenv()

# Constants and State

ROBLOSECURITY = os.getenv("ROBLOSECURITY_TOKEN")

if not ROBLOSECURITY:
    raise EnvironmentError("ROBLOSECURITY_TOKEN is missing from environment.")

# Must match the user ID of the account that owns the ROBLOSECURITY_TOKEN
PUBLISHER_USER_ID = os.getenv("PUBLISHER_USER_ID")

if not PUBLISHER_USER_ID:
    raise EnvironmentError("PUBLISHER_USER_ID is missing from environment.")

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

# Proxy configuration
ROBLOX_PROXY = os.getenv("ROBLOX_PROXY")


def _proxy_url(url: str) -> str:
    """Redirect roblox.com URLs to a proxy if configured."""
    if not ROBLOX_PROXY:
        return url
    return url.replace("roblox.com", ROBLOX_PROXY)


CSRF_URL = _proxy_url("https://apis.roblox.com/assets/user-auth/v1/assets")

ASSET_DELIVERY_BASE_URL = _proxy_url(
    "https://assetdelivery.roblox.com/v1/asset/?id={asset_id}"
)

ECONOMY_BASE_URL = _proxy_url("https://economy.roblox.com/v2/assets/{asset_id}/details")

UPLOAD_URL = _proxy_url("https://apis.roblox.com/assets/user-auth/v1/assets")

# Custom Exceptions


class RateLimitError(Exception):
    """Raised when hitting Roblox rate limits (HTTP 429)."""

    pass


# Client instance for connection pooling
_client = None


def _get_client() -> httpx.AsyncClient:
    """Get or create the shared HTTP client for connection pooling."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient()
    return _client


# Internal methods


async def _economy_request(asset_id: int) -> httpx.Response:
    """Fetch asset details from the Roblox economy API."""
    client = _get_client()
    return await client.get(
        ECONOMY_BASE_URL.format(asset_id=asset_id), headers=FETCH_HEADERS
    )


async def _asset_delivery_request(asset_id: int) -> httpx.Response:
    """Fetch an asset from the Roblox asset delivery API."""
    client = _get_client()
    return await client.get(
        ASSET_DELIVERY_BASE_URL.format(asset_id=asset_id),
        headers=FETCH_HEADERS,
        follow_redirects=True,
    )


async def _get_asset_xml(asset: models.RbxAsset) -> xml.etree.ElementTree.Element:
    """Fetch and parse asset XML content."""
    response = await _asset_delivery_request(asset.asset_id)
    response.raise_for_status()
    content = response.content.decode("utf-8")
    xml_root = xml.etree.ElementTree.fromstring(content)
    return xml_root


def _get_shirt_template_id_from_xml(root: xml.etree.ElementTree.Element) -> int:
    """Extract shirt template ID from asset XML."""
    url_element = root.find(".//url")
    if url_element is None:
        raise ValueError("XML did not contain a <url> tag.")
    url = url_element.text
    if not url:
        raise ValueError("<url> tag did not contain any text.")
    template_id = url.split("id=")[1]
    return int(template_id)


async def _get_csrf_token(url: str = CSRF_URL) -> str:
    """Retrieve CSRF token from the Roblox API."""
    client = _get_client()
    response = await client.post(url, cookies=CSRF_COOKIES, headers=CSRF_HEADERS)
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
    """Fetch asset information from Roblox by asset ID."""
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
    """Fetch the image data for a clothing asset."""
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
    """Upload a clothing image to Roblox and return the asset ID."""
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

    if response.status_code == 429:
        raise RateLimitError("Rate limit hit during upload")

    response.raise_for_status()
    data = response.json()

    operation_id = data.get("operationId")
    if operation_id:
        max_tries = 10
        wait_time = 1
        for attempt in range(max_tries):
            await asyncio.sleep(wait_time)
            op_response = await client.get(
                _proxy_url(f"https://apis.roblox.com/assets/user-auth/v1/operations/{operation_id}"),
                headers={"X-CSRF-TOKEN": csrf},
                cookies=CSRF_COOKIES,
            )
            op_response.raise_for_status()
            op_data = op_response.json()

            if op_data.get("done"):
                if op_data.get("response") and op_data["response"].get("assetId"):
                    return {"asset_id": op_data["response"]["assetId"]}
                return op_data

    return data


async def onsale_asset(
    asset_id: int,
    name: str,
    description: str,
    group_id: int,
    price: int = 5,
):
    """Put an asset on sale."""
    csrf = await _get_csrf_token()
    data = {
        "saleLocationConfiguration": {"saleLocationType": 1, "places": []},
        "targetId": asset_id,
        "priceInRobux": price,
        "publishingType": 2,
        "idempotencyToken": str(uuid.uuid4()),
        "publisherUserId": PUBLISHER_USER_ID,
        "creatorGroupId": group_id,
        "name": name,
        "description": description,
        "isFree": False,
        "agreedPublishingFee": 0,
        "priceOffset": 0,
        "quantity": 0,
        "quantityLimitPerUser": 0,
        "resaleRestriction": 2,
        "targetType": 0,
    }
    client = _get_client()
    response = await client.post(
        _proxy_url("https://itemconfiguration.roblox.com/v1/collectibles"),
        json=data,
        headers={
            "X-CSRF-TOKEN": csrf,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
            "Referer": "https://create.roblox.com/",
            "Origin": "https://create.roblox.com",
        },
        cookies=CSRF_COOKIES,
    )

    if response.status_code == 429:
        raise RateLimitError("Rate limit hit during onsale")

    response.raise_for_status()
    return response.json()
