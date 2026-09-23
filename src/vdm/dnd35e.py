"""First D&D 3.5e checks: abilities and user-entered skill ranks."""

import secrets
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, Literal

from vdm.characters import ABILITIES, Character


@dataclass(frozen=True)
class CheckResult:
    """Auditable server roll and all modifiers used to calculate its total."""

    character_id: str
    character_name: str
    kind: Literal["ability", "skill"]
    target: str
    die: int
    ability: str
    ability_modifier: int
    ranks: float
    misc: int
    total: float
    dc: int | None
    success: bool | None

    def details(self) -> dict[str, Any]:
        """Return JSON-safe roll data for storage and clients."""
        return asdict(self)


def ability_modifier(score: int) -> int:
    """3.5e modifier, rounded down for odd scores below 10."""
    return (score - 10) // 2


def resolve_check(
    character: Character,
    kind: Literal["ability", "skill"],
    target: str,
    dc: int | None,
    roll_d20: Callable[[], int] | None = None,
) -> CheckResult:
    """Compute one check from the saved sheet; a 1/20 is not special here."""
    sheet = character.sheet
    ranks = 0.0
    misc = 0
    if kind == "ability":
        ability = target
        if ability not in ABILITIES:
            raise ValueError("Unknown ability")
    else:
        skill = sheet["skills"].get(target)
        if skill is None:
            raise ValueError("Add this skill to the character sheet before rolling")
        ability = skill["ability"]
        ranks = float(skill["ranks"])
        misc = skill["misc"]
    modifier = ability_modifier(sheet["abilities"][ability])
    die = roll_d20() if roll_d20 else secrets.randbelow(20) + 1
    if not 1 <= die <= 20:
        raise ValueError("d20 result must be 1-20")
    total = die + modifier + ranks + misc
    return CheckResult(
        character.id, character.name, kind, target, die, ability, modifier,
        ranks, misc, total, dc, total >= dc if dc is not None else None,
    )
