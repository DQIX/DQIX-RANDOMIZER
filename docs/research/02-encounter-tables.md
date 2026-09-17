# 2. Encounter tables, scripted battles and the save file (§15–§18)

Part of the [research notes](README.md). Sections keep their original numbers.

## 15. Encounter tables — DECODED

Three files in `/data/prm`, all in the tagged table format of §3. ARM9 overlay
**17** references them, together with `fld_mondata.bin`.

| File | Records | Role |
|---|---|---|
| `encmons.bin` | 209 | species per map |
| `encfld.bin` | 1,827 | field encounters |
| `encbtl.bin` | 2,874 | battle encounters |

### Where the identifiers are — measured, not assumed

For each combination (file, tag, field count, position), we counted the share
of non-zero values that are valid monster identifiers, under several splits.
The result leaves no doubt:

| File | Tag | Field | Values | Low 12 bits = valid id |
|---|---|---|---|---|
| `encbtl.bin` | `0x66` | 0 | 1,058 | **100.0 %** |
| `encbtl.bin` | `0x67` | 0 | 1,526 | **100.0 %** |
| `encfld.bin` | `0x67` | 0 | 1,043 | **100.0 %** |

That is 3,627 values whose low 12 bits are *all* valid identifiers. There are
only 438 valid identifiers out of 65,536 possible values: such a rate is
impossible by chance.

The high bits carry something else. In `encfld.bin` tag `0x67`, `value >> 12`
only takes values 0 to 7 — most likely a spawn weight or probability. They are
kept as they are.

### `encmons.bin` — species per map

Tag `0x66` records, 3 to 5 fields:

```
field 0        map identifier
fields 1..n    two u16, each possibly holding a monster identifier
```

The **high u16** is a valid identifier 100 % / 99.2 % of the time over all
data fields. The low u16 is valid most of the time, but only 14 % on one field:
its exact meaning is not worked out.

Map identifier confirmation: the community documentation of
`data/map/maplist9.bin` cites map `0x4E22` = 20002; the first value found here
is `0x4E21` = 20001.

Semantic validation, once names were available:

| Map | Species |
|---|---|
| 20001 | cruelcumber, slime, batterfly, teeny sanguini, sacksquatch, bodkin archer |
| 7102 | bag o' laughs, firespirit, spirit, funghoul, mecha-mynah, dracky |
| 40412 | seavern, pale whale, drakulord, hammer horror, prime slime |

Groups of even difficulty, and maps sort cleanly by median bestiary index: 13
for the starting areas, 234 to 268 for the final ones. 1 to 6 species per map,
most often 5.

### Other tags, not worked out

- `encfld.bin` tag `0x69`, 5 fields: field 0 is a map identifier, the four
  others are zero in all 210 records. A header record.
- Tag `0x68`, 1 field, 289 distinct values all below 4,096: appears as a
  separator before each run of `0x66`/`0x67`. Probably an encounter group id.
- `encfld.bin` tag `0x66`, 1 field: only 38 % valid identifiers, unknown meaning.
- About thirty bytes at the end of `encbtl.bin` and `encfld.bin` are not parsed.

### Safety rule when writing

`scripts/enctables.py` rewrites **only the slots that already hold a valid
identifier**, at the positions measured above. A field of unknown meaning
therefore stays intact by construction — it cannot be corrupted.

Total: **4,525 rewritable species references** (`encbtl` 2,584, `encfld`
1,043, `encmons` 898).

### Verification status at the time

The decoding above is solid at the **file** level: identifier positions are
measured at 100 % over 3,627 values, the rewrite is checked (strict
permutation, 0 inconsistency, no invalid value written), and the groups per map
make sense.

But **in-game confirmation was not yet obtained.** Two facts:

1. On the randomized ROM, the prologue battle (Observatory, level 1 hero with
   Aquila) shows **the same species as the original ROM** — `slime` and
   `cruelcumber`, the original list of map 20001, not the randomized one.
2. No record of the three encounter tables, original or patched, is found in RAM
   in the savestates taken so far — while the patched stat table is (4 records
   of 132 bytes, §12).

Two explanations remained:

