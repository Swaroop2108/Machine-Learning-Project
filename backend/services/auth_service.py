import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from backend.services.db_service import db_service

# Active User Sessions Store (token -> { user_id, expires_at })
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSION_EXPIRY_HOURS = 24
MAX_VERIFICATION_ATTEMPTS = 5
VERIFICATION_CODE_EXPIRY_MINUTES = 10

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${key}"

def verify_password(password: str, password_hash: str) -> bool:
    """Verify plain password against stored salted hash."""
    try:
        parts = password_hash.split("$")
        if len(parts) != 2:
            return False
        salt, stored_key = parts[0], parts[1]
        computed_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return secrets.compare_digest(stored_key, computed_key)
    except Exception:
        return False

def generate_verification_code() -> Tuple[str, str, str]:
    """
    Generates a random 6-digit verification code, returns (plain_code, code_hash, expiry_iso).
    Plain code is used ONLY for sending email and is NEVER stored or logged!
    """
    plain_code = f"{secrets.randbelow(900000) + 100000}"
    salt = secrets.token_hex(8)
    code_hash = hashlib.sha256((plain_code + salt).encode('utf-8')).hexdigest() + f"${salt}"
    expiry_dt = datetime.now() + timedelta(minutes=VERIFICATION_CODE_EXPIRY_MINUTES)
    return plain_code, code_hash, expiry_dt.isoformat()

def verify_code_hash(input_code: str, stored_code_hash: str) -> bool:
    """Verifies input code against stored hashed verification code."""
    try:
        if not stored_code_hash or "$" not in stored_code_hash:
            return False
        stored_hash, salt = stored_code_hash.split("$")
        computed_hash = hashlib.sha256((input_code.strip() + salt).encode('utf-8')).hexdigest()
        return secrets.compare_digest(stored_hash, computed_hash)
    except Exception:
        return False

def create_session_token(user_id: str) -> str:
    """Creates a secure session token valid for 24 hours."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS)
    ACTIVE_SESSIONS[token] = {
        "user_id": user_id,
        "expires_at": expires_at
    }
    return token

def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Validates session token and returns active user profile."""
    if not token or token not in ACTIVE_SESSIONS:
        return None
    
    session = ACTIVE_SESSIONS[token]
    if datetime.now() > session["expires_at"]:
        del ACTIVE_SESSIONS[token]
        return None
    
    return db_service.get_user_by_id(session["user_id"])

def invalidate_session(token: str):
    """Invalidates session token on logout."""
    if token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
