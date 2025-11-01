from fastapi.routing import APIRouter
from fastapi import Query, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from file_operations import validate, validate_user_file, get_user_folder
import base64
import aiofiles
import json
from typing import Optional
from jwt_mock import get_user_id
from post_routes import user_key
from limiter_inst import limiter

router = APIRouter()

def _read_b64_sync(path: str):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

async def _read_b64_async(path: str):
    async with aiofiles.open(path, "rb") as fp:
        bytes = await fp.read()
        return base64.b64encode(bytes).decode()

@router.get("/file")
@limiter.limit("10/minute", key_func=user_key)
async def _get_file(request: Request, path: str = Query(...), mode: Optional[str] = Query("base64")):
    user_id = get_user_id(request)

    if path is None or str(path).strip() == "":
        raise HTTPException(status_code=400, detail="Path should not be None or empty.")

    # try:
    #     validated_path = validate(path)
    # except Exception:
    #     raise HTTPException(status_code=400, detail="Failed to validate path.")

    try:
        validated_path = validate_user_file(path, user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path.")
    
    if (not validated_path.exists()) or (not validated_path.is_file()):
        raise HTTPException(status_code=404, detail="File does not exist or is not a file.")

    m = (mode or "base64").lower()
    if m == "download":
        return FileResponse(path=validated_path.as_posix(), media_type="application/octet-stream", filename=validated_path.name)

    try:
        b64 = await _read_b64_async(str(validated_path))
    except Exception:
        b64 = _read_b64_sync(str(validated_path))

    # response = {"path": validated_path.relative_to(validated_path.parent).as_posix(), "content": b64}

    # return PlainTextResponse(json.dumps(response), media_type="application/json")

    response = {
        "path": str(validated_path.relative_to(get_user_folder(user_id))),
        "content": b64
    }

    return PlainTextResponse(json.dumps(response), media_type="application/json")


# router.get("/file")(_get_file)