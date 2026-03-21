import os
import time
import uuid
import requests
from storage import get_nfts, save_nfts
from config import NFT_COLLECTION_ADDRESS, PINATA_API_KEY, PINATA_SECRET_KEY

def upload_file_to_ipfs(file_path: str) -> str:
    """آپلود تصویر در فضای غیرمتمرکز IPFS"""
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_KEY
    }
    with open(file_path, "rb") as file:
        response = requests.post(url, files={"file": file}, headers=headers)
    if response.status_code == 200:
        return f"ipfs://{response.json()['IpfsHash']}"
    raise Exception(f"IPFS Upload Error: {response.text}")

def upload_json_to_ipfs(metadata: dict) -> str:
    """آپلود فایل متادیتا (JSON) در IPFS"""
    url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
    headers = {
        "Content-Type": "application/json",
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_KEY
    }
    response = requests.post(url, json=metadata, headers=headers)
    if response.status_code == 200:
        return f"ipfs://{response.json()['IpfsHash']}"
    raise Exception(f"IPFS Metadata Error: {response.text}")

def build_nft_metadata(project_id: str, title: str, description: str, ipfs_image_url: str) -> dict:
    """ساخت استاندارد متادیتای NFT برای شبکه TON"""
    return {
        "name": title,
        "description": description,
        "image": ipfs_image_url,
        "attributes": [
            {"trait_type": "Project ID", "value": project_id},
            {"trait_type": "Creator", "value": "ArchAgent AI"}
        ]
    }

def create_mint_request(project_id: str, owner_wallet: str, title: str, description: str, local_image_path: str) -> dict:
    """تابع اصلی برای آماده‌سازی مینت"""
    # ۱. آپلود تصویر در IPFS
    ipfs_image_url = upload_file_to_ipfs(local_image_path)

    # ۲. ساخت و آپلود متادیتا در IPFS
    metadata = build_nft_metadata(project_id, title, description, ipfs_image_url)
    ipfs_metadata_url = upload_json_to_ipfs(metadata)

    # ۳. ذخیره در دیتابیس لوکال
    nft_id = str(uuid.uuid4())
    data = get_nfts()
    data[nft_id] = {
        "project_id": project_id,
        "owner_wallet": owner_wallet,
        "metadata_url": ipfs_metadata_url, # ذخیره لینک بلاکچینی
        "metadata": metadata,
        "status": "pending_mint",
        "created_at": int(time.time()),
    }
    save_nfts(data)

    return {
        "nft_id": nft_id,
        "status": "pending_mint",
        "metadata_url": ipfs_metadata_url,
    }
