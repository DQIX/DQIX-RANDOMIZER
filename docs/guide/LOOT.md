# How loot works in the randomizer (version 1.2)

This guide explains, in plain terms, what version 1.2 does to the items you find
in Dragon Quest IX (Europe, `YDQP`): what comes out of chests, pots, barrels and
cupboards, what monsters drop, and what is left untouched. Everything here was
read from the game data and checked in game.

The detailed lists are in the `loot/` folder next to this file:

| File | What it answers |
|---|---|
| [`loot/containers_by_rank.md`](loot/containers_by_rank.md) | Where is every blue chest, pot, barrel, cupboard and red chest, and what rank is it? |
| [`loot/rank_tables.md`](loot/rank_tables.md) | What are the odds of item / gold / ambush / nothing for each rank? |
| [`loot/drop_rates.md`](loot/drop_rates.md) | How often does each field monster drop its common and rare item? |

Each release also ships spreadsheets for the seed of its patch (see
[Release files](#release-files)).

---

## 1. The five kinds of containers

| Container | What the game stores | When the content is decided |
|---|---|---|
| **Red chest** | one fixed item (or gold) | never changes: it is written in the room data |
| **Blue chest** | a **rank** from 1 to 5 | rolled **each time you enter the room** (or come back from a battle) |
| **Pot, barrel, cupboard** | a **rank** from 1 to 20 | rolled each time you enter the room |

Once a container is opened, it stays opened.

## 2. What a rank is

A blue chest or a pot does not hold an item. It holds a **rank**, fixed by the
room it sits in. Roughly, the later the area in the story, the higher the rank.

Each rank has its own **loot list**: a set of lines, each one an item, an amount
of gold or an ambush, with a percentage. When you enter the room, the game rolls a
number from 0 to 99 and walks down the list of that rank. If the roll goes past
the last line, the container is **empty**.

Example, a rank 1 blue chest in the original game:

| Line | Chance |
|---|---|
| Medicinal herb | 25 % |
| Antidotal herb | 20 % |
| Moonwort bulb, Holy water, Chimaera wing | 10 % each |
| 5 other items | 5 % each |
| 18 gold | 5 % |

Blue chest lists add up to 100 %: a blue chest is never empty. Pot lists add up to
20-50 %: **most pots are empty**, in the original game as in the randomizer.

Ranks 3 and 14 of pots contain only gold. Rank 0 pots are always empty.

## 3. What version 1.2 changes

**Kept exactly as in the original game**

- the rank of every container;
- the chance of item, gold, ambush and nothing for every rank;
- the amounts of gold;
- when the content is rolled (on entering the room).

**Changed**

- **Which items fill each list.** Any item of the game can appear, weapons and
  armour included, except key items (see §6).
- **More lines per list.** The original lists hold 68 lines (blue chests) and 98
  lines (pots). Version 1.2 splits the same item percentage into many smaller
  lines, 242 per list, so that many more different items can come out. The game
  engine accepts at most 32 lines per rank and 244 per list; 1.2 stays under both.
- **Twin ranks for blue chests: 3b, 4b, 5b.** With only five ranks, blue chest
  lists cannot reach 242 lines. So ranks 3, 4 and 5 each get a **twin** with
  exactly the same odds and a *different* item list, and one blue chest out of two
  of those ranks now uses the twin. A rank 5b chest behaves exactly like a rank 5
  chest; it just draws from another list. (In the game data the twins are stored
  as ranks 6, 7 and 8.)
- **Red chests** get a new fixed item, drawn once when the ROM is built.
- **Monster drops** get new items (see §5).

**Every one of the 1,090 allowed items can be obtained.** The randomizer places
each item at least once in a place the player can reach: a chest list, a red
chest, or a field monster's drop.

## 4. Rarity

Every item has a **rarity from 0 to 5 stars**, shown at the top right of its
description screen. The 22 five-star items are the legendary equipment (hypernova
sword, starsmasher, legendary armour, seraph's bow...).

Version 1.2 places items according to their rarity:

| Where | Rarity allowed |
|---|---|
| Blue chest rank 1-2 | 0-2★ |
| Blue chest rank 3 / 3b | 2-3★ |
| Blue chest rank 4 / 4b | 3-4★ |
| Blue chest rank 5 / 5b (the highest) | 3-5★ |
| Pot, barrel, cupboard rank 1-7 | 0-1★ |
| Pot, barrel, cupboard rank 8-13 | 1-2★ |
| Pot, barrel, cupboard rank 14-19 | 2-3★ |
| Pot, barrel, cupboard rank 20 (the highest) | 3-5★ |
| Monster drop, chance 1/8 or 1/16 | 0-1★ |
| Monster drop, chance 1/32 or 1/64 | 2-3★ |
| Monster drop, chance 1/128 | 4★ |
| Monster drop, chance 1/256 | 4-5★ |
| Red chest | any, 0-5★ |

So a **five-star item** can only come from: a rank 5 or 5b blue chest, a rank 20
pot, barrel or cupboard, a monster drop at 1/256, or a red chest. The locations of
the highest-rank containers are at the end of each section of
[`loot/containers_by_rank.md`](loot/containers_by_rank.md).

## 5. Monster drops

Every monster has a **common** and a **rare** drop, each with a chance taken from
this scale:

| Class | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| Chance | always | 1/8 | 1/16 | 1/32 | 1/64 | 1/128 | 1/256 | never |

When you defeat a monster, the game rolls the **rare** drop first; only if it
fails does it roll the common one. At most one item drops per monster.

Version 1.2 keeps every chance and changes the items, following the rarity table
above. A monster that exists as several entries in the game data (for example two
story variants of the same species) drops the same items in all of them.

Quest items that monsters drop only while a quest is active (like the hocus
chimaera feather) are **not** part of this system: a quest script hands them out.
They are unchanged.

## 6. What is never touched

- **Key items.** The game has 88 of them (keys, Fyggs, quest and story items).
  None is ever placed in a chest or a drop.
- **The Magic Key chest** (Mirage Mahal - L3). It is the only chest of the game
  that holds a key item, and it keeps it.
- **The Ultimate Key chest** after the Gortress boss. It is created by the boss
  event, not by the chest system, so the randomizer does not see it.
- **Ambushes.** Rank 4 and 5 blue chests (and their twins) still hide a cannibox or
  a mimic 10 % of the time.
- **Treasure maps and grottos.** Their chests use their own system.
- **Quest rewards, shops, sparkly spots.**

## 7. Release files

Each release attaches, for the seed used to build its patch:

| File | Content |
|---|---|
| `items.csv` | the 1,178 items: name, category, rarity, key item or not, obtainable or not, number of sources |
| `item_sources.csv` | one line per source of an item: which red chest, which rank and chance, which monster and drop chance |
| `containers.csv` | every container: location, rank or fixed content, position, ROM offset |
| `vanilla_containers.csv` | the same, for the original game |

The spreadsheets use `;` as separator and UTF-8, and open directly in Excel.

## 8. For developers

The formats (loot tables, container records, item catalogue, drop classes, rarity
field) are documented with their evidence in [`../research/RESEARCH.md`](../research/RESEARCH.md),
sections 79 to 81. The code is in `scripts/treasure.py`, `scripts/objets.py`,
`scripts/rarete.py` and `scripts/patch_loot.py`; the lists in this folder are
generated by `scripts/doc_loot.py`, the spreadsheets by
`scripts/catalogue_objets.py`.
