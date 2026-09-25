# 12. Scripted bosses: the full roster, and the hook that can draw one per fight

Measured 22 September 2026 on the European ROM, from
`data/event/eventbattle.bin` (98 records, tag `0x64`, 9 u32 fields — format in
[02-encounter-tables](02-encounter-tables.md) §16).

## Why this page exists

The 1.4 randomizer permutes boss species once, at build time. A boss you meet
twice is therefore always the same stand-in. The player asked for the opposite:
**a boss drawn at the moment the battle starts, held for the length of that
fight, and forgotten afterwards**, so the bosses you can re-fight give someone
else next time. That needs to know exactly which battles are re-fightable, and
where in the code the species is chosen. Both are below.

## The roster, in story order

Record index, event id, species. Names are the French ones the game ships.

| # | evt | who | note |
|---|-----|-----|------|
| 0 | 26 | gluant ×1, concombrageur ×1, gluant ×1 | the prologue battle |
| **1** | **2** | **hexacorne (300)** | **first boss, fought with no party** |
| 2–11 | 0,1,3–10 | chevalier Karbon, Sylvane, Épidémon, Blaisephème, Moby Pick, garde Gouille, Tyrantule, Balthézard, Directueur, Larstastnaras | story |
| 12 | 131 | Aquila (800) | scripted, not a real fight |
| 13–17 | 11–15 | Gadrongo, Grizius, then three mixed groups | story |
| 18–24 | 16–19 | **general Mac Assin (313), Mac Hulotte (314), Mac Léo (315)**, king Govin (316) | the Gittish empire, first meeting |
| 25–26 | 134,135 | king Govin (317), Corvus (801) | |
| **27–29** | **20,21,22** | **Mac Assin (344), Mac Hulotte (345), Mac Léo (346)** | **the three generals, second meeting** |
| 30–32 | 23,24,25 | Corvus (319), Barbarus (318), Corvus (320) | end of the story |
| 33–38 | 27–32 | Moby Pick (347), Fourax, Médhor, king Godefroi, Tyrannamort, Atoner | post-game |
| 39–42 | 33,136–138 | scarlatin ×4 (284, 287, 288, 289) | |
| **43–54** | **34–45** | **Équinocte (216), Némée (234), Monte-gluancien (225), Trauminator (227), Grévanescent (332), baron Hémoglobon (322), Atlas (219), Hannimal (335), Volattila (336), Charibaldi (337), Tyrannomort (326), Grizius (338)** | **the lair bosses (grottes), re-fightable at will** |
| **55–93** | **46–84** | **Lordragon, Malroth, Baramos, Zoma, Psaro, Estark, Nimzo, Meurtor, Mortamor + his two claws, Nokturnus, Orgodémir, Dhoulmagus, Rhapthorne — the same thirteen, three times** | **the legacy bosses, three difficulty tiers, re-fightable** |
| 94–97 | 139–142 | slime groups, and one mixed group | |

### What this changes for the design

* **The three Gittish generals already have two records each**, with *different
  species ids* (313/344, 314/345, 315/346). A build-time permutation therefore
  already gives a different stand-in for the rematch. They are not the problem.
* **The lair bosses and the legacy bosses are.** Each is one record, fought as
  many times as the player likes, so the species must be drawn per encounter,
  not per build.
* **Hexacorne, species 300, is the one to be able to spare.** It appears once
  in `encfld.bin`, once in `encbtl.bin` and once in `eventbattle.bin`, and
  nowhere else — so removing it from the permutation pool before the shuffle
  leaves all three untouched. That is `--boss-garder-premier`, on by default in
  the application.

## Where the engine picks the species — CONFIRMED (static)

`data/event/eventbattle.bin` is named in the decompressed ARM9 at `0x020f0d40`
and in overlay 17. The ARM9 pointer to it lives at `0x02074174`, used by the
loader at `0x02074124`, which hands the buffer to the walker at `0x0207417c`.

The record parser is **`0x02074070`**, called once per record:

```
02074070  push {r4,r5,r6,lr}
02074074  mov  r5, r0          ; r5 = the record
02074078  add  r5, r5, #8
0207407c  bl   0x2030b1c       ; read one u32 field, advance
02074080  ldr  r1, [pc,#0x94]  ; -> 0x20f0d2c, the requested event id
02074088  cmp  r0, r1
0207408c  movne r0, #1         ; not this record: keep walking
02074094  ldr  r6, [pc,#0x84]  ; -> 0x2108dd8, the destination struct
020740a0  strh r0, [r1]        ;   +0x00  event id
020740a8  ...                  ; loop i = 0..2
020740b8  strh r0, [r1,#2]     ;   +0x02/+0x04/+0x06  SPECIES i
020740d0  strh r0, [r1,#8]     ;   +0x08/+0x0a/+0x0c  count i
020740f0  strh r0, [r1,#0xe]   ;   +0x0e  field 7
02074108  strh r0, [r1,#0x10]  ;   +0x10  message id
02074114  strh r2, [r1,#0x12]  ;   +0x12  zero
```

`0x020740b8` is the one instruction that writes a boss species into the
structure the battle system then reads. A graft there sees the species in `r0`
and the destination in `r1`, and can substitute a draw.

