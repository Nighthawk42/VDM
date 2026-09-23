"""Replace only the VDM site handler in z1-hestia's Caddyfile.

This script backs up the original file and validates the changed configuration
before asking Caddy to reload. It restores the original on failure.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def run(command: list[str]) -> None:
    """Run a command and fail on a nonzero exit code."""
    subprocess.run(command, check=True)


def replacement(original: str) -> str:
    """Replace the known old VDM handler while preserving site access controls."""
    site = original.index("vdm.nighthawk.moe {")
    start = original.index("    handle @local {", site)
    end = original.index("    # Abort connection silently for external IPs", start)
    old_handler = original[start:end]
    if "127.0.0.1:18600" not in old_handler or "root * /srv/vdm" not in old_handler:
        raise ValueError("VDM handler no longer matches the expected old deployment")
    new_handler = (
        "    handle @local {\n"
        "        encode zstd gzip\n"
        "        reverse_proxy 127.0.0.1:18610\n"
        "    }\n"
    )
    return original[:start] + new_handler + original[end:]


def main() -> None:
    """Back up, switch, validate, and reload one Caddy site."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    path: Path = args.config
    original = path.read_text(encoding="utf-8")
    updated = replacement(original)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.vdm-{stamp}.bak")
    shutil.copy2(path, backup)
    caddy_command = ["docker", "exec", "caddy", "caddy"]
    config_args = ["--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
    try:
        # Caddy has this file bind-mounted. Edit its contents without replacing its inode.
        path.write_text(updated, encoding="utf-8")
        run([*caddy_command, "validate", *config_args])
        run([*caddy_command, "reload", *config_args])
    except (OSError, subprocess.CalledProcessError):
        path.write_text(original, encoding="utf-8")
        run([*caddy_command, "reload", *config_args])
        raise
    print(f"VDM route switched to port 18610; backup: {backup}")


if __name__ == "__main__":
    main()
