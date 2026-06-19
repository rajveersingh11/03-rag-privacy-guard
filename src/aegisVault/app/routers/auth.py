"""
Auth Router
-----------
Endpoints for admin registration (signup) and login.
"""

import uuid
import hashlib
import os
import secrets
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from aegisVault.db.session import get_db
from aegisVault.utils.common import get_logger

logger = get_logger(__name__)

router = APIRouter()

class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)

class AuthResponse(BaseModel):
    status: str
    username: str
    role: str
    api_key: str

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 100000
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations
    )
    return f"{salt}${iterations}${key.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, iterations, key_hex = hashed.split('$')
        iterations = int(iterations)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )
        return secrets.compare_digest(key.hex(), key_hex)
    except Exception:
        return False

@router.post("/signup", response_model=AuthResponse)
def signup(req: AuthRequest, db: Session = Depends(get_db)):
    # Check if username already exists
    try:
        check_user = db.execute(
            text("SELECT username FROM users WHERE username = :username"),
            {"username": req.username}
        ).fetchone()
        
        if check_user:
            raise HTTPException(status_code=400, detail="Username is already taken")
            
        pass_hash = hash_password(req.password)
        user_id = str(uuid.uuid4())
        
        db.execute(
            text("""
                INSERT INTO users (id, username, password_hash, role)
                VALUES (:id, :username, :password_hash, :role)
            """),
            {
                "id": user_id,
                "username": req.username,
                "password_hash": pass_hash,
                "role": "admin"
            }
        )
        db.commit()
        
        api_key = os.environ.get("API_KEY", "change-me-at-least-32-chars")
        
        return AuthResponse(
            status="success",
            username=req.username,
            role="admin",
            api_key=api_key
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database registration failed: {str(e)}")

@router.post("/login", response_model=AuthResponse)
def login(req: AuthRequest, db: Session = Depends(get_db)):
    try:
        user = db.execute(
            text("SELECT username, password_hash, role FROM users WHERE username = :username"),
            {"username": req.username}
        ).fetchone()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
            
        # Verify password
        if not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
            
        api_key = os.environ.get("API_KEY", "change-me-at-least-32-chars")
        
        return AuthResponse(
            status="success",
            username=user.username,
            role=user.role,
            api_key=api_key
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database login check failed: {str(e)}")
