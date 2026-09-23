"""Take a consistent snapshot of the prior VDM SQLite database."""

import argparse
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    """Use SQLite's backup API while the old service is still running."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--backup-dir", required=True, type=Path)
    args = parser.parse_args()
    source: Path = args.source
    destination_dir: Path = args.backup_dir
    if not source.is_file():
        raise FileNotFoundError(source)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_dir.chmod(0o700)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = destination_dir / f"vdm_core-{stamp}.db"
    with (
        sqlite3.connect(f"file:{source}?mode=ro", uri=True) as old,
        sqlite3.connect(destination) as backup,
    ):
        old.backup(backup)
    destination.chmod(0o600)
    print(destination)


if __name__ == "__main__":
    main()
