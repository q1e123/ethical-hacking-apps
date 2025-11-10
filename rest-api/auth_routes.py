from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from passlib.context import CryptContext
import sqlite3
import time
import os
import uuid

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 600        # 10 min
REFRESH_TOKEN_EXPIRE = 3600 * 24 # 1 day

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

security = HTTPBearer()

class RegisterModel(BaseModel):
    email: EmailStr
    password: str

class LoginModel(BaseModel):
    email: EmailStr
    password: str

#DB setup
def get_db():
    conn = sqlite3.connect("users.db")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            access_token TEXT,
            refresh_token TEXT,
            access_exp INTEGER,
            refresh_exp INTEGER
        )"""
    )
    return conn

#token utils
def create_token(data: dict, expires_in: int):
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(password, hashed):
    return pwd_context.verify(password, hashed)

def hash_password(password):
    return pwd_context.hash(password)

#register endpoint
@router.post("/register")
def register_user(body: RegisterModel):
    conn = get_db()
    cursor = conn.cursor()

    hashed_pwd = hash_password(body.password)
    
    # Generate a UUID for the new user
    user_id = str(uuid.uuid4())

    try:
        cursor.execute(
            "INSERT INTO users (id, email, password) VALUES (?, ?, ?)",
            (user_id, body.email, hashed_pwd)
        )
        conn.commit()
        
        # Create tokens with user_id (consistent with login)
        access_token = create_token({"user_id": user_id}, ACCESS_TOKEN_EXPIRE)
        refresh_token = create_token({"user_id": user_id}, REFRESH_TOKEN_EXPIRE)
        
        # Update the user record with the tokens
        cursor.execute(
            "UPDATE users SET access_token=?, refresh_token=?, access_exp=?, refresh_exp=? WHERE id=?",
            (access_token, refresh_token,
             int(time.time()) + ACCESS_TOKEN_EXPIRE,
             int(time.time()) + REFRESH_TOKEN_EXPIRE,
             user_id)
        )
        conn.commit()
        
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="User already registered")

    return {"access_token": access_token, "refresh_token": refresh_token}

#login endpoint
@router.post("/login")
def login_user(body: LoginModel):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password, refresh_token, refresh_exp FROM users WHERE email=?", (body.email,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=400, detail="User not found")

    user_id, hashed_pwd, refresh_token, refresh_exp = row

    # validate password
    if not verify_password(body.password, hashed_pwd):
        raise HTTPException(status_code=401, detail="Invalid password")

    now = int(time.time())
    if refresh_exp > now:
        # refresh valid -> reuse it, just issue new access_token
        new_access = create_token({"user_id": user_id}, ACCESS_TOKEN_EXPIRE)
        cursor.execute(
            "UPDATE users SET access_token=?, access_exp=? WHERE id=?",
            (new_access, now + ACCESS_TOKEN_EXPIRE, user_id)
        )
        conn.commit()
        return {"access_token": new_access}
    else:
        # refresh expired -> create new pair
        new_access = create_token({"user_id": user_id}, ACCESS_TOKEN_EXPIRE)
        new_refresh = create_token({"user_id": user_id}, REFRESH_TOKEN_EXPIRE)
        cursor.execute(
            "UPDATE users SET access_token=?, refresh_token=?, access_exp=?, refresh_exp=? WHERE id=?",
            (new_access, new_refresh, now + ACCESS_TOKEN_EXPIRE, now + REFRESH_TOKEN_EXPIRE, user_id)
        )
        conn.commit()
        return {"access_token": new_access, "refresh_token": new_refresh}

#Extract user id from token
def get_user_id_from_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token format")
        return str(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# FastAPI dependency for authentication
def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    FastAPI dependency that extracts and validates the bearer token.
    Returns the user UUID as a string.
    """
    return get_user_id_from_token(credentials.credentials)

# Alternative dependency that extracts from Authorization header manually
def get_user_from_header(authorization: str = Header(None)) -> str:
    """
    Alternative dependency that extracts token from Authorization header.
    Returns the user UUID as a string.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    # Handle both "Bearer token" and just "token" formats
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    elif authorization.startswith("bearer "):
        token = authorization[7:]
    
    return get_user_id_from_token(token)