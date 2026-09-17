# 9. Loot: containers, draw tables, item catalogue and drops (§79–§81)

Part of the [research notes](README.md). Sections keep their original numbers.
This is the research behind version 1.2. The player-facing summary is in
[`docs/guide/LOOT.md`](../guide/LOOT.md).

## 79. Loot: containers, draw tables, and the item catalogue

All the loot of the normal world — red chests, blue chests, pots, barrels, cupboards —
lives in **a single file**, `data/scenario/treasure.nsarc` (51,480 bytes, 268 members).
The community decompilation (`DQIX/dqix-decomp`, `src/World/LootableContainer.cpp`)
gives the code; every format below was reread on the real bytes of the EU ROM.

### 79.1 The 268 members

265 zone scripts (`C01.bin`, `D06M03.bin`, `R05M01a.bin`…) and **three draw tables**:

| member | for | outcomes | ranks |
|---|---|---|---|
| `randTBox.bin` | blue chests | 68 | 1 to 5 |
| `randTTT.bin` | pots, barrels, cupboards | 98 | 1 to 20 |
| `randTD.bin` | **grottos** | 162 | 1 to 10 |

`randTTT`: *tsubo, taru, tansu* — pot, barrel, chest of drawers. `randTD` is not loaded
by `LootableContainer::LoadZoneContainers`, which only reads the first two; the string
`randTD` only appears in the ARM9, and its ten ranks are exactly those of
`ActiveGrottoClass::RandomizeChestRank`. So it is the grotto table, and it is out of
scope.

### 79.2 The format: a generic Nitro script

Each member is a script of the game's `Script` class, the same one used elsewhere
(`itemsort_en.bin` is one too).

```
header, 16 bytes     i32 instruction count
                     u32 data section offset
                     i32 data section length
                     u32 string count
instruction          u16 opcode
                     u8  parameter count
                     2 type bits per parameter (0 string, 1 integer,
                       2 float), then 0xff padding up to the next word
                     then 4 bytes per parameter
end                  opcode 0xffff
```

Opcodes found: `0x64` and `0x65` (build timestamp — every member carries
`2009/04/13 13:31`, and they are empty stubs in the game), `0x66`
(`LootManager_Unknown_66`), `0x67` (`LootManager_CreateContainer`), `0x69`
(`LootDistribution_DeclareOutcome`), `0x6a` (`LootDistribution_AllocateOutcomes`).

### 79.3 The outcome (opcode `0x69`), a packed u32

```
bits 0-6    percentage
bits 7-22   itemID, or gold amount, or ambush type
bits 23-25  lootType: 0 nothing, 1 gold, 2 item, 3 ambush
bits 26-30  rank
```

Check: the first entry of `randTBox` is `0x052af819`, i.e. rank 1, item type, id 22000,
25 % — and 22000 is the medicinal herb, the most common item in the game, at the highest
percentage of the lowest rank.

### 79.4 What the tables REALLY contain

Measured, and it settles two questions the community only answered by hearsay:

- **`randTBox`**: every rank sums to **exactly 100 %**. Ambushes only at **rank 4 (10 %,
  type 38)** and **rank 5 (10 %, type 39)**.
- **`randTTT`**: sums range from **20 to 50 %** per rank. The rest is empty — `Sample()`
  returns `NULL` when the 0-99 draw exceeds the cumulative sum, and the caller then writes
  `lootType = 0`. **No `lootType = 3` outcome:** pots, barrels and cupboards never ambush
  outside grottos, it is written in the data, not a player impression.
- **`randTD`**: ambushes at ranks 3 to 10, types 38, 39 and **40**.

