# Skill trees

## §87 A bonus's type comes from the palier ID, not from its nature field (ZER-46)

**CONFIRMED in game, 24 September 2026.** Found while trying to let tree bonuses
travel between trees in *Total chaos*.

### The table, re-read

`data/prm/skilltable.bin` has 286 records of 9 fields, one per palier (26 trees ×
11). Field 0 was documented as a row index. **It is not.** It is the **palier
ID**, the same number the community save editor uses for the per-character
proficiency bits (`tools/community/editor/src/game/data.js`, `skills`): the axe
tree reads 178, 177, 180, 181, 176… and 183 is *Attack +30 with Axe*. Field 7 is
the sequential row number.

| field | meaning | moved by the randomizer |
|---|---|---|
| 0 | palier ID: **the bonus type** | yes, since ZER-46 |
| 1 | tree (1–26) | no, it is the place |
| 2 | cost in skill points | no, it is the place |
| 3 | action ID when the palier teaches an ability | yes |
| 4 | "nature" (1 ability, 2 attack, 3 crit, 4 mastery, 11 HP…) | yes |
| 5 | **the bonus value** | yes |
| 6, 8 | secondary action, display category | yes |
| 7 | row number | no |

The weapon of a weapon bonus is **not in the record's other fields**. *Attack +10
with …* is `(0, 2, 10, 0, 2)` in fields 3–6/8 in eleven weapon trees; the thirteen
*Omnivocational …master* are all `(0, 4, 0, 0, 5)`. Only field 0 tells them apart.

### The measurement

Same save (Papouz, Gladiator level 68, Axe 100 / Hammer 3 / Guts 77, axe
equipped), cold boot on each ROM, *Attributes* screen:

| ROM | Max HP | Attack |
|---|---|---|
| vanilla | 409 | 551 |
| one swap axe 76 SP ↔ Guts 4 SP, **fields 3–6/8 only** | **429** | **531** |
| the same swap, **fields 3–6/8 and 0** | 409 | 551 |

With the ID left in place, *Attack +30 with Axe* (value 30) sitting on the Guts
4 SP place (vanilla *Natural Max HP +10*, ID 198) gives **+30 max HP** and no
attack, and the axe 76 SP place gives **+10 attack** from the HP bonus's value.
Moving the ID with the rest gives back the vanilla numbers exactly. Two more
readings on the 1.5 chaos test ROM agree: *Natural Vitality +60* and *Natural Max
MP +10* sitting on vanilla axe-attack places gave 70 **attack**, and no vitality
or MP.

So the game reads the **value** from field 5 and the **type** from field 0. The
1.5 builds before this fix moved only fields 3–6/8, and were wrong in both modes.

### Mastery in a vocation tree

With the ID left in place (the old method), a mastery placed on a vocation-tree
place that was an ability in vanilla does nothing visible: no stat moves, and a
spear and a wand stay "Équipt impos." for the Gladiator.

### Labels and the weapon icon

`sklname.gp2` (one member per language) holds the label of each place, keyed by
(tree, cost). Its field 5 flags the 54 labels that end with *with* (*Attack +10
with*); the menu then draws the weapon icon **of the tree the palier sits in**.
Measured: *Attack +30 with* moved into Guts shows no icon at all, even with its
ID. The flag, not the trailing space, marks these labels: nine Spanish ones have
no trailing space.

The game has no text tag that draws a weapon icon (140 tags found across all
text files, none does). A weapon bonus that leaves its tree therefore gets a new
label that names the weapon (*Attaque + 30 avec la hache*), built from the long
tree names in `data/bin/str_sklc.gp2`, with the icon flag cleared.

A `sklname` member starts with four words: record count, string pool offset,
pool size, string count. The pool is padded with `0xFF` to a multiple of 16. New
strings are appended after the last one and the size and count updated, the same
method the "Talent" tree names used in `str_su.gp2` on 23 September.

### Label width

