# 1. ROM, file formats and the monster table (§1–§14)

Part of the [research notes](README.md). Sections keep their original numbers.

> Anything marked **CONFIRMED** was checked against at least two independent
> clues. Anything marked **HYPOTHESIS** still needs validating, usually by
> observing the game in the emulator.

## 1. The ROM

| | |
|---|---|
| File | `Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds` |
| Internal title | `DRAGONQUEST9` |
| Serial | **YDQP** (European multilingual) — JPN = `YDQJ`, USA = `YDQE` |
| Size | 268,435,456 bytes (256 MiB); used data 257,915,964 bytes |
| CRC32 | `FE8EC0E8` |
| MD5 | `3a63438fff7db282fa3133e8fd020e85` |
| SHA1 | `ff761d349709f329c8ac4bd0023fdce21861e8a1` |

Binaries and file systems:

| Item | ROM offset | RAM address | Size |
|---|---|---|---|
| ARM9 | `0x00004000` | `0x02000000` (entry `0x02000800`) | 638,216 bytes |
| ARM7 | `0x001E2400` | `0x02380000` | 167,876 bytes |
| FNT (names) | `0x0020B400` | — | 90,629 bytes |
| FAT | `0x00221800` | — | 60,128 bytes (**7,516 files**) |
| ARM9 overlays | `0x0009FE00` | — | **35 overlays** |

RAM address to offset in `arm9.bin`: `offset = RAM_address - 0x02000000`, valid
only for `0x02000000 <= address < 0x0209BD08`. Beyond that (heaps, dynamic
objects, loaded overlays) you need a live RAM dump from the emulator.

## 2. NitroFS tree

23 directories, 7,516 files. The big ones:

| Directory | Files | Size | Content |
|---|---|---|---|
| `/data/sound` | 7 | 69.3 MiB | `.sdat` (standard Nitro audio) |
| `/data/map` | 1,386 | 50.1 MiB | maps |
| `/data/scenario` | 983 | 38.6 MiB | scenario |
| `/data/pack_lv5` | 12 | 27.8 MiB | Level-5 archives |
| `/data/effect` | 1,430 | 22.9 MiB | effects |
| **`/data/prm`** | **60** | **2.25 MiB** | **parameter tables — the target** |
| `/data/enemy` | 26 | 0.48 MiB | `.chr` models of a few enemies only |

`/data/prm` is the game's parameter directory. Useful names:

| File | Size | Likely role |
|---|---|---|
| **`mon_btldata.nat`** | 57,820 | **battle stats of the 438 monsters — DECODED** |
| `mon_moddata.nat` | 28,036 | 438 × 64 bytes — per-monster model data |
| `mons_info2.nat` | 32,588 | monster info (format still unknown) |
| `mon_data.gp2` | 59,036 | GPC2 container |
| `mon_list.gp2` | 45,232 | GPC2 container |
| `mon_trv1/2.gp2` | ~105 k | GPC2 containers |
| **`encmons.bin`** | 5,104 | **encounter groups — partly decoded** |
| `encbtl.bin` | 27,296 | battle encounters (tag 0x68 not handled) |
| `encfld.bin` | 23,072 | field encounters (tag 0x69 not handled) |
| `enchab.gp2` | 29,048 | "encounter habitat" — GPC2 container |
| **`fld_mondata.bin`** | 15,840 | **437 field monsters — DECODED** |
| `mons_dmy.bin` | 1,316 | list of u16 indexes |
| `level0.bin` … `level12.bin` | 5,312 ×13 | **level-up tables of the 13 vocations — DECODED** |
| `skilltable.bin` / `spelltable.bin` | 12,704 / 2,576 | skills / spells — DECODED |
| `itemdt*.gp2`, `itemname.gp2` … | — | items (see §79–§81) |

## 3. Tagged table format (`.bin` in `/data/prm`) — CONFIRMED

Header:

```
+0x00  u32  record_count
+0x04  u32  data_size
+0x08  u32  0x1B     (constant; 0 in the short-header variant)
+0x0C  u32  0x02     (constant; 0 in the short-header variant)
+0x10  u16 tag=0x65, u16 0x0001, u32 0x00000000    } long variant
+0x18  u16 tag=0x64, u16 0x0001, u32 0x00000014    } only
```