Ambush types 38, 39, 40 compare to internal identifiers 37 (cannibox), 38 (mimic), 39
(Pandora's box): **the offset is +1**, constant over all three. Either the value is
`identifier + 1`, or it designates a battle group. Not settled — that is ZER-21, and the
decomp's opcodes `Loot_Opcode_64` and `0x65` are empty stubs, so the answer is not in the
decompiled code.

### 79.5 The container (opcode `0x67`)

```
param 0   packedID : uniqueID in the high 16 bits,
                     itemIDOrRank in the low 16 bits
param 1   flags    : bits 0-1 unknown, bits 2-3 lootType, bits 4-6 containerType
rest      the position: 4 values for containerType 0 and 4,
                        1 for containerType 3, 3 otherwise
```

`containerType`: 0 red chest, 1 pot, 2 barrel, 3 cupboard, 4 blue chest.

**Inventory of the 265 zones: 847 containers.**

| container | vanilla lootType | count |
|---|---|---|
| red chest | item | 145 |
| red chest | gold | 16 |
| red chest | nothing | 6 |
| pot | nothing (rank) | 279 |
| barrel | nothing (rank) | 185 |
| cupboard | nothing (rank) | 151 |
| blue chest | nothing (rank) | 65 |

For everything but red chests, the `itemIDOrRank` field holds a **rank**, not an item:
`LoadZoneContainers` draws from the table and overwrites `lootType` and `itemIDOrRank` at
every zone load. The red chest keeps what its script says — that is why the scripts must be
patched.

### 79.6 Only one red chest holds a key item

Scan of the 847 containers against the list of 88 key items: **the Magic key (22043), in
`C02M07.bin`, uniqueID 58**. That is all.

The **Ultimate key (22044) is in no container of the game** — not in a red chest, not in a
table. It therefore comes from a script event, not the loot system. The common belief that
it is in a Gortress red chest is wrong as far as this file goes. *(The chest is spawned by
the boss event.)*

Two (uniqueID, item) pairs appear in two zones at once, `C04M04` and `C04M05`: the same
room at two moments of the story. A randomizer must give them the same item, otherwise a
chest's content changes with story progress.

### 79.7 The engine's hard constraint

`LootDistribution::GetOutcomesByRank` fills a **32-entry** array and stops there. A rank
with more than 32 outcomes would have the rest ignored. Vanilla tops out at 16, so there is
room — but not beyond 32.

### 79.8 The item catalogue, and the 88 key items

`data/prm/item_fn_div.nat` lists the catalogue's nine archives. Each `itemdt_<c>.gp2` holds
five `.nat`, one per language, of the same structure:

```
+0x00   u16   record count in the low 12 bits
+0x10         the records, 32 bytes each
                +0x04  u32  flags; low nibble: 8 = usable
                            from the menu, 9 = not
                +0x14  u16  ITEM IDENTIFIER
        then a string pool
```

Found by exhaustive scan: for each (header size, record size, position), look for the u16
column whose values are all distinct and all within 11000-23000. **A single combination
comes out**, the same for all nine files.

| file | category | count | identifier range |
|---|---|---|---|
| `itemdt_w` | weapons | 268 | 19050-20918 |
| `itemdt_s` | shields | 45 | 21000-21397 |
| `itemdt_b` | torso | 183 | 13000-13794 |
| `itemdt_u` | legs | 85 | 16093-16390 |
| `itemdt_h` | head | 132 | 12170-12917 |
| `itemdt_a` | arms | 78 | 15000-15299 |
| `itemdt_l` | feet | 101 | 17091-17421 |
| `itemdt_d` | accessories | 52 | 18000-18055 |
| `itemdt_t` | regular **and** key items | 234 | 22000-22290 |
| | **total** | **1178** | |

1178 is also exactly the record count of `itemname.gp2` (`itemname_<lg>.nat`: 4-byte
header, 16-byte records, singular and plural name offsets into a pool after it). Two
independent counts that match.

**Key items.** The game has no universal "important" flag: the low nibble of `+0x04` is 9
for **all** equipment. But inside `itemdt_t`, which mixes regular and key items, it
separates **exactly 88** records (nibble 9) from 146 (nibble 8). And those 88 are exactly
the ones the community save editor (`DQIX/editor`, `src/game/data.js`) classes as
`ITEM_TYPE_IMPORTANT` — two independent sources, zero disagreement, over the 234 entries.
The reading is therefore: *in `itemdt_t`, not usable from the menu = key item*.

The 88 do include the six progression witnesses: Thief's key (22042), Magic key (22043),
Ultimate key (22044), Little key (22131), Quarantomb key (22162), Fygg (22169).
`scripts/objets.py` checks that count and those witnesses at every build and refuses to
produce a ROM if one is missing.

**Allowed pool: 1178 − 88 = 1090 items.**

### 79.9 Rewriting without moving anything

Every rewrite targets a `u32` already present — an outcome, or a container's `packedID`.
No file size changes, so the ROM layout is preserved and savestates stay valid. Check on a
real build: between a 1.1 ROM and the same with `--objets`, **628 bytes differ, all in
`treasure.nsarc`**, and nothing else. *(No longer true once the tables are enlarged,
§80.6.)*

## 80. Item names, monster drops, and the in-game test of 1.2

### 80.1 Identifier → name, in the ROM

`itemname_<lg>.nat` (in `itemname.gp2`): 4-byte header, 1178 records of 16 bytes
`{u32 name, u32 plural, u32 ?, u32 ?}`, offsets relative to a string pool that follows
(after zero padding).

**The link to the identifier is the order**: the nine `itemdt_*` categories laid end to end
in the order `h b a u l d w s t` (head, torso, arms, legs, feet, accessories, weapons,
shields, items), each in its record order. Measured: under that rule, 1178 English names of
1178 match the community save editor, apart from tags (`<1>` apostrophe, `<:u>` ü,
`<6>`/`<9>` quotes) and three typos **in the editor** ("startotoga", "sensible sandles",
"xenion claws"). No column of `itemdt` or `itemsort` holds a name index: the order is the
link.

Confirmed in game: items 15033 and 20507 display as "silver bracelets" and "holy lance"
(screenshots of September 17, §80.4).

### 80.2 Monster drops: `mon_btldata.nat` +0x04 and +0x06

The two u16 that `montable.py` called `nom_str` and `desc_str` are **the common and rare
item** the monster drops. Evidence:

- scan of u16 columns against the catalogue: `+0x04` has 428 non-zero values out of 438,
  **all** valid item identifiers; `+0x06` has 387, all valid. Out of 65,536 possible values,
  1178 of them valid, that is impossible by chance;
- the slime and other well-known monsters carry their known vanilla drops (medicinal herb
  for the slime, chimaera wing for the chimaera).

815 non-empty slots in total, **576 of them on encounterable monsters** (the whitelist of
256). Drop rates are not in these two fields (see §81); they are left untouched.

### 80.3 Quest items dropped by monsters are NOT drops

None of the 88 key items appears at `+0x04` or `+0x06`. The chimaera feather (22187), only
picked up with the quest active, is referenced as a constant in
`data/scenario/quest_btl_1.stb` (magic `SB2`, two occurrences at `0x83F0` and `0x8420`): the
**quest script** gives it after the battle. Randomizing the two drop columns therefore does
not touch that mechanism. The `SB2` format is not decoded.

### 80.4 In-game test of 1.2, on the player's savestates

Probe `scripts/lua/ouvre_conteneur.lua`: loads the state, reads the zone's container list
(EUR manager `0x02108E90`, read from the literal at `0x0207BA6C`), presses A, captures the
message, reads again.

| savestate | container | content read in RAM | on-screen message |
|---|---|---|---|
| `coffre_bleu_v12` | blue chest uid 573, rank 2 | 15033 | "acquires a pair of silver bracelets" |
| `coffre_rouge_v12` | red chest `C01M16` uid 13 | 20507 | "acquires a holy lance" |
| `pot_v12` | the searched pot | empty | no message |

All three match the build log. Positions read in RAM are those of the zone scripts
(`13.75 ; 0.1 ; -37.03` for chest 13), which also validates the reading of the position in
opcode `0x67`. On opening, the game resets `lootType` to 0 in the RAM list.

### 80.5 Coverage: how many items can come out

Measured by `scripts/catalogue_objets.py` (column `obtenable`: comes out of a table, a red
chest or an encounterable monster):

| ROM | pool items obtainable |
|---|---|
| vanilla | 284 of 1090 |
| 1.2, draw with replacement | 594 |
| 1.2, draw without replacement (at the time) | **859** |

The ceiling with the vanilla structure is **861** reachable slots (141 outcomes, 144 red
chests, 576 drops of encounterable monsters). Getting all 1090 out requires more slots:
extra outcomes in the tables, up to 32 per rank (§79.7), which grows `treasure.nsarc`.

### 80.6 Enlarging the draw tables, and the engine's two ceilings

So that all 1090 pool items can come out, `randTBox.bin` and `randTTT.bin` are **rebuilt**
with more lines per rank (`patch_loot.repartir`): gold and ambushes are copied, the "item"
share of each rank is split into whole-percentage lines. Each rank's sum, hence its empty
share, does not move a point (assertion at build time).

Two ceilings, read in the decomp **and checked in the EUR code**:

- `Sample()` stores a rank's outcomes in an array of **32**;
- `LoadZoneContainers` (EUR `0x0207BD44`) loads each table into a stack buffer:
  `mov r2, #0x400 ; bl 0x02032500` (`CreateTypeA`). The `HMRFAllocator` header is **48
  bytes**: `add r2, r4, #0x30` in `CreateInRegion` (EUR `0x020AF860`). 976 bytes remain,
  i.e. **244 outcomes**. Beyond that, `AllocateOutcomes` fails and the table is empty — no
  crash, no more loot. We stop at **242**.

Result on seed 1: `randTBox` 68 → 160 lines (5 ranks × 32), `randTTT` 98 → 242,
`treasure.nsarc` 51,480 → 53,368 bytes. **1090 pool items of 1090 obtainable.** The ROM
layout changes: earlier savestates are no longer valid. Cold boot checked.

The rebuild is exact: rebuilding the three vanilla tables and the archive without changing
anything gives back the original bytes, identical.

### 80.7 Zone names

`data/map/maplist9.bin` (Nitro script, opcode `0x67`): param 0 = map identifier, param 4 =
file code. `data/map/mapname.gp2` → `mapname_<lg>.bin`: opcode `0x67`, identifier → displayed
name. `C01M16` → 116 → "Stornway Castle - B1", the minimap name on the player's savestate.
All 265 zones of `treasure.nsarc` are resolved (`scripts/zones.py`). The Magic key chest
(`C02M07`) is indeed at "Mirage Mahal - L3".

## 81. The monster drop roll, and the rate classes

Found by setting read breakpoints on the golem's drops during a battle
(`scripts/lua/lecteurs_drop.lua`), then looking for calls to the RNG `0x02032380` next to an
access to `+4` and `+6` in battle RAM.

**The roll function** is in the battle code loaded in RAM (EUR, around `0x021F4930`). For
each defeated monster, it reads the `mon_btldata` record (`bl 0x02070FE0`):

```
ldrb r0, [fp, #3]          RARE drop class
ldr  r1, =0x021FD888       class -> denominator table
ldr  r1, [r1, r0, lsl #2]
... bl 0x02032380          rand_below(denominator)
cmp r0, #0 ; bne common    0 -> the rare drops: ldrh r1, [fp, #6]
ldrb r0, [fp, #2]          otherwise, COMMON drop class, same roll
... ldrh r1, [fp, #4]
```

Two paths change the denominator: `r7 > 0` passes it through a percentage function
(`0x0200CF44`, probably a bonus), and an actor bit (`[r8]` bits 14 and 15) forces it to 1,
i.e. a guaranteed drop.

**The table** (`0x021FD888`, int32): class 0 = 1 (always), 1 = 8, 2 = 16, 3 = 32, 4 = 64,
5 = 128, 6 = 256, 7 = 0 (never).

**In `mon_btldata.nat`**: `+0x02` common class, `+0x03` rare class. `montable.py` called that
u16 `modele`: renamed `classes_drop`. Vanilla examples: slime 1/8 and 1/16, metal slime 1/64
and 1/256, golem 1/16 and 1/128. The 256 field species have no slot in class 7; the "never"
ones are all on bosses or non-field entries.

**Checked in game** with `scripts/rom_drops_garantis.py` (test ROM, never published) on the
golem savestate: common forced to 0 and rare to 7 → "The golem drops a treasure chest! It
contains a sadistick!", the randomized common item; rare forced to 0 → "It contains an iron
helmet!", the randomized rare item. The drop randomizer works, and the class reading is right.

An item's sell price is the u16 at `+0x16` of its `itemdt` record (medicinal herb 4, a 1,500
sword, a 36,000 hammer). *(The star rarity was first thought absent from the catalogue; §81.1
found it.)*

### 81.1 Star rarity

The item screen shows a "Rarity" of 0 to 5 stars. It is in the `itemdt` record: **byte
`+0x05`, bits 1 to 3**. Found with three player screenshots on v12 (antidotal herb 0★, an
executioner's axe 2★, "Gladiator's Guide" 3★): a single position in the record gives those
three numbers, and its values stay within 0-5 over the 1178 items. The **22 items at 5★** are
exactly the legendary equipment (hypernova sword, legendary armour, seraph's bow...).

1090 pool by stars: 0★ 64, 1★ 405, 2★ 204, 3★ 285, 4★ 110, 5★ 22. Function:
`objets.raretes()`.