Measured in game by switching BizHawk's `FirmwareLanguage` (2 French, 4 Italian,
5 Spanish): *↑ probabilità colpo critico con il ventaglio* (44 visible
characters) fits with room to spare; *Aumentar valor de impacto crítico con
abanico* (45) touches the border. Every other language stays below 44. The
Spanish critical-rate label is the only one that would overflow (*… con espada
corta*, 50), so a renamed one starts with *Más impactos críticos con* instead
(39 at most).

### Learned milestones live in the save

The save keeps the learned milestones **by ID**. Loading a save on a ROM with
another layout changes no stat. When skill points are confirmed, the game
re-evaluates every tree and announces each milestone newly reached. A save
carried from one ROM to another therefore keeps the bonuses of both layouts:
players start a new game on each randomized ROM.

## §88 Learning messages: field 8, and only five bits of it

**CONFIRMED in game, 24 September 2026.**

Field 8 of a milestone is the number of its learning message in
`data/prm/str_gskl.gp2` (1 learns an ability, 2 attack or MP with a weapon,
3 critical rate, 4 stat, 5 mastery, 14 evasion, 11–13 wand, 16–17 bare hands…).
It does not drive the effect: it travelled with the rest of the record in every
in-game test without changing a stat.

In messages 2, 3, 5 and 14, `<str_2>` is text **100 + the tree the milestone
sits in** (101 *une épée* … 114 *une paire de poings*; 113 *un bouclier* is
stored after 216). A weapon bonus moved to a vocation tree therefore reads
*… lorsqu'il est équipé d' !* (measured). Records are not stored in number
order (113 comes after 216).

**Only the low five bits of the number seem to be used.** A copy of message 2
stored under number 25 is shown; the same kind of copy under 34 shows the
original message 2 (34 = 32 + 2). Two readings, one explanation that fits both;
the code reading field 8 has not been disassembled. Either way numbers below 32
work, and the free ones are 24 to 31: too few for one copy per weapon (up to 36
per seed).

So a weapon bonus that leaves its tree gets a message without a weapon name,
since its label already names it: 2 → 4 (the stat message, *voit son attaque
augmenter de 30 !*, where `<str_2>` is text 200 + nature), 3 and 14 → a copy cut
before the weapon (numbers 24 and 25), 5 → a copy where the weapon becomes *this
weapon* (26). Seen in game: *Melchior voit son attaque augmenter de 20 !*,
*Melchior a plus de chances d'infliger des coups critiques !*.

A `str_gskl` member has the same four-word header as `sklname`; a `0x66` record
holds the message count; records are 4 bytes of descriptor plus 4 per field.
`PrmTable` stops before the last record (113) and must not be used on it.

## §88 The 0-point milestones are the skill books (ZER-51)

Each of the 26 trees has exactly one record with cost 0. It is not bought with
skill points: it is the technique of that tree's **skill book**, one of the 26
quest-reward items `22265`–`22290` (*Swordcraft in Summary* … *Luminary's
Lore*), which works while held in the bag. Cross-checked against the list of
skill manuals of the English release: the 20 labelled 0-point records are the
20 book techniques (Gigagash, Lightning Storm, Persecutter, Zing Stick, Counter
Wait, Serpent's Bite, Hand of God, Hustle Dance, Whopper Chop, Big Banga,
Shining Shot, Gigathrow, Miracle Moon, Wave of Relief, Weakening Wave, Gritty
Ditty, Solar Flair, the Armamentalist's party Fource, Twocus Pocus, Gold Rush);
the 6 unlabelled ones are the passive books (Shield: no critical hits taken;
Warrior: counters; Martial Artist: keeps Tension; Thief: steals after battle;
Gladiator: double attacks; Ranger: critical rate at low HP, nature 3).

Shuffling them put book techniques on ordinary milestones — seen in play:
Whopper Chop learned by points, no book — and made an ordinary milestone only
reachable through a book. Since ZER-51 all 26 are pinned; the other **260**
milestones (128 abilities, 132 bonuses) are redealt. Measured on seeds 1, 15
and 42 in both modes: 0 book record changed, 0 book technique on an ordinary
milestone, and the 260 moved contents are exactly the original multiset.
The two nature-0 records outside the books (wand MP regeneration, MP cost
−25 %) are real passives keyed by their palier ID, not empty places.