### Two call sites, not one — CONFIRMED (static)

`0x02074124` is the lookup: **r0 = destination structure, r1 = event id**. The
globals `0x02108DD8` and `0x020F0D2C` are only where the walker stashes those
two arguments for the per-record callback. Exactly two `BL` reach it, both in
overlay 17:

| site | destination | what it looks like |
|---|---|---|
| `0x021B72E8` | `sl + 0x2C`, a field of a live object | the battle context being built |
| `0x021B8AE0` | `sp + 0`, a 20-byte stack temporary, then a loop over the three species and their counts, returning −1 on failure | a query: *which monsters will this battle need?* |

**So a boss battle looks the record up twice.** Drawing independently at each
call would answer one boss to the query and another to the battle — a
preloaded model that does not match the monster on screen. That is the exact
shape of the field-monster bugs that cost this project weeks, and it settles
the design: the draw must be **cached by event id**, so both call sites get the
same answer.

### What clears the cache, and why that is the whole problem

The cache has to be forgotten between two fights of the same boss, or the lair
bosses would still be fixed for the whole save. The signal to clear it must
happen **after** both lookups, never between them:

* clearing at battle *entry* is wrong — the query at `0x021B8AE0` probably runs
  on the field, before entry, so entry falls between the two calls;
* clearing at **map mount** is right: the field is remounted on the way back
  from a battle, and that is a hook the randomizer already owns (the blob's
  trigger, [08-relocatable-blob-and-eviction](08-relocatable-blob-and-eviction.md)).

And the degradation is clean: if the clear never fires, every battle keeps its
first draw, which is exactly the 1.4 behaviour — a fixed boss per encounter,
never a mismatched model.

### Measured, 24 September: **one** lookup per battle

`scripts/lua/eventbattle.lua` on the player's savestate, taken standing in
front of Équinocte on a chaos build:

```
chargement de ... dq9 15 chaos b.MelonDS.QuickSave3.State
   1  image   64835  demande 34  evt 34  especes 305/65535/65535  nombres 1/0/0
fini : 1 recherche(s) de combat scripte
```

Event 34 is Équinocte's lair, species 305 is Moby Pick — exactly the
substitution the player saw. **One lookup, not two.** The probe would have
caught a second one: it overwrites the requested-id global with a marker after
reading it, so any further lookup shows up as a return to a sane value.

That removes the constraint this page was built around. Two call sites exist
in overlay 17, but only one runs for a given battle, so **a draw made at that
single lookup needs no cache**: the species is decided once and read once.
Re-entering the lair runs the lookup again and draws again — which is exactly
the "no memory afterwards" the player asked for.

### Still to measure in the emulator

Whether the same holds for a multi-monster scripted battle (record 63,
`right claw + Mortamor + left claw`) and for the prologue. `scripts/lua/eventbattle.lua`
counts the lookups without an execution breakpoint: the caller writes the
requested event id into `0x020F0D2C` before walking the table and the callback
only reads it, so the probe reads that word each frame, logs it with the
destination structure, then overwrites it with a marker. Each return to a sane
value is one more lookup — which makes two lookups of the *same* battle
visible, where watching for a change of value would not.


## Measured, 24 September (evening): one table walk, with the blob installed

Execution witnesses on the same savestate (`eventbattle.lua` with a RAM
patch, `DQ9_PATCH`), from standing in front of Équinocte to the first battle
menu:

| witness | count |
|---|---|
| lookup `0x02074124` | 1 |
| record parser `0x02074070` | 44 (it walks the records until the id matches) |
| species store `0x020740B8` | 1 |

The requested-id word is sometimes written twice by the caller (the probe saw
two or three "lookups" 29 frames apart), but the table is **walked once per
battle**. And at that moment the field blob is **installed**: `BLOB_BASE`
(`0x020F1CD8`) is non-zero and the model-loader site `0x021A21F8` holds the
blob's `bl`. A blob graft on `0x020740B8` therefore runs at the lookup.

A RAM-injected copy of the graft did **not** run on the savestate: the
emulated ARM9 instruction cache kept serving the original `strh`, and a Lua
memory write cannot invalidate it. The real blob does: its installer flushes
and invalidates the range it patches (`PLAGE_AMORCE` widened to cover
`0x020740B8`).

## The lair graft (ZER-37)

The player's rule: a story boss is drawn once and stays until beaten (the
build-time permutation already does that); the three Gittish generals get a
different boss for the rematch (already true: two records, two species, a
bijective permutation); **a lair boss changes each time the lair is loaded**.
The twelve lair bosses (events 34–45, records 43–54) exist only in
`eventbattle.bin` — no field symbol in `encfld`, `encbtl` or `encmons` — so
drawing at the lookup cannot desynchronise a symbol from its battle.

`greffe_antre` replaces the store at `0x020740B8`: for slot 0 of events
34–45 it draws from the true-boss pool (88 species with Hexacorne kept), and
remembers the draw per lair in the blob. The blob is re-read from the ROM at
every map mount, so the memory lasts exactly one visit. Legacy bosses
(events 46–84) keep their build-time draw, by the player's choice. Only with
`--boss`.