The body starts at `0x20` if `0x20 + data_size == file_size` (long variant),
otherwise at `0x10` (short variant, e.g. `encmons.bin`).

Body: a sequence of **variable-size** records:

```
u16   tag            0x64, 0x65, 0x66 (and 0x68, 0x69 in encbtl/encfld)
u8    field_count
...   type descriptor + 0xFF padding, aligned to 4 bytes
N x u32 the fields
```

The descriptor is **identical for every record of a given kind** in a file, so
it can be treated as an opaque prefix and the fields rewritten without
understanding their meaning — enough to patch.

Observed descriptors: `field_count=2` gives a 4-byte descriptor; `field_count=5`
gives 8 bytes (`66 00 05 55 01 ff ff ff`); `field_count=11` gives 8 bytes
(`66 00 0b 55 55 15 ff ff`). *(Later understood as the generic Nitro script
format: 2 bits of type per parameter; see §79.2.)*

Implementation: `scripts/prmtable.py` (class `PrmTable`, method `set_field`).

### `level0.bin` … `level12.bin` — CONFIRMED

13 files, one per vocation. 98 records of 11 u32 fields (levels 1 to 99).

```
[0]  = 0,  10, 9, 8, 8, 9, 8, 8, 30, 10, 0
[1]  = 17, 11, 10, 9, 9, 10, 9, 9, 32, 11, 0
[2]  = 44, 13, 12, 11, 11, 12, 11, 11, 35, 13, 0
```

Field 0 = cumulative experience required. Fields 1-7 = stats. Fields 8-9 = max
HP and MP (30 / 10 at level 1). Field 10 = always 0. **HYPOTHESIS**: the exact
order of stats 1-7 is still to be confirmed in game.

### `spelltable.bin` — CONFIRMED

175 header / 212 records of 2 u32 fields: `(sequential_index, id)`. The `id`s
come in groups of 4: `(9,10,11,779) (12,16,17,780) (13,14,15,781)…`

### `encmons.bin` — PARTIAL

Short header, body at `0x10`, 209 records of mixed shapes (120 × 5 fields,
71 × 4 fields, 17 × 3 fields).

The u32 fields read back as **pairs of u16**, which gives consistent groups:

```
[7102, 0, 0x0007002B, 0x0009001E, 0x00040014]
   -> zone 7102, then (43,7) (30,9) (20,4)
```

**HYPOTHESIS**: each pair is `(monster_id, count or weight)` and the record
describes an encounter group for a zone. *(Superseded by §15.)*

### `fld_mondata.bin` — CONFIRMED (structure), fields to be named

437 records of 7 u32 fields, preceded by a count record (tag `0x64`, single
field = 438).

```
[1, 1,  5, 0x003C0011, 0x3EC8000D, 10,  7]
[2, 7, 12, 0x003C0011, 0x3EC8000D, 23, 18]
```

Field 0 = monster id. **Cross-check CONFIRMED**: fields 5 and 6 are exactly
`mon_btldata.nat +0x60` and `+0x62` (attack and defence) of the same monster.
That cross-check is what validates the alignment of the two tables.

## 4. `mon_btldata.nat` — the central table — CONFIRMED

**This is the main finding.** The community decompilation project (GitHub org
`DQIX`) considered this table unlocated at the time.

Format: `u32 count = 438`, then **438 records of 132 bytes**.
`4 + 438 × 132 = 57,820` = exact file size.

