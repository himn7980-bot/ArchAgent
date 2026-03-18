import time
import uuid
from storage import get_nfts, save_nfts
from config import NFT_COLLECTION_ADDRESS


def build_nft_metadata(project_id: str, title: str, description: str, image_url: str, owner_wallet: str) -> dict:
    return {
        "name": title,
        "description": description,
        "image": image_url,
        "project_id": project_id,
        "owner_wallet": owner_wallet,
        "collection": NFT_COLLECTION_ADDRESS,
        "created_at": int(time.time()),
    }


def create_mint_request(project_id: str, owner_wallet: str, title: str, description: str, image_url: str) -> dict:
    nft_id = str(uuid.uuid4())
    metadata = build_nft_metadata(project_id, title, description, image_url, owner_wallet)

    data = get_nfts()
    data[nft_id] = {
        "project_id": project_id,
        "owner_wallet": owner_wallet,
        "metadata": metadata,
        "status": "pending",
    }
    save_nfts(data)

    return {
        "nft_id": nft_id,
        "status": "pending",
        "metadata": metadata,
    }