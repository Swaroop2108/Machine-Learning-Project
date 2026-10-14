import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from backend.config import BASE_DIR

# MongoDB Optional Import
try:
    from pymongo import MongoClient
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

MONGO_URI = os.getenv("MONGO_URI", "").strip()
DB_NAME = os.getenv("MONGO_DB_NAME", "wayvista").strip()

class DatabaseService:
    def __init__(self):
        self.use_mongo = False
        self.mongo_client = None
        self.mongo_db = None

        if PYMONGO_AVAILABLE and MONGO_URI:
            try:
                self.mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
                # Quick server check
                self.mongo_client.admin.command('ping')
                self.mongo_db = self.mongo_client[DB_NAME]
                self.use_mongo = True
                print(f"[DatabaseService] Connected successfully to MongoDB database: {DB_NAME}")
            except Exception as e:
                print(f"[DatabaseService] MongoDB connection notice ({e}). Falling back to SQLite local database.")
                self.use_mongo = False
        else:
            if not PYMONGO_AVAILABLE:
                print("[DatabaseService] pymongo module not configured. Using SQLite database.")
            else:
                print("[DatabaseService] MONGO_URI not set. Using SQLite local database.")

        if not self.use_mongo:
            self.db_dir = BASE_DIR / "backend" / "data"
            self.db_dir.mkdir(parents=True, exist_ok=True)
            self.sqlite_path = self.db_dir / "wayvista.db"
            self._init_sqlite()

    def _init_sqlite(self):
        """Initialize SQLite tables for users and trips."""
        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_verified INTEGER DEFAULT 0,
                    verification_code_hash TEXT,
                    verification_expiry TEXT,
                    verification_attempts INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trips (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    distance_km REAL NOT NULL,
                    travel_mode TEXT NOT NULL,
                    estimated_duration TEXT NOT NULL,
                    traffic_condition TEXT NOT NULL,
                    departure_time TEXT NOT NULL,
                    eta TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            conn.commit()

    # ================= USER OPERATIONS =================

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        clean_email = email.strip().lower()
        if self.use_mongo:
            user = self.mongo_db.users.find_one({"email": clean_email})
            if user:
                user["id"] = str(user.get("id", user.get("_id")))
                user["is_verified"] = bool(user.get("is_verified", False))
                return user
            return None
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE email = ?", (clean_email,))
                row = cursor.fetchone()
                if row:
                    user_dict = dict(row)
                    user_dict["is_verified"] = bool(user_dict["is_verified"])
                    return user_dict
                return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self.use_mongo:
            user = self.mongo_db.users.find_one({"id": user_id})
            if user:
                user["id"] = str(user.get("id", user.get("_id")))
                user["is_verified"] = bool(user.get("is_verified", False))
                return user
            return None
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    user_dict = dict(row)
                    user_dict["is_verified"] = bool(user_dict["is_verified"])
                    return user_dict
                return None

    def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        verification_code_hash: str,
        verification_expiry: str
    ) -> Dict[str, Any]:
        user_id = str(uuid.uuid4())
        clean_email = email.strip().lower()
        created_at = datetime.now().isoformat()

        user_doc = {
            "id": user_id,
            "name": name.strip(),
            "email": clean_email,
            "password_hash": password_hash,
            "is_verified": False,
            "verification_code_hash": verification_code_hash,
            "verification_expiry": verification_expiry,
            "verification_attempts": 0,
            "created_at": created_at
        }

        if self.use_mongo:
            self.mongo_db.users.insert_one(user_doc)
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (id, name, email, password_hash, is_verified, verification_code_hash, verification_expiry, verification_attempts, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, name.strip(), clean_email, password_hash, 0, verification_code_hash, verification_expiry, 0, created_at))
                conn.commit()

        return user_doc

    def delete_user_by_email(self, email: str):
        clean_email = email.strip().lower()
        if self.use_mongo:
            self.mongo_db.users.delete_one({"email": clean_email})
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE email = ?", (clean_email,))
                conn.commit()

    def update_verification_code(self, email: str, verification_code_hash: str, verification_expiry: str):

        clean_email = email.strip().lower()
        if self.use_mongo:
            self.mongo_db.users.update_one(
                {"email": clean_email},
                {"$set": {
                    "verification_code_hash": verification_code_hash,
                    "verification_expiry": verification_expiry,
                    "verification_attempts": 0
                }}
            )
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users
                    SET verification_code_hash = ?, verification_expiry = ?, verification_attempts = 0
                    WHERE email = ?
                """, (verification_code_hash, verification_expiry, clean_email))
                conn.commit()

    def increment_verification_attempts(self, email: str):
        clean_email = email.strip().lower()
        if self.use_mongo:
            self.mongo_db.users.update_one(
                {"email": clean_email},
                {"$inc": {"verification_attempts": 1}}
            )
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET verification_attempts = verification_attempts + 1 WHERE email = ?", (clean_email,))
                conn.commit()

    def mark_email_verified(self, email: str):
        clean_email = email.strip().lower()
        if self.use_mongo:
            self.mongo_db.users.update_one(
                {"email": clean_email},
                {"$set": {
                    "is_verified": True,
                    "verification_code_hash": None,
                    "verification_expiry": None,
                    "verification_attempts": 0
                }}
            )
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users
                    SET is_verified = 1, verification_code_hash = NULL, verification_expiry = NULL, verification_attempts = 0
                    WHERE email = ?
                """, (clean_email,))
                conn.commit()

    # ================= TRIP OPERATIONS =================

    def save_trip(
        self,
        user_id: str,
        source: str,
        destination: str,
        distance_km: float,
        travel_mode: str,
        estimated_duration: str,
        traffic_condition: str,
        departure_time: str,
        eta: str
    ) -> Dict[str, Any]:
        trip_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()

        trip_doc = {
            "id": trip_id,
            "user_id": user_id,
            "source": source,
            "destination": destination,
            "distance_km": float(distance_km),
            "travel_mode": travel_mode,
            "estimated_duration": estimated_duration,
            "traffic_condition": traffic_condition,
            "departure_time": departure_time,
            "eta": eta,
            "created_at": created_at
        }

        if self.use_mongo:
            self.mongo_db.trips.insert_one(trip_doc)
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO trips (id, user_id, source, destination, distance_km, travel_mode, estimated_duration, traffic_condition, departure_time, eta, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (trip_id, user_id, source, destination, distance_km, travel_mode, estimated_duration, traffic_condition, departure_time, eta, created_at))
                conn.commit()

        return trip_doc

    def get_user_trips(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        if self.use_mongo:
            trips = list(self.mongo_db.trips.find({"user_id": user_id}).sort("created_at", -1).limit(limit))
            for t in trips:
                t["id"] = str(t.get("id", t.get("_id")))
                if "_id" in t:
                    del t["_id"]
            return trips
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM trips WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
                """, (user_id, limit))
                return [dict(row) for row in cursor.fetchall()]

# Singleton Database Instance
db_service = DatabaseService()
