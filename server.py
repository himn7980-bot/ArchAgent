from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from payments import create_payment_intent, verify_payment_stub
from nft import create_mint_request
from storage import get_projects

app = FastAPI(title="ArchAgent TON Backend")

app.mount("/webapp", StaticFiles(directory="webapp"), name="webapp")


@app.get("/")
def root():
    return {"app": "ArchAgent", "ok": True}


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/webapp/index.html")
def webapp_index():
    return FileResponse("webapp/index.html")


class PaymentCreate(BaseModel):
    user_id: str
    project_id: str
    amount_ton: str
    purpose: str


class PaymentVerify(BaseModel):
    payment_id: str
    tx_hash: str


class MintRequest(BaseModel):
    project_id: str
    owner_wallet: str
    title: str
    description: str
    image_url: str


@app.post("/api/payment/create")
def payment_create(payload: PaymentCreate):
    return create_payment_intent(
        user_id=payload.user_id,
        project_id=payload.project_id,
        amount_ton=payload.amount_ton,
        purpose=payload.purpose,
    )


@app.post("/api/payment/verify")
def payment_verify(payload: PaymentVerify):
    ok = verify_payment_stub(payload.payment_id, payload.tx_hash)
    return {"ok": ok}


@app.post("/api/nft/mint")
def mint_nft(payload: MintRequest):
    projects = get_projects()
    if payload.project_id not in projects:
        return {"ok": False, "error": "Project not found"}

    return create_mint_request(
        project_id=payload.project_id,
        owner_wallet=payload.owner_wallet,
        title=payload.title,
        description=payload.description,
        image_url=payload.image_url,
    )