- the prologue is **scripted** and does not read these tables, its species
  being defined in event data (`/data/event`, `/data/scenario`);
- the engine **converts** these tables when loading them, which defeats a byte
  search. Community documentation describes a "monster table" in RAM at
  `0x020FDDC4` filled by `ChooseFieldMonsterId`, i.e. a runtime structure.

Do not confuse "the file bytes are correctly changed", which is established,
with "the game behaves differently", which was not yet.

Test to settle it: a ROM where **every** encounterable species is replaced by
the `metal slime` (identifier 3, 4 HP, defence 256, metallic look). 4,516 of
4,525 references replaced, only the empty-slot marker `65535` remains. If the
tables feed the engine, every non-scripted encounter must show a metal slime and
nothing else — a difference impossible to miss, unlike a swap between two
similar species. Built by `scripts/enc_sentinel.py`. *(Result: §16 and §18.)*

## 16. `data/event/eventbattle.bin` — scripted battles — CONFIRMED

Found by searching file path strings in the code: `data/event/eventbattle.bin`
is referenced by the **decompressed ARM9** and by **overlay 17**.

This file explains why randomizing `encmons`/`encfld`/`encbtl` changes nothing
in the prologue battle.

Format: short header (body at `0x10`), 98 tag `0x64` records of **9 u32
fields**:

```
field 0   event identifier                  1 to 142
field 1   identifier of monster 1           100 % valid identifiers
field 2   count of monster 1                1 to 8
field 3   identifier of monster 2           or 0xFFFFFFFF if the slot is empty
field 4   count of monster 2
field 5   identifier of monster 3           or 0xFFFFFFFF
field 6   count of monster 3
field 7   ?                                 15 distinct values, 23 to 38
field 8   message identifier                30116 to 30903
```

### Validation

The content is DQ9's complete boss roster, in story order: Wight Knight, Morag,
Ragin' Contagion, Master of Nu'un, Lleviathan, Garth Goyle, Tyrantula, Grand
Lizzier, Dreadmaster, Larstastnaras, Gadrongo, Greygnarl, the Gittish trio
(Goreham-Hogg, Hootingham-Gore, Goresby-Purrvis), King Godwyn, Corvus,
Barbarus — then the legacy bosses Dragonlord → Rhapthorne **repeated three
times**, matching the three difficulty tiers of post-game rematches.

Multi-enemy battles are consistent: `[17] bad karmour, Hootingham-Gore, bad
karmour` and `[54] right claw, Mortamor, left claw`.

### The prologue proof

Record `[26]` is `1x slime, 1x cruelcumber, 1x slime` — exactly what the screen
shows in the prologue battle (level 1 hero with Aquila).

The identifiers used are 290 and 292, **not** 1 and 57: they are bestiary
duplicates (`slime` carries identifiers 1, 249, 250, 290, 291, with sometimes
identical stats). Consistent with §14's 55 names carried by several entries.

Decisive test: a ROM where **all** species of the three encounter tables are
replaced by the `metal slime` leaves the prologue battle **unchanged** (`slime`
and `cruelcumber` on screen). The battle is scripted, read from
`eventbattle.bin`.

### Randomization

`scripts/enctables.py` handles this file, but the randomizer puts it behind a
**separate flag** `--boss`, apart from `--rencontres`. Reason: touching story
bosses is far riskier for progression than swapping field species. A final boss
too weak trivializes the game; an early boss too strong blocks it.

Rewritable references: 112 in `eventbattle.bin`, for a total of **4,637** with
the three encounter tables.

### Causal confirmation in game — CONFIRMED

Two ROMs identical but for one thing: in one, `eventbattle.bin` is patched (every
species replaced by `metal slime`, identifier 3); in the other, only the three
encounter tables are. Same button-mashing seed, so same run, and a savestate
taken at the same frame during the prologue battle.

We then search RAM for the enemy runtime structure, described by the community
as `+0x04 maxHP, +0x06 maxMP, +0x08 attack, +0x0A defence`, i.e. 8 consecutive
bytes per monster.

| RAM occurrences | `metal slime` (4/255/35/256) | `slime` id 290 (8/2/10/7) | `cruelcumber` id 292 (10/2/12/9) |
|---|---|---|---|
| `eventbattle` **not** patched | 1 | **3** | **2** |
| `eventbattle` **patched** | **5** | **0** | **0** |

