"""Small interfaces for storage implementations."""

from contextlib import AbstractContextManager
from typing import Protocol

from vdm.storage.sqlite import Domain


class Connection(Protocol):
    """Minimum SQL connection contract consumed by repositories."""

    def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> object:
        """Execute a parameterized statement."""


class Storage(Protocol):
    """Storage lifecycle and per-domain connection contract."""

    def initialize(self) -> None:
        """Create or migrate persistent stores."""

    def connect(self, domain: Domain) -> AbstractContextManager[Connection]:
        """Open a connection to one isolated domain."""
