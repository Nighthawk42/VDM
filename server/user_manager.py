# server/user_manager.py
import json
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple, TypedDict

from passlib.context import CryptContext

from .config import settings
from .logger import logger

class StoredUserData(TypedDict):
    name: str
    avatar_style: str
    hashed_password: str

class ClientUserData(TypedDict):
    token: str
    name: str
    avatar_style: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserManager:
    """
    Manages player registration and authentication using a simple JSON file.
    - Stores users with hashed passwords for persistence.
    - Issues temporary session tokens upon successful login.
    """

    def __init__(self):
        """Initializes the UserManager and loads user data."""
        # FIX: Updated to use the new setting path from the reorganized config.
        self.users_file = Path(settings.paths.memory_dir) / "users.json"
        
        self._users_by_name: Dict[str, StoredUserData] = {}
        self._sessions: Dict[str, str] = {}
        
        self._load_users()

    def _load_users(self):
        """Loads the users.json file into memory."""
        try:
            if self.users_file.exists():
                with open(self.users_file, "r", encoding="utf-8") as f:
                    loaded_data: Dict[str, Dict[str, str]] = json.load(f)
                    
                    for name, data in loaded_data.items():
                        if "avatar_style" in data and "hashed_password" in data:
                            user: StoredUserData = {
                                "name": name,
                                "avatar_style": data["avatar_style"],
                                "hashed_password": data["hashed_password"]
                            }
                            self._users_by_name[name.lower()] = user
                        else:
                            logger.warning(f"Skipping malformed user entry for '{name}' in users.json.")

                logger.info(f"Loaded {len(self._users_by_name)} users from {self.users_file}")
            else:
                logger.info("No users.json file found. A new one will be created upon registration.")
        except Exception:
            logger.error(f"Failed to load or parse {self.users_file}.", exc_info=True)

    def _save_users(self):
        """Saves the current user data to users.json."""
        try:
            data_to_save = {
                user["name"]: {
                    "avatar_style": user["avatar_style"],
                    "hashed_password": user["hashed_password"]
                }
                for user in self._users_by_name.values()
            }
            with open(self.users_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2)
        except Exception:
            logger.error(f"Failed to save users to {self.users_file}.", exc_info=True)

    def _get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def register_player(self, name: str, avatar_style: str, password: str) -> Tuple[bool, str]:
        """
        Registers a new player name, avatar style, and password.
        Returns a tuple of (success, message).
        """
        if not (3 <= len(name) <= 20):
            return False, "Player name must be between 3 and 20 characters."
        if len(password) < 8:
            return False, "Password must be at least 8 characters long."

        if name.lower() in self._users_by_name:
            return False, "Player name is already registered."

        hashed_password = self._get_password_hash(password)
        
        new_user: StoredUserData = {
            "name": name,
            "avatar_style": avatar_style,
            "hashed_password": hashed_password,
        }
        
        self._users_by_name[name.lower()] = new_user
        self._save_users()
        
        logger.info(f"Registered new player '{name}'.")
        return True, "Registration successful. You can now log in."

    def login(self, name: str, password: str) -> Optional[ClientUserData]:
        """
        Verifies a user's credentials. If successful, creates a new session
        token and returns the client-safe user data.
        """
        user = self._users_by_name.get(name.lower())
        if not user:
            return None
        
        if not self._verify_password(password, user["hashed_password"]):
            return None
        
        session_token = str(uuid.uuid4())
        self._sessions[session_token] = user["name"]
        
        logger.info(f"Player '{user['name']}' logged in successfully. Session token created.")
        
        client_data: ClientUserData = {
            "name": user["name"],
            "avatar_style": user["avatar_style"],
            "token": session_token
        }
        return client_data

    def get_user_by_token(self, token: str) -> Optional[StoredUserData]:
        """Finds a user's data using their active session token."""
        username = self._sessions.get(token)
        if not username:
            return None
            
        return self._users_by_name.get(username.lower())
    
    def logout(self, token: str):
        """Removes a session token, effectively logging the user out."""
        if token in self._sessions:
            del self._sessions[token]
            logger.info(f"Session token {token[:8]}... ended.")