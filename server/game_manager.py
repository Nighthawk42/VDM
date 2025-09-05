# server/game_manager.py
import re
import random
from typing import NamedTuple, List, Optional

class DiceRollResult(NamedTuple):
    """A structured result of a dice roll."""
    rolls: List[int]
    modifier: int
    total: int
    as_string: str

class DiceRoller:
    """A utility class for parsing and rolling dice based on standard notation."""

    # Pre-compiled regex for efficiency.
    # Captures: (1) num_dice, (2) sides, (3) modifier
    DICE_PATTERN = re.compile(r"(\d*)d(\d+)([+-]\d+)?", re.IGNORECASE)

    def roll(self, dice_string: str) -> Optional[DiceRollResult]:
        """
        Parses a dice notation string (e.g., "1d20", "2d6+3"), rolls the dice,
        and returns a structured result. Returns None if the string is invalid.
        """
        match = self.DICE_PATTERN.fullmatch(dice_string.strip())
        if not match:
            return None

        num_dice_str, sides_str, modifier_str = match.groups()

        num_dice = int(num_dice_str) if num_dice_str else 1
        sides = int(sides_str)
        modifier = int(modifier_str) if modifier_str else 0

        # Anti-abuse limits
        if not (1 <= num_dice <= 100):
            return None
        if not (1 <= sides <= 1000):
            return None
        if not (-1000 <= modifier <= 1000):
            return None

        # Perform the roll
        rolls = [random.randint(1, sides) for _ in range(num_dice)]
        total = sum(rolls) + modifier

        # Format the result into a user-friendly string
        result_string = self._format_result(dice_string, rolls, modifier, total)
        
        return DiceRollResult(rolls=rolls, modifier=modifier, total=total, as_string=result_string)

    def _format_result(self, dice_string: str, rolls: List[int], modifier: int, total: int) -> str:
        """Creates a pretty string for display, e.g., "(2d6+3) -> [5, 2] + 3 = 10" """
        rolls_str = str(rolls)
        
        if modifier != 0:
            mod_str = f" + {modifier}" if modifier > 0 else f" - {abs(modifier)}"
            return f"`{dice_string}` → {rolls_str}{mod_str} = **{total}**"
        else:
            return f"`{dice_string}` → {rolls_str} = **{total}**"