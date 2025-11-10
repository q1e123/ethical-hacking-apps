from fastapi import FastAPI, Request
from fastapi.security import HTTPBearer
import get_routes
import post_routes
import bullshit
import uvicorn
import os
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from limiter_inst import limiter
import auth_routes

app = FastAPI(
    title="This is an API",
    description="API with JWT Bearer Token Authentication",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.include_router(post_routes.router)
app.include_router(get_routes.router)
app.include_router(auth_routes.router, prefix="/auth",tags=["auth"])

try:
    bullshit.stupid_test()
except Exception:
    pass

@app.get("/health")
def main():
    return {"Server": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("APP_PORT", 8000)))