Without the patch, RAM holds three slime structures and two cruelcumber ones —
what the screen shows (two slimes and one cruelcumber, plus extra state slots).
With the patch: neither species anymore, and five metal slimes.

The swap is total and goes both ways. That is the causal proof: **changing
`eventbattle.bin` changes the monsters the engine instantiates.**

### Still unconfirmed in game at this point

The three field encounter tables (`encmons`, `encfld`, `encbtl`) are decoded and
correctly rewritten at the file level, but their effect in game is not yet
observed: the prologue does not read them. *(Confirmed in §18.)*

## 17. `ChooseFieldMonsterId` disassembled — the format confirmed by code

EUR address provided by the community: `0x02073FEC`. It falls in the ARM9
(`0x02000000` to `0x020F4618` once decompressed), so at offset `0x73FEC` of
`work/dumps/code/arm9_decompresse.bin`. Disassembled with `capstone`.

```
02073fec  push  {r3, r4, r5, lr}
02073ff0  mov   r4, r0              ; r0 = pointer to the table in RAM
02073ff4  mov   r0, #0              ; total = 0
02073ff8  mov   r2, r0              ; i = 0
; --- first loop: sum of weights ---
02074000  add   r1, r4, r2, lsl #2  ; 4-BYTE entry, indexed by i
02074004  ldrh  r1, [r1, #8]        ; u16 of the entry, table from +8
02074008  add   r2, r2, #1
0207400c  lsl   r1, r1, #0x11       ; << 17
02074010  add   r0, r0, r1, lsr #29 ; total += (x << 17) >> 29
02074014  ldrh  r1, [r4, #2]        ; entry count = u16 at +2
0207401c  blt   #0x2074000
02074020  bl    #0x2032380          ; random draw
; --- second loop: weighted lottery ---
02074030  add   r3, r4, #8
0207403c  ldrh  r1, [r3, r1]
02074044  add   lr, lr, r2, lsr #29 ; running sum of weights
02074048  cmp   r0, lr              ; compare to the draw
0207404c  lsllt r0, r1, #0x14       ; << 20
02074050  lsrlt ip, r0, #0x14       ; >> 20  -> keeps the low 12 bits
02074068  mov   r0, ip              ; return value
0207406c  pop   {r3, r4, r5, pc}
```

The two bit extractions:

| Instruction | Effect | Meaning |
|---|---|---|
| `(x << 17) >> 29` | keeps bits **12 to 14** | 3-bit weight, 0 to 7 |
| `(x << 20) >> 20` | keeps bits **0 to 11** | 12-bit monster identifier |

**This confirms by code the format deduced in §15.** Both statistical
measurements match the real mechanics:

- the low 12 bits are a valid identifier 100 % of the time over 3,627 values →
  that is the field the function returns;
- `value >> 12` only takes values 0 to 7 in `encfld.bin` tag `0x67` → that is a
  3-bit weight.

The function implements a classic weighted lottery: sum of weights, draw, then
a cumulative walk until the draw is passed.

### What remains inferred

The function reads a table **in RAM**, whose pointer comes in `r0`. The chain
file → RAM table was not traced instruction by instruction. What is established:
the file holds exactly the layout the code consumes (4 bytes, 12-bit identifier,
3-bit weight), and it is the only source of these identifiers in the whole ROM.
*(The last link is confirmed by observation in §18.)*

### Why in-game confirmation failed at first

Three attempts, all blocked by the test harness and not by the ROM — details in
the internal journal. The last one: the auto-pilot stays stuck in the prologue
battle, never confirming an attack. Reaching a free-roam area needed either much
finer driving or an advanced save file.

## 18. Save file and RAM addresses from cheat codes

### The folder provided

DeSmuME layout (`Battery`, `Cheats`, `States`, `StateSlots`), from a game really
played. The ROM it contained is **bit-identical** to the reference ROM
(`3a63438fff7db282fa3133e8fd020e85`), so every offset and address in these notes
applies to it without revalidation.

### DeSmuME `.dsv` format