```
+0x00  u16   0x8000 | monster_id        id from 1 to 0x384 (900)
+0x02  u16   model / family?            byte pair, 24 distinct values
                                        (LATER: drop rate classes, §81)
+0x04  u16   string id: name?           range ~13000-22200
                                        (LATER: common drop item, §80)
+0x06  u16   string id: description?    range ~13000-22300
                                        (LATER: rare drop item, §80)
+0x08  u16   EXPERIENCE given
+0x0A  u16   flag, values {0, 1, 3}
+0x0C  u16   GOLD given
+0x0E  u16   constant 0
+0x10  u16   ?
+0x12  u16   bit field (0x1800, 0x9800, 0x1A00…)
+0x14  u16   ?  (0-605, two columns identical with +0x16)
+0x16  u16   ?
+0x18  u16 x 6  ?  values 1 / 225, two groups of three      -> +0x22
+0x24  u16   ?  23 distinct values
+0x26  u16   ?  11 distinct values
+0x28  u16   ?  10 distinct values
+0x2A  u16   ?  0-136, correlated with progression
+0x2C  ..    46 bytes ALWAYS ZERO (reserved)                 -> +0x5B
+0x5C  u16   MAX HP          <- correlation 0.86; runtime role not verified,
                              see the caveat below
+0x5E  u16   MAX MP
+0x60  u16   ATTACK
+0x62  u16   DEFENCE
+0x64  u16   AGILITY
+0x66  u16   constant 0
+0x68  u16   constant 0
+0x6A  u16   constant 0
+0x6C  u8 x 7   ELEMENTAL RESISTANCES in %                   -> +0x72
+0x73  u8       always 100
+0x74  u8 x 14  STATUS AILMENT RESISTANCES in %              -> +0x81
+0x82  u8 x 2   alignment padding (always 0)
```

### Evidence

**1. The metal slime signature.** Record index 2 (id 3):

```
HP 4 · MP 255 · ATK 35 · DEF 256 · AGI 89 · XP 4096 · gold 20
resistances: immune (0) in most columns
```

4 HP with 256 defence and massive immunity: that is a metal slime, no other
creature of the series has that profile.

**2. Distribution of the resistance bytes.** Over 10,512 sampled bytes, only
**15 distinct values**, all round steps:

| Value | % |
|---|---|
| 100 | 31.8 |
| 0 | 27.6 |
| 50 | 14.5 |
| 75 | 11.5 |
| 25 | 3.7 |
| 125 | 3.4 |
| 150 | 3.1 |
| 5 / 10 / 15 / 35 / 200 … | rest |

And two clearly separate blocks: `+0x6C..+0x72` accepts 125/150/200 (so
**weaknesses**, a damage multiplier), `+0x74..+0x81` caps at 100 (so a
**probability** of resisting). Unstructured data would never produce this
distribution.

**3. Control zone.** `+0x2C..+0x5B` is zero in all 438 records without
exception: the record alignment is necessarily right.

**4. Cross-file check.** `fld_mondata.bin` fields 5-6 equal `+0x60` and `+0x62`
for every monster.

**5. Correlation with progression.** `+0x5C` (HP) has a Spearman rho of **0.86**
with the bestiary index — monster tables are ordered by appearance in the game,
so HP must grow, and it does.

### Caveat on the HP field — raised by in-game observation

The player saw a monster of the sentinel species, whose `+0x5C` had been set to
**111**, die after a hit shown as **73** damage.

What remains solid for `+0x5C = max HP`:

- canonical series values found exactly: `metal slime` 4 HP, `liquid metal
  slime` 8 HP, `metal king slime` 16 HP — and these are those monsters,
  confirmed by their names read independently (§14);
- agreement with `fld_mondata.bin` on neighbouring fields;
- 0.86 correlation with bestiary order.

What is **not** established: that the monster instance created in battle takes
its max HP from this field. Three explanations remain open:

1. the 73 damage was only one of four hits in a group turn, and the total went
   over 111;
2. the game applies an HP variance when the monster spawns;
3. the instance takes its HP from another source.

Note that the earlier check (§12) found the `(HP, MP, attack, defence)` pattern
in memory, but that pattern **also exists in the file bytes loaded in RAM**: I
cannot rule out having measured the file buffer rather than the runtime
structure. §12's conclusion on where the data comes from stands — it compared
two ROMs — but it does not prove the precise runtime role of this field.

Settling it needs a savestate taken **during** a battle. Four automation
attempts failed: the driver reaches the plain but meets no monster symbol, and
probing candidate addresses for the enemy structure only returns noise
(`HP 9740/15488`, current MP above max). Address `0x022A4C7C` comes from
Japanese Action Replay codes and may not be valid for EUR.

**No impact on the randomizer**, which by default does not touch stats.

### Still to do on this table

- Name the 7 elemental and 14 status ailment columns (method: cast a spell of
  each kind on a monster with a known weakness).
- Identify the dropped items — *(done later: `+0x04`/`+0x06`, §80)*.
- Work out `+0x18..+0x22` (values 1/225 in two groups of three).

## 5. GPC2 container (`.gp2`) — NOT DECODED at this stage

