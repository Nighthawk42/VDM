# server/user_manager.py
import uuid
from typing import Dict, Optional, Tuple, TypedDict, Any

from passlib.context import CryptContext

from .logger import logger
from .database_manager import DatabaseManager

# These TypedDicts define the shape of user data for different contexts.
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

# CryptContext for hashing and verifying user passwords securely.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserManager:
    """
    Manages player registration and authentication using the SQLite database.
    - Stores users with hashed passwords for persistence.
    - Issues temporary in-memory session tokens upon successful login.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initializes the UserManager with a database manager instance.

        Args:
            db_manager: An active instance of the DatabaseManager.
        """
        self.db = db_manager
        # Sessions are kept in memory. A server restart will log everyone out.
        self._sessions: Dict[str, str] = {}
        logger.info("UserManager initialized with database backend.")

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

        # Check if user already exists in the database
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
        Verifies user credentials against the database and creates a session token.

        Args:
            name: The username to log in with.
            password: The plain-text password.

        Returns:
            A dictionary with client-safe user data if successful, otherwise None.
        """
        user_data = self.db.get_user_by_name(name)
        if not user_data:
            return None

        if not self._verify_password(password, user_data["hashed_password"]):
            return None

        session_token = str(uuid.uuid4())
        # Store the correctly-cased username in the session map
        self._sessions[session_token] = user_data["username_cased"]
        logger.info(f"Player '{user_data['username_cased']}' logged in successfully.")

        client_data: ClientUserData = {
            "name": user_data["username_cased"],
            "avatar_style": user_data["avatar_style"],
            "token": session_token
        }
        return client_data

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Finds a user's full data from the database using their session token.

        Args:
            token: The user's active session token.

        Returns:
            A dictionary with the user's database record if the token is valid,
            otherwise None.
        """
        username = self._sessions.get(token)
        if not username:
            return None
        
        # Fetch fresh user data from the database
        return self.db.get_user_by_name(username)

    def logout(self, token: str):
        """
        Removes a session token, effectively logging the user out.

        Args:
            token: The session token to invalidate.
        """
        if token in self._sessions:
            del self._sessions[token]
            logger.info(f"Session token {token[:8]}... ended.")