from pathlib import Path
import re
import time

_CURRENT_SCRIPT_FOLDER = Path(__file__).parent.resolve()
_UPLOAD_FOLDER = (_CURRENT_SCRIPT_FOLDER / "uploads").resolve()
_UPLOAD_FOLDER.mkdir(exist_ok=True)

_MAX_SIZE = (1 << 20) * 10
_RX = re.compile(r"[^A-Za-z0-9_.-]")

def safe_file_name(path: str) -> str:
    try:
        name_of_path = Path(path).name
    except Exception:
        raise ValueError("name could not be converted to Path")

    name_of_path = _RX.sub("_", name_of_path)
    name_of_path = re.sub(r"^\.+", "", name_of_path)

    if not name_of_path:
       name_of_path = f"f_{int(time.time())}"

    return name_of_path

def destination() -> Path:
    return _UPLOAD_FOLDER

def max_size() -> int:
    return _MAX_SIZE

def validate(path: str) -> Path:
    save_to = (destination() / path).resolve()
    try:
        save_to.relative_to(destination())
    except Exception:
        raise ValueError("Bad path provided, need to be relative.")

def validate_user_file(path: str, user_id: str) -> Path:
    user_folder = destination() / user_id
    user_folder.mkdir(parents=True, exist_ok=True)

    save_to = (user_folder / path).resolve()
    try:
        save_to.relative_to(user_folder)
    except Exception:
        raise ValueError("Bad path provided; must be relative to user folder.")

    return save_to

    return save_to

def change(relative_path: str) -> str:
    return relative_path.replace("../", "").lstrip("/")

def get_user_folder(user_id: str) -> Path:
    folder = destination() / user_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_user_quota_used(user_id: str) -> int:
    folder = get_user_folder(user_id)
    total = sum(f.stat().st_size for f in folder.glob("*") if f.is_file())
    return total