ASCII magic `GPC2` at the start. Common header:

```
00000000: 47 50 43 32  05 30 05 00  15 00 20 00  0f 00 14 00   GPC2.0.... .....
00000010: <varies>     e0 01 00 00  <varies>
```

Proprietary Level-5 format. `Tinke` and `Kuriimu` do not handle it
([Kuriimu issue #566](https://github.com/IcySon55/Kuriimu/issues/566), never
implemented). The dedicated community tool is
[`DQIX/ArchiveTool`](https://github.com/DQIX/ArchiveTool) (C#, two drag-and-drop
executables). No public written specification. *(Decoded later in Python:
`scripts/gp2.py`, `scripts/lz_dq9.py`, see §13.)*

## 6. `.nat` tables — PARTLY CONFIRMED

All start with `u32 = 438` (the monster count). Whole-number stride:

| File | Check | Stride |
|---|---|---|
| `mon_btldata.nat` | `4 + 438 × 132 = 57,820` OK | 132 |
| `mon_moddata.nat` | `4 + 438 × 64 = 28,036` OK | 64 |
| `mons_info2.nat` | not whole | different header, to be worked out |

## 7. Known RAM addresses (source: community)

From [`DQIX/dqix-functions`](https://github.com/DQIX/dqix-functions) and Action
Replay codes, cross-checked.

Enemy structure in battle, in RAM: `enemy(i) = 0x022A4C7C + i × 0xA4`,
5 slots (`i = 0..4`):

```
+0x00 u16 current HP   +0x02 u16 current MP
+0x04 u16 max HP       +0x06 u16 max MP
+0x08 u16 attack       +0x0A u16 defence     +0x0C u16 speed
```

Spawn functions, **EUR addresses available** (valuable: the decomp officially
covers only JPN and USA):

| Function | EUR | JPN |
|---|---|---|
| `ChooseFieldMonsterId` | `0x02073FEC` | `0x02075168` |
| monster table read by the above | `0x020FDDC4` | — |
| `GenerateCompanionByBT` | `0x0209AFE4` | `0x0209CD4C` |
| associated table | `0x020FDE68` | — |
| `GenerateCompanionByAT` | `0x0209B458` | `0x0209D1C0` |
| `initMonsterData` | — | `0x021677AC` |

Map structure: `0x020FDAAC + 0x314 × N`, `N = 0..4`.

## 8. Pseudo-random generators — documented by the community

| Name | Width | Formula | Used for |
|---|---|---|---|
| **AT** | 32 bits | `r = r × 0x41C64E6D + 0x3039` | monster spawns, drops, symbol movement |
| **BT** | 64 bits | `s = s × 0x5D588B656C078965 + 0x269EC3` | 2nd/3rd enemy groups, alchemy, fleeing |
| **CT** | 48 bits | same as BT | battle actions, camera; reseeded each battle |

AT and BT share the initial seed. The grotto generator is different:
`s = s × 1103515245 + 12345`, output `(s >> 16) & 0x7FFF` — reimplemented in
JavaScript in [`DQIX/editor`](https://github.com/DQIX/editor)
(`src/game/grotto.js`), with its lookup tables copied in.

For the randomizer: the pre-emptive strike formula is
`max_dexterity × 0.05 + 2` %, +10 % when attacking from behind.

## 9. Code binaries — map

### The ARM9 is compressed (BLZ)

`rom.arm9` straight out of the ROM is **compressed**: 638,216 bytes, which give
1,000,984 bytes once decompressed (factor 1.57). BLZ footer in the last 12
bytes: `00 00 00 08 08 7d 09 08 10 89 05 00`.

```python
import ndspy.rom, ndspy.codeCompression as cc
rom = ndspy.rom.NintendoDSRom.fromFile(ROM)
full = cc.decompress(rom.arm9)      # 1,000,984 bytes
```

**In practice: decompress before disassembling.** Searching a pattern in the raw
`arm9.bin` finds nothing — which is why an ARM9 code byte is not found as-is in
a savestate, while the (uncompressed) ARM7 is found immediately.

The 35 ARM9 overlays are compressed too, but `ndspy.loadArm9Overlays()` returns
the decompressed content directly (`overlay.data`).

### Which overlay reads what

Found by searching file path strings in each decompressed overlay. Several
overlays share the same RAM address: they are swapped in on demand.

| Overlay | RAM address | Size | `/data/prm` files referenced |
|---|---|---|---|
| 0 | `0x021536E0` | 199,488 | `mon_btldata`, `mon_data` |
| 2 | `0x021536E0` | 105,664 | `skilltable`, `spelltable` |
| 14 | `0x021842A0` | 21,856 | `enchab`, `mon_list`, `mons_info` |
| **17** | `0x0218B5A0` | 314,688 | **`encbtl`, `encfld`, `encmons`, `fld_mondata`**, `mon_data` |
| 23 | `0x021D8A40` | 159,648 | `mon_data`, `skilltable`, `spelltable` |
| **25** | `0x021D8A40` | 93,984 | **`mon_btldata`**, `mon_data` |
| 26 | `0x021D8A40` | 25,792 | `skilltable`, `spelltable` |

Overlays **0 and 25** carry the battle system, overlay **17** the encounter
system.

Strings also present in the decompressed ARM9, so always resident:

| String | ARM9 offset | RAM address |
|---|---|---|
| `data/prm` | `0xEF0B5` | `0x020EF0B5` |
| `mon_btldata` | `0xF0B6D` | `0x020F0B6D` |
| `encmons` | `0xF24CC` | `0x020F24CC` |

`mon_data_<LG>.nat` appears as a file name template with a `<LG>` language
marker. There is no `mon_data_en.nat` in the NitroFS: the per-language variants
are **inside** `mon_data.gp2` (confirmed in §14).

## 10. Proof that the engine uses `mon_btldata.nat`

Two independent facts, both checkable by script.

**1. The file is referenced by its full path in the code.** The literal
`data/prm/mon_btldata.nat` is in the decompressed ARM9 (always resident) and in
overlays 0 and 25 (battle system).

**2. There is no other copy of this data in the ROM.** Searching for the metal
slime's 132-byte record across the whole ROM — decompressed `arm9`, `arm7`, the
35 decompressed overlays and the 7,481 NitroFS files — finds it in **a single
file**: `/data/prm/mon_btldata.nat`.

### What this does not cover

It establishes that the file is the only source and that the code opens it. It
does not establish that **every field** means what I assume. HP / attack /
defence / agility / experience / gold are confirmed by monster signatures and by
`fld_mondata.bin`, but fields still marked `?` in §4 remain unknown.

### Why a byte search in RAM is not enough

Checked: none of the 60 `/data/prm` files is in RAM during the opening sequence
(Observatory), not even `level0.bin`. They are loaded on demand. And the runtime
structure of an enemy in battle is **0xA4 = 164 bytes** (community source)
against 132 in the file: the engine builds its own structure.

Conclusion: in-game confirmation must compare **values** read in the runtime
structure during a battle, not look for identical bytes.

## 11. `encbtl.bin` and `encfld.bin` — wider tag set

The first parser accepted only tags `0x64`/`0x65`/`0x66` and returned **0
records** for these two files. Widening the accepted set to `0x60`–`0x6F`, both
parse almost fully:

| File | Records | Unparsed tail | Shapes |
|---|---|---|---|
| `encbtl.bin` | 2,874 / 2,877 | 40 bytes | tag `0x67` × 1 field (×1526), `0x66` × 2 fields (×1058), `0x68` × 1 field (×290) |
| `encfld.bin` | 1,827 / 1,830 | 52 bytes | tag `0x67` × 2 fields (×1043), `0x68` × 1 field (×287), `0x66` × 1 field (×287), `0x69` × 5 fields (×210) |

The few dozen bytes left at the end are probably a trailing record of a still
unknown shape.

### Map identifiers — CONFIRMED by cross-check

The first field of `encfld.bin`'s `0x69` records and of `encmons.bin`'s `0x66`
records takes the values `20001`, `20055`, `7301`, `7102`…

Community research on the `data/map/maplist9.bin` interpreter documents a map
with identifier **`0x4E22`**. `0x4E22 = 20002`, and `0x4E21 = 20001` is exactly
the first value found here.

**So this field is a map identifier.** Both files index encounters by area,
exactly the structure needed to randomize which species are met.

### Still to do (at the time)

- Meaning of the u16 pairs in `encmons.bin`'s 5-field `0x66` records. Map
  20001: `(57,1) (32,56) (63,23)`; map 7301: `(48,36) (15,45)`; map 20055:
  `(89,55)`. The sums of the second elements (80, 81, 55) are not 100, so they
  are not plain percentages. *(See §15.)*
- Respective roles of `encbtl` (battle) and `encfld` (field).
- Cross-check with overlay 17, which references all four files.

## 12. Causal confirmation in game — CONFIRMED

§10's static proof established that the file is the only source and that the
code opens it. Here is the confirmation by observation.

### Setup

`scripts/sentinel_patch.py` builds a ROM where the monster at index *i* has
`HP = 20000 + i` and `MP = 3000 + i`. These values are **impossible in the
original table**, whose MP never exceeds 255. No HP collision either (checked:
0 out of 438).

The randomizer's `shuffle` mode is **not** suitable for this check: it is a
permutation, so the randomized ROM holds exactly the same set of stat blocks as
the original. Any value found matches both tables and proves nothing. Hence the
sentinels.

`scripts/lua/monkey.lua` then gets through the intro and character creation by
hammering buttons, walks at random and saves states periodically. The intro
battle is reached around frame 18,000, about 6 minutes of machine time, with no
human input.

### The statistical trap not to repeat

A first version of the checker concluded as soon as it found the 438 sentinel
MP values in RAM. **That was wrong.** In a 16.8 MiB memory block, a given 2-byte
value appears by pure chance about `16.8e6 / 65536 ≈ 256` times. The observed
counts (94, 34, 24, 40…) are even *below* that background noise. Finding a
2-byte value proves nothing.

The criterion kept is the **full 132-byte record**. The probability of a given
132-byte sequence appearing by chance is around 2⁻¹⁰⁵⁶.

### Result

| Savestate | Context | Intact 132-byte records found |
|---|---|---|
| frame 12,033 | out of battle (Observatory) | **0 / 438** — negative control |
| frame 18,030 | **during a battle** | **4 / 438** |

The four found are indexes 277, 278, 279 and 280, at addresses `0xF5F8C2`,
`0xF5F946`, `0xF5F9CA`, `0xF5FA4E` — **exactly 132 bytes apart**.

### What this establishes

1. The engine does read `data/prm/mon_btldata.nat`, and reads the patched
   version.
2. It loads a **contiguous slice on demand**, not the whole table: the full file
   is never in RAM in one piece, and out of battle no record is there.
3. Records are copied **verbatim**. The 0xA4 = 164-byte runtime structure
   described by the community is therefore a *separate* structure built next to
   it.

The full path is validated end to end: **changing this file changes what the
engine loads in memory during a battle.**

## 13. Internal compression of GPC2 archives — type 1 ported

Every block of a GPC2 archive (index, name table, and each internal file) is
preceded by a control u32: `type = u32 & 7`, `size = u32 >> 3`. Types: 0 = raw,
1 = algorithm A, 2 and 3 = B, 4 = C.

### Algorithm A is a classic LZSS — CONFIRMED

`ArchiveTool`'s C++ source is 176 lines full of `goto`, but it contains a
`compressionType` variable set to 0 and **never reassigned**. The whole
`if (compressionType == 1)` branch is dead code. What remains:

```
control byte -> 8 flags, read from most to least significant bit
  flag 0 : copy one literal byte
  flag 1 : read two bytes b1 b2, then copy from the output
             length   = (b1 >> 4) + 3                    (3 to 18)
             distance = 1 + (((b1 & 0xF) << 8) | b2)     (1 to 4096)
```

Cross-check with the compressor in the same repository, which writes
`((length - 3) << 4) | (distance_minus_one >> 8)` then
`distance_minus_one & 0xFF`: the decompressor computes `0x30 + b1`, and since
`0x30 = 3 << 4`, that rebuilds `(length << 4) | (distance_minus_one >> 8)`. Both
directions match exactly.

Implementation: `scripts/lz_dq9.py`. Right the first time — `mon_data.gp2`'s
name table gives `mon_data_de.nat`, `mon_data_en.nat`, `mon_data_es.nat`,
`mon_data_fr.nat`, `mon_data_it.nat`.

### Types 2, 3 and 4

Also ported in `scripts/lz_dq9.py`. Type 4 is a trivial RLE (bit 7 of the
control word: literals or repeat). Types 2 and 3 form a table-driven binary
decoder whose original source contains an **overflowing unsigned subtraction** —
reproduced as is, not knowing whether it is a bug or intended.

Over the 163 internal files of the 40 `.gp2` archives in `/data/prm`:
**152 extracted, 11 failed.**

| Failure cause | Count | Status |
|---|---|---|
| **type 7** compression | 5 | undocumented. The community source itself notes "5-7 are unknown". |
| type 2 or 3, absurd announced size | 6 | 2 to 3.8 MiB announced from a 212 KiB archive (60×). Probably a misread control word, or my `DecompressB` port is wrong. |

The 11 files are all `actdt_*` — skill data, unrelated to monsters. Not
blocking, left open.

### Name pairing trap

In the archive, the name table matches the index entries **sorted by masked
offset**, not by hash (that is what `fileEntrySorter` does in the source).
Checked by content: in offset order, the languages come out `de, en, es, fr, it`
in every tested archive. Sorting by hash gives a wrong and **silent** pairing —
French names in a file labelled `_en.nat`.

## 14. Monster names — CONFIRMED

File: `mon_data_<lg>.nat`, inside `data/prm/mon_data.gp2`, one variant per
language. The game code references the template `mon_data_<LG>.nat`.

```
+0x00   u16   count in the low 12 bits: u16 & 0xFFF = 438
              The high 4 bits are flags that vary by language (0x0, 0x1, 0x3,
              0xC). Same convention as the GPC2 header's packedFileCount.
+0x02   u16   ?
+0x04         438 records of 28 bytes:
                +0x00  u32  name offset, in the pool
                +0x04  u32  model code offset
                +0x14  u32  plural name offset
                (the other 12 bytes are still unknown)
        then  optional zero padding
        then  the pool: zero-terminated strings
```

Consistency check: for English, `4 + 438 × 28 = 12,268 = 0x2FEC`, exactly the
offset of the string `slime`. And all 438 name offsets point at a real string
start, **in all five languages**.

So this is a **direct index → name** mapping for all 438 records.
Implementation: `scripts/monnames.py`.

### Text markup

Diacritics: `<'e>` = é, `` <`a> `` = à, `<^e>` = ê, `<:a>` = ä, `<~n>` = ñ,
`<ss>` = ß. Grammatical inflection, mostly in German and French: `[gs]` genitive
singular, `[adjf]` feminine adjective, `[sgl_inf_1]`… The engine resolves them
at display time; for us they are noise.

### Three cross-validations

**1. Meaning against stats.** Every monster whose name contains "metal slime"
has an abnormal defence, without exception over 7 entries:

| index | name | HP | DEF | XP |
|---|---|---|---|---|
| 2 | metal slime | 4 | 256 | 4,096 |
| 26 | liquid metal slime | 8 | 256 | 40,200 |
| 112 | metal slime knight | 46 | 140 | 305 |
| 167 | **metal king slime** | 16 | **512** | 54,504 |

**2. The series' legacy bosses** are at indexes 330 to 344, **consecutive**
identifiers 500 to 514, models `b100a` to `b112a` in the exact order from DQ1 to
DQ8 — Dragonlord, Malroth, Baramos, Zoma, Psaro, Estark, Nimzo, Murdaw,
Mortamor, Orgodemir, Dhoulmagus, Rhapthorne, Nokturnus — all between 6,000 and
8,500 HP.

**3. DQ9's story bosses** are at indexes 292 to 302, in story order, with
**King Godwyn and Corvus in two forms** each (models `b019a`/`b020a` and
`b022a`/`b023a`).

Only one entry out of 438 has no name: index 437, identifier 900 — the
32,000-HP training dummy. 55 names are carried by several entries: the
strengthened grotto variants (`stenchurion` at 160 then 300 HP).

### A method error, corrected

A first attempt rebuilt the mapping by **grouping** pool strings into
`(name, plural, model code)` triplets. That heuristic gave a wrong alignment,
shifted by 3 from index 249, because the pool holds 5 groups with no name (two
consecutive model codes). It put `Dragonlord` where `Dreadmaster` actually is.

Reading the 28-byte record table removes any heuristic: it gives the exact name
offset of each monster.
