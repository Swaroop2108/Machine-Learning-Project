import re
import time
from datetime import datetime
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Header, Depends

from backend.schemas import (
    RegisterRequest, VerifyEmailRequest, ResendCodeRequest, LoginRequest, SaveTripRequest
)
from backend.services.db_service import db_service
from backend.services.auth_service import (
    hash_password, verify_password, generate_verification_code, verify_code_hash,
    create_session_token, get_user_from_token, invalidate_session, MAX_VERIFICATION_ATTEMPTS
)
from backend.services.email_service import send_verification_email

auth_router = APIRouter()

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Track resend cooldowns in-memory (email -> last_sent_timestamp)
RESEND_COOLDOWNS: Dict[str, float] = {}
RESEND_COOLDOWN_SECONDS = 45

def get_current_user_from_header(authorization: Optional[str] = Header(None), x_auth_token: Optional[str] = Header(None)):
    token = None
    if x_auth_token:
        token = x_auth_token
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    if not token:
        raise HTTPException(status_code=401, detail="Authentication token required. Please log in.")

    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid token. Please log in again.")

    return user

@auth_router.post("/api/auth/register")
def register_endpoint(payload: RegisterRequest):
    email = payload.email.strip().lower()
    name = payload.name.strip()

    # 1. Validate email format
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    # 2. Validate passwords match
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Password and confirm password do not match.")

    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    # 3. Check duplicate email
    existing_user = db_service.get_user_by_email(email)
    if existing_user:
        if existing_user.get("is_verified"):
            raise HTTPException(status_code=400, detail="An account with this email already exists.")
        else:
            # Clean up unverified account to allow re-registration
            db_service.delete_user_by_email(email)

    # 4. Generate verification code & hash password
    pwd_hash = hash_password(payload.password)
    plain_code, code_hash, expiry_iso = generate_verification_code()

    # 5. Create user in DB
    user = db_service.create_user(
        name=name,
        email=email,
        password_hash=pwd_hash,
        verification_code_hash=code_hash,
        verification_expiry=expiry_iso
    )

    # 6. Send verification code email via SMTP
    email_sent, err_msg, error_case = send_verification_email(email, name, plain_code)

    if not email_sent:
        # Roll back created user since verification code could not be sent
        db_service.delete_user_by_email(email)
        raise HTTPException(status_code=500, detail=err_msg)

    return {
        "success": True,
        "message": f"Account created. A 6-digit verification code has been sent to {email}.",
        "email": email
    }

@auth_router.post("/api/auth/verify-email")
def verify_email_endpoint(payload: VerifyEmailRequest):
    email = payload.email.strip().lower()
    code = payload.code.strip()

    user = db_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=400, detail="User account not found. Please register first.")

    if user.get("is_verified"):
        return {"success": True, "message": "Email is already verified. You can now log in."}

    # Check attempt limit
    attempts = user.get("verification_attempts", 0)
    if attempts >= MAX_VERIFICATION_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Too many failed verification attempts. Please request a new code.")

    # Check expiry
    expiry_str = user.get("verification_expiry")
    if expiry_str:
        try:
            expiry_dt = datetime.fromisoformat(expiry_str)
            if datetime.now() > expiry_dt:
                raise HTTPException(status_code=400, detail="Verification code expired. Please request a new code.")
        except ValueError:
            pass

    # Verify code hash
    stored_hash = user.get("verification_code_hash", "")
    if not verify_code_hash(code, stored_hash):
        db_service.increment_verification_attempts(email)
        raise HTTPException(status_code=400, detail="Incorrect verification code.")

    # Mark verified
    db_service.mark_email_verified(email)

    return {
        "success": True,
        "message": "Email verified successfully! You can now log in."
    }

@auth_router.post("/api/auth/resend-code")
def resend_code_endpoint(payload: ResendCodeRequest):
    email = payload.email.strip().lower()
    user = db_service.get_user_by_email(email)

    if not user:
        raise HTTPException(status_code=400, detail="User account not found.")

    if user.get("is_verified"):
        return {"success": True, "message": "Email is already verified."}

    # Cooldown check
    now = time.time()
    last_sent = RESEND_COOLDOWNS.get(email, 0)
    if now - last_sent < RESEND_COOLDOWN_SECONDS:
        remaining = int(RESEND_COOLDOWN_SECONDS - (now - last_sent))
        raise HTTPException(status_code=429, detail=f"Please wait {remaining} seconds before requesting a new code.")

    plain_code, code_hash, expiry_iso = generate_verification_code()
    db_service.update_verification_code(email, code_hash, expiry_iso)

    email_sent, err_msg, error_case = send_verification_email(email, user.get("name", "User"), plain_code)

    if not email_sent:
        raise HTTPException(status_code=500, detail=err_msg)

    RESEND_COOLDOWNS[email] = now

    return {
        "success": True,
        "message": "Verification code sent successfully."
    }


@auth_router.post("/api/auth/login")
def login_endpoint(payload: LoginRequest):
    email = payload.email.strip().lower()
    password = payload.password

    user = db_service.get_user_by_email(email)
    if not user or not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Incorrect email or password.")

    if not user.get("is_verified"):
        raise HTTPException(status_code=403, detail="Please verify your email before logging in.")

    token = create_session_token(user["id"])

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "is_verified": user["is_verified"]
        }
    }

@auth_router.get("/api/auth/me")
def get_me_endpoint(user: dict = Depends(get_current_user_from_header)):
    return {
        "success": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "is_verified": user["is_verified"],
            "created_at": user.get("created_at")
        }
    }

@auth_router.post("/api/auth/logout")
def logout_endpoint(authorization: Optional[str] = Header(None), x_auth_token: Optional[str] = Header(None)):
    token = x_auth_token or (authorization.split(" ")[1] if authorization and authorization.startswith("Bearer ") else None)
    if token:
        invalidate_session(token)
    return {"success": True, "message": "Logged out successfully."}

# ================= MY TRIPS ENDPOINTS =================

@auth_router.get("/api/trips")
def get_user_trips_endpoint(user: dict = Depends(get_current_user_from_header)):
    trips = db_service.get_user_trips(user["id"])
    return {
        "success": True,
        "count": len(trips),
        "trips": trips
    }

@auth_router.post("/api/trips")
def save_user_trip_endpoint(payload: SaveTripRequest, user: dict = Depends(get_current_user_from_header)):
    trip = db_service.save_trip(
        user_id=user["id"],
        source=payload.source,
        destination=payload.destination,
        distance_km=payload.distance_km,
        travel_mode=payload.travel_mode,
        estimated_duration=payload.estimated_duration,
        traffic_condition=payload.traffic_condition,
        departure_time=payload.departure_time,
        eta=payload.eta
    )
    return {
        "success": True,
        "message": "Trip saved to history.",
        "trip": trip
    }
