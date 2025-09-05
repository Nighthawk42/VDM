# server/user_manager.py
import uuid
from typing import Dict, Optional, Tuple, TypedDict, Any

from passlib.context import CryptContext

from .logger import logger
from .database_manager import DatabaseManager

# TypedDicts remain unchanged
class StoredUserData(TypedDict):
    """Represents the data shape of a user record from the database."""
    username_cased: str
    avatar_style: str
    hashed_password: str

class ClientUserData(TypedDict):
    """Represents the user data sent to the client upon successful login."""
    token: str
    name: str
    avatar_style: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserManager:
    """
    Manages player registration and authentication using the SQLite database.
    - Stores users and persistent session tokens in the database.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initializes the UserManager with a database manager instance.

        Args:
            db_manager: An active instance of the DatabaseManager.
        """
        self.db = db_manager
        # REMOVED: The in-memory session dictionary is no longer needed.
        # self._sessions: Dict[str, str] = {}
        logger.info("UserManager initialized with database backend for users and sessions.")

    def _get_password_hash(self, password: str) -> str:
        """Hashes a plain-text password."""
        return pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifies a plain-text password against a stored hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def register_player(self, name: str, avatar_style: str, password: str) -> Tuple[bool, str]:
        """
        Registers a new player in the database.

        Args:
            name: The desired username.
            avatar_style: The chosen avatar style.
            password: The plain-text password.

        Returns:
            A tuple containing a success boolean and a status message.
        """
        if not (3 <= len(name) <= 20):
            return False, "Player name must be between 3 and 20 characters."
        if len(password) < 8:
            return False, "Password must be at least 8 characters long."

        if self.db.get_user_by_name(name):
            return False, "Player name is already registered."

        hashed_password = self._get_password_hash(password)
        success = self.db.add_user(name, hashed_password, avatar_style)

        if success:
            logger.info(f"Registered new player '{name}'.")
            return True, "Registration successful. You can now log in."
        else:
            return False, "An unexpected error occurred during registration."

    def login(self, name: str, password: str) -> Optional[ClientUserData]:
        """
        Verifies user credentials and creates a persistent session in the database.

        Returns:
            A dictionary with client-safe user data if successful, otherwise None.
        """
        user_data = self.db.get_user_by_name(name)
        if not user_data:
            return None

        if not self._verify_password(password, user_data["hashed_password"]):
            return None

        session_token = str(uuid.uuid4())
        
        # UPDATED: Create the session in the database instead of in memory.
        username_cased = user_data["username_cased"]
        if not self.db.create_session(session_token, username_cased):
            logger.error(f"Failed to create database session for user '{username_cased}'")
            return None

        logger.info(f"Player '{username_cased}' logged in. DB session created.")

        client_data: ClientUserData = {
            "name": username_cased,
            "avatar_style": user_data["avatar_style"],
            "token": session_token
        }
        return client_data

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Finds a user's data from the DB using their persistent session token.

        Returns:
            A dictionary with the user's database record if the token is valid.
        """
        # UPDATED: Validate the token against the database.
        session = self.db.get_session_by_token(token)
        if not session:
            return None
        
        # Session is valid, now fetch the full user data using the username from the session.
        return self.db.get_user_by_name(session["username_lower"])

    def logout(self, token: str):
        """
        Deletes a session token from the database.

        Args:
            token: The session token to invalidate.
        """
        if self.db.delete_session(token):
            logger.info(f"Session token {token[:8]}... deleted from database.")