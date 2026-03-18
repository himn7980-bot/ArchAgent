import json
import os
import uuid
from typing import Any, Dict

from config import DATA_DIR

os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
PROJECTS_FILE = os.path.join(DATA_DIR, "projects.json")
PAYMENTS_FILE = os.path.join(DATA_DIR, "payments.json")
NFTS_FILE = os.path.join(DATA_DIR, "nfts.json")


def _load(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_users():
    return _load(USERS_FILE)


def save_users(data):
    _save(USERS_FILE, data)


def get_projects():
    return _load(PROJECTS_FILE)


def save_projects(data):
    _save(PROJECTS_FILE, data)


def get_payments():
    return _load(PAYMENTS_FILE)


def save_payments(data):
    _save(PAYMENTS_FILE, data)


def get_nfts():
    return _load(NFTS_FILE)


def save_nfts(data):
    _save(NFTS_FILE, data)


def create_project(user_id: str, payload: Dict[str, Any]) -> str:
    data = get_projects()
    project_id = str(uuid.uuid4())
    data[project_id] = payload | {"user_id": user_id}
    save_projects(data)
    return project_id