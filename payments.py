import time
import uuid
import httpx
from config import TON_MERCHANT_ADDRESS, TON_API_BASE, TON_API_KEY
from storage import get_payments, save_payments


def create_payment_intent(user_id: str, project_id: str, amount_ton: str, purpose: str) -> dict:
    payment_id = str(uuid.uuid4())
    data = get_payments()
    data[payment_id] = {
        "user_id": user_id,
        "project_id": project_id,
        "amount_ton": amount_ton,
        "purpose": purpose,
        "status": "pending",
        "created_at": int(time.time()),
    }
    save_payments(data)

    return {
        "payment_id": payment_id,
        "merchant_address": TON_MERCHANT_ADDRESS,
        "amount_ton": amount_ton,
        "purpose": purpose,
    }


def mark_paid(payment_id: str, tx_hash: str) -> None:
    data = get_payments()
    if payment_id in data:
        data[payment_id]["status"] = "paid"
        data[payment_id]["tx_hash"] = tx_hash
        save_payments(data)


def verify_payment_stub(payment_id: str, tx_hash: str) -> bool:
    # MVP/hackathon stub:
    # in production, fetch tx details from TON API and verify amount/comment/payload
    # This file is the correct place to implement that.
    mark_paid(payment_id, tx_hash)
    return True