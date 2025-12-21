from enum import IntEnum
from typing import Literal

# Enums


class RbxAssetType(IntEnum):
    IMAGE = 1
    SHIRT = 11
    PANTS = 12


# Types

ClothingAssetType = Literal[
    RbxAssetType.SHIRT,
    RbxAssetType.PANTS,
]
CreatorType = Literal["User", "Group"]

# Roblox Creator class (for creator info - mainly useful for returning data + TUI)


class RbxCreator:
    def __init__(self, creator_id: int, username: str, creator_type: CreatorType):
        self.creator_id = creator_id
        self.username = username
        self.creator_type = creator_type


# Asset base class


class RbxAsset:
    def __init__(
        self,
        asset_id: int,
        creator: RbxCreator,
        name: str,
        description: str,
        asset_type: RbxAssetType,
    ) -> None:
        self.asset_id = asset_id
        self.name = name
        self.description = description
        self.creator = creator
        self.asset_type = asset_type


# Clothing asset class


class ClothingAsset(RbxAsset):
    def __init__(
        self,
        asset_id: int,
        creator: RbxCreator,
        name: str,
        description: str,
        asset_type: ClothingAssetType,
    ) -> None:
        super().__init__(
            asset_id=asset_id,
            creator=creator,
            name=name,
            description=description,
            asset_type=asset_type,
        )

    async def get_image(self) -> bytes:
        from utils import roblox_service

        return await roblox_service.fetch_clothing_image(self)
