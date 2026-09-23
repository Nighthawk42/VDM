# D&D 3.5e character sheet

Character sheets are available only in rooms whose ruleset is `dnd35e`.
Freeform storytelling does not require or expose sheets. A sheet stores six
ability scores, race, class, alignment, level, experience, health, armor class components,
initiative, base attack, saves, attacks, equipment, feats, spells, a set of named skills
with key ability, ranks, and miscellaneous modifier, notes, and optional additional JSON fields. The extra fields survive
simple-editor saves. Only the owner or a room GM can edit or roll a character;
only a GM can attach a DC to a check. The update API requires the current sheet
version so one editor cannot silently overwrite another's work.

The server rolls a d20 and records the die, each modifier, total, optional DC,
and result with the chronicle event. Ability modifiers round down from
`(score - 10) / 2`. A skill check adds ranks, the linked ability modifier, and
the entered miscellaneous modifier. Natural 1 and 20 do not override ability
or skill check totals. This follows the [3.5e SRD's skill summary](https://www.d20srd.org/srd/skills/skillsSummary.htm)
and [using skills rules](https://www.d20srd.org/srd/skills/usingSkills.htm).

The editor's section organization and field coverage were adapted from
[Roll20's D&D 3.5 sheet](https://github.com/Roll20/roll20-character-sheets/tree/ce18c7cdb4574e8c6c46f0241be44a602d0e14e2/D%26D_3-5)
by Diana P. and Hoyer. The upstream sheet is MIT licensed; the
[license notice](third-party/roll20-character-sheets-LICENSE) is included here.
The layout and controls are implemented for this app rather than embedding
Roll20's legacy HTML, CSS, macros, images, or external assets.

Displayed armor class and saving throw totals use entered components and the
relevant ability modifier. Attack and spell entries are currently records, not
automated rolls. Existing sheets receive defaults for new fields when loaded.

This is still a starter adapter. It does not yet enforce class versus cross-class
rank caps, trained-only skills, armor check penalties, synergies, opposed
checks, saving throw rolls, attacks, or spell rules. Those need class, level,
equipment, and effect data in the sheet before the server can adjudicate them.
