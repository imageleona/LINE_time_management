import json
import os
import tempfile
from datetime import datetime

STATE_FILE = "state.json"


def load_state() -> dict:
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    dir_name = os.path.dirname(os.path.abspath(STATE_FILE))
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, suffix=".tmp") as tmp:
        json.dump(state, tmp)
        tmp_path = tmp.name
    os.replace(tmp_path, STATE_FILE)


def get_active(user_id: str) -> dict | None:
    state = load_state()
    return state.get(user_id)


def set_active(user_id: str, task: str, start_time: datetime) -> None:
    state = load_state()
    state[user_id] = {
        "task": task,
        "start_time": start_time.isoformat(),
    }
    save_state(state)


def clear_active(user_id: str) -> None:
    state = load_state()
    state.pop(user_id, None)
    save_state(state)