```
[raw save data]
"|<--Snip above here to create a raw sav by excluding this DeSmuME savedata footer:"
u32 x6  footer fields: 0x8011, 0x10000, 0x3, 0x2, 0x10000, 0x0
"|-DESMUME SAVE-|"
```

The file documents itself: the `|<--Snip above here` marker is exactly where
the raw data ends. Here **65,536 bytes** (64 KiB, 512 Kibit), as the footer's
`0x10000` field confirms.

### Internal structure: two mirrored copies

The fill profile per 4 KiB block is **strictly identical** between
`0x00000-0x07FFF` and `0x08000-0x0FFFF` (46.6 / 29.6 / 65.5 / 43.6 / 14.3 /
11.6 / 8.3 / 100 %, twice). DQ9 keeps two 32 KiB copies: a main one and a
backup. Keep this in mind for any save patch — changing only one copy may fail
the game's integrity check.

### Converting for BizHawk

BizHawk expects the save in `NDS/SaveRAM/`, in **raw** format (as extracted
above), and names the file after the **game's internal name**, not the ROM file
name. Underscores become spaces: ROM `dq9_encsent3.nds` expects
`dq9 encsent3.SaveRAM`. A copy named `dq9_encsent3.SaveRAM` is silently ignored.

The internal name can be read from Lua with `gameinfo.getromname()`.

### EUR RAM addresses from the cheat file

The provided `.dct` file holds Action Replay codes for `NTR-YDQP-EUR`, so
**genuine EUR** addresses, proven by use.

| Address | Code effect | Interest |
|---|---|---|
| `0x020FD764` | inn level | global state block |
| `0x020FD768` | guestbook | same |
| `0x020FD76C` | inn upgrades | same |
| `0x020FD778` | unlocked visitor rooms | same |
| `0x020FA92A` | visitor count | same |
| `0x02108B11`…`0x02108B75` | quest flags | progression table |
| `0x021098C0`…`0x021098D8` | downloadable content | — |
| `0x0215525C`, `0x02155270` | code patch (2 instructions) | **overlay** area (`0x021536E0`+) |
| `0x02066A58` | code patch: text speed | ARM9 |
| `0x020A2358`, `0x020A23C8` | code patch: free camera | ARM9 |
| `0x023893D1`, `0x023893E4`, `0x02389404` | DQVC shop unlock | top of main RAM |

**Notable cross-check.** The `0x020FD764`-`0x020FD778` block sits next to the two
community-documented addresses: `0x020FDAAC` (map structure) and `0x020FDDC4`
(monster table read by `ChooseFieldMonsterId`, §17). The `0x020FD000`-`0x020FE000`
area is the game's global state block. Two independent sources converge.

The code `94000130 FFFB0000`, present several times, is the standard "SELECT held"
conditional: `0x04000130` is the NDS `KEYINPUT` register.

### In-game confirmation of field encounters — CONFIRMED

Obtained with an advanced save provided by the player, who took the party to an
open plain and saved a state.

**Setup.** ROM `dq9_encsent3.nds`: the 4,510 species references of the three
encounter tables replaced by species 1, `data/event/eventbattle.bin` left
intact. Built by `scripts/enc_sentinel2.py`.

**Visual check.** The plain now only has slimes, where it normally shows varied
species.

**Live memory read**, on the savestate, at the community-documented EUR address
`0x020FDDC4`, applying the format from the disassembly (§17):

```
ChooseFieldMonsterId @020FDDC4 :  count = 4
    ids     = {1, 1, 1, 1}
    weights = {3, 3, 5, 5}
```

All four slots carry identifier **1**, the sentinel. The weights are 3-bit
values.

**The chain is complete and checked link by link:**

| Link | Check |
|---|---|
| patched file | 4,510 references rewritten, strict permutation |
| RAM table | `ids = {1,1,1,1}` read at `0x020FDDC4` |
| entry format | 4 bytes, 12-bit id, 3-bit weight — disassembly §17 |
| consuming code | `ChooseFieldMonsterId` returns the low 12 bits |
| on screen | only slimes on the plain |

The "file → RAM table" link, still an inference in §17, is now established by
observation.
