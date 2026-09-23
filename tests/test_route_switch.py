"""Protect unrelated Caddy sites when switching the VDM route."""

import pytest
from deploy.switch_vdm_route import replacement


def test_replacement_keeps_other_sites_and_access_guard() -> None:
    """Only the known VDM handler changes."""
    source = """other.example {
    respond 200
}
vdm.nighthawk.moe {
    import local_only
    handle @local {
        route {
            root * /srv/vdm
            reverse_proxy 127.0.0.1:18600
        }
    }
    # Abort connection silently for external IPs
    handle {
        abort
    }
}
"""
    result = replacement(source)
    assert "other.example {\n    respond 200\n}" in result
    assert "reverse_proxy 127.0.0.1:18610" in result
    assert "import local_only" in result
    assert "handle {\n        abort\n    }" in result
    assert "127.0.0.1:18600" not in result


def test_replacement_rejects_unexpected_route() -> None:
    """A changed VDM site requires a fresh review before editing."""
    with pytest.raises(ValueError, match="expected old deployment"):
        replacement(
            "vdm.nighthawk.moe {\n    handle @local {\n    }\n"
            "    # Abort connection silently for external IPs\n}"
        )
