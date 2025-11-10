from fastapi.routing import APIRouter
from fastapi import UploadFile, File, HTTPException, Request, Depends
import aiofiles
import time
from file_operations import safe_file_name, destination, max_size, change, validate, validate_user_file, get_user_folder, get_user_quota_used
from auth_routes import get_current_user_id
from limiter_inst import limiter

router = APIRouter()
_READ_SIZE = (1 << 16)
USER_MAX_QUOTA = 1 * 1024 ** 3

def user_key(request: Request):
    # Extract token from Authorization header for rate limiting
    token = request.headers.get("Authorization", "")
    if token.startswith("Bearer "):
        token = token[7:]
    try:
        from auth_routes import get_user_id_from_token
        user_id = get_user_id_from_token(token)
        return f"user:{user_id}"
    except:
        return "anonymous"

@router.post("/file")
@limiter.limit("10/minute", key_func=user_key)
async def _save_file(
    request: Request, 
    file: UploadFile = File(..., description="File to upload"),
    user_id: str = Depends(get_current_user_id)
):
    file_name = getattr(file, "filename", None)

    try:
        safe = safe_file_name(file_name)
    except Exception as ex:
        raise HTTPException(status_code=400, detail=ex)

    try:
        dst = validate_user_file(safe, user_id)
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))

    if dst.exists(): # If destination already exists create a new file with the current time
        stem = dst.stem
        suffix = dst.suffix
        safe = ("%s_%d%s") % (stem, int(time.time()), suffix)
        # dst = destination() / safe
        dst = dst.parent / safe

    quota_used = get_user_quota_used(user_id)
    size = 0
    try:
        async with aiofiles.open(dst, "wb") as o:
            while True:
                bytes_read = await file.read(_READ_SIZE)
                if not bytes_read:
                    break

                size += len(bytes_read)
                if size > max_size():
                    try:
                        await o.close()
                    except Exception:
                        pass

                    try:
                        dst.unlink(missing_ok=True)
                    except Exception:
                        pass

                    raise HTTPException(status_code=413, detail="File size is to large.")
                
                # Check per-user quota dynamically
                if quota_used + size > USER_MAX_QUOTA:
                    try:
                        await o.close()
                    except Exception:
                        pass
                    try:
                        dst.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise HTTPException(status_code=400, detail="User quota exceeded (1GB max).")
                
                await o.write(bytes_read)
    finally:
        try:
            await file.close()
        except Exception:
            pass

    relative = dst.relative_to(dst.parent).as_posix()
    return {
        "response": "ok",
        "path": relative,
        "size": size,
        "stripped_path": change(relative)
    }