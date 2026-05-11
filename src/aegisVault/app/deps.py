import hashlib
import os
import secrets
from fastapi import HTTPException, Header, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

# Setup Limiter
limiter = Limiter(key_func=get_remote_address)

# Cache hashed keys at startup
_API_KEYS_HASHED = {}
def init_api_keys():
    global _API_KEYS_HASHED
    _API_KEYS_HASHED = {}
    keys = os.environ.get("API_KEYS", os.environ.get("API_KEY", ""))
    for key in keys.split(","):
        key = key.strip()
        if key:
            # Hash the key to prevent timing attacks and store by prefix
            _API_KEYS_HASHED[key[:4]] = hashlib.sha256(key.encode()).digest()

init_api_keys()

def verify_api_key(request: Request, x_api_key: str = Header(..., alias="X-API-Key")):
    if not _API_KEYS_HASHED:
        raise HTTPException(status_code=503, detail="API keys are not configured")
        
    prefix = x_api_key[:4]
    expected_hash = _API_KEYS_HASHED.get(prefix)
    
    if expected_hash is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
        
    actual_hash = hashlib.sha256(x_api_key.encode()).digest()
    if not secrets.compare_digest(actual_hash, expected_hash):
        raise HTTPException(status_code=401, detail="Invalid API key")
        
    request.state.api_key_prefix = prefix
    return prefix
