# 17. Battle groups, boss families, drop rates, the Whistle and technique weapons (§95–§99)

Part of the [research notes](README.md). Work of 28–29 September 2026 for
1.6 (ZER-67, ZER-69, ZER-70, ZER-60/62/71), static analysis and unicorn
emulation; in-game checks pending.

## §95 Battle groups: why blob monsters fight alone (ZER-67)

### 95.1 How a field contact builds the battle

On contact with a field symbol, overlay 17 (`0x021B74AC`) calls
`GenerateCompanionByBT` (ARM9 `0x0209AFE4`, name from the community symbols,
§56) with `r0` = the loaded `encbtl` areas (context `+0x124`), `r1` = the
touched species, `r2` = the area id. The loaded table holds six areas of
`0x4C` bytes:

    +0x00  u16  area id (the `0x68` record of encbtl.bin)
    +0x04  6 × 8 bytes   LEADERS  (the 0x66 records): u32 packed, species in
                          bits 0-11, group-size fields above, + 4 bytes
    +0x34  6 × 4 bytes   COMPANIONS (the 0x67 records): species in bits 0-11,
                          weight in bits 12-14 (the `lsl #17, lsr #29` reads)

`0x0209B8E4(areas, species, area, &index)` finds the area, then the touched
species among its **leaders**, and returns the 8-byte leader entry or 0. Then:

    0x0209B02C  species 38..40 (the three chest ambushes) -> one monster
    0x0209B050  cmp sl, #0 ; strheq r6, [r4, #6] ; beq end   -> NOT A LEADER:
                                                                ONE MONSTER
    else        the leader's packed fields give 1 to 3 groups and their
                sizes; companions are drawn from the area's six (weights),
                with the BT generator (`0x0207430C(rng, n)` -> [0, n))

With the blob, the species that spawns is drawn from the whole bestiary; it is
almost never one of the area's leaders, so **the battle is that monster
alone**. That is the player's report (1.6 test ROMs). `GenerateCompanionByAT`
(`0x0209B458`, other caller `0x021B73A0`) has the same shape, and falls back
to species `0x10` alone.

### 95.2 The graft

`greffe_groupe` (blob, `--sans-groupes` to disable) replaces `cmp sl, #0`:
when `sl` is 0, it finds the area whose id is `r8` in `sb`, counts its
non-empty leaders, draws one with the function's own generator (`r5`,
`0x0207430C`), and returns it in `sl` as a TEMPLATE; the touched species
stays the leader (`strh r6, [r4]` already happened at `0x0209B00C`). It ends
with `cmp sl, #0`, whose flags the next two instructions read. A leader found
by the game is left alone; an area without leaders, or unknown, still gives
one monster. Emulated in unicorn (`scripts/emu_groupe.py`: kept leader,
template drawn and each leader reached, empty area, unknown area, single
leader; registers and flags). The site is in the ARM9: a fifth cache range
(`0x0209B040`, 0x20) is flushed and invalidated at install and uninstall, and
the site table gets one more entry — only when the option is on, so the blob
of `--sans-groupes` is byte-identical to 1.5's (A/B checked).

Companions are the area's `encbtl` species (permuted with the encounters).
In-game check pending: companion count and variety on the plain.

## §96 Drop rates with the blob (ZER-69)

The battle takes a monster's drop rate classes, exp and gold from the zone's
`mon_moddata` copy (+0x30/+0x31, +0x28, +0x2C) for zone species, and keeps
the `mon_btldata` values (+0x02/+0x03, +0x08, +0x0C) for species drawn by the
blob (§94.4). **The two files agree on all 438 records** for these fields
(`work/zer69/taux.py`): mean chance per defeated monster 7.41 % common,
2.73 % rare, either way. The per-battle drop graft (§90) replaces the ITEM
only; its `rares` mode rejects a 4–5★ item 7 times out of 8 and draws again,
it never empties a slot. So the chance per defeated monster is vanilla. What
changed is the number of monsters per battle: one instead of a group (§95),
so fewer rolls per battle. Fixed by §95.

## §97 Boss families (ZER-70, 60, 62, 71)

`eventbattle.bin` sorts its boss fights by event id: 2–33 and 131–138 story
(32 species, post-game quests included), 34–45 grottos (12), 46–84 legacy
bosses (45: thirteen bosses in three levels each, and Mortamor's claws).
`scripts/categories_boss.py` holds the lists and checks them against the file.

Measured with `--boss` over 40 seeds (`work/zer70/mesure.py`): a story fight
gets a story boss 34 %, a legacy boss 52 %, a grotto boss 13 % — the uniform
permutation of 89 species follows the species count, and legacy bosses count
three times. Story bosses were never excluded.

1.6 modes (`scripts/tirage_boss.py`): `--boss-familles-egales` (family first,
a third each), `--boss-histoire` (story bosses among themselves, other fights
vanilla), `--boss-mixte` (bestiary monsters as one more family),
`--boss-chaque-combat` (the blob's `0x020740B8` graft, generalised from the
lairs of §84: a per-event slot mask, families, monster bitmap; a new draw at
every eventbattle lookup, i.e. every battle entry, on maps where the blob is
mounted). `--boss` alone keeps its path and its ROM (A/B checked). The graft
is emulated for every event, slot and family (`scripts/emu_boss.py`).

## §98 The Whistle spawns nothing (ZER-68)

The field Whistle is a task of overlay 17 (constructor `0x021C2744`, type
`0x45`, species `-1` at `+0x18`; update `0x021C2784`). State 0 plays the
sound and waits; state 1 calls the spawn wrapper `0x021A23E4` ONCE
(`0x021C296C`) with that species. Species `< 0` goes to the fallback draw at
`0x021A24CC` (`bl ChooseFieldMonsterId`), which the blob routes through
`tirage_unique` (§85). Result 0 -> state 2 (failure: a message, then state 3
ends the task); non-zero -> state 5, which also writes `[player+0xC3] = 0`.

With the blob, `tirage_unique` returns -1 whenever the drawn species' model
cannot be loaded — the model heap full, the player's choice of ZER-42 (no
monster without its own model). The field tick simply retries the next frame;
the Whistle does not retry: nothing appears. The failure path never clears
`[player+0xC3]`, the likely cause of "then we walk through monsters"
(inferred, not measured).

Fix (default, `--sifflet-sans-repli` for the 1.5 code): at the FALLBACK site
only (the caller's return address, read from the stack), a failed draw takes
the species of a random LIVE field actor — its model is in memory, the spawn
succeeds. An exception to "never the same species twice on screen", limited
to one-shot spawns with a full heap. Emulated in unicorn
(`scripts/emu_sifflet.py`: live-actor fallback on three ranks, the tick
unchanged, eight duplicates, no live actor).

**That was not the cause (in-game test, 11/10/2026).** Traced on the bench
(`work/v16/sifflet.lua`, hooks on `0x021C296C`, `0x021A24CC` and their
returns): the fallback draw DID return a species (257), and the wrapper still
returned 0. After the draw, the wrapper looks the species up in the map's
container (`add r0, sb, #0x2f8` ; `bl 0x0206F500` at `0x021A24E8`, a
BinarySearch with extractor `0x0206EF50`) and gives up when it is not one of
the map's own species. Vanilla never meets this (the drawer only returns map
species); with the blob it almost always does. The field tick does not go
through the wrapper: it calls `0x021A2128`, whose identical lookup
(`0x021A2164`) the blob already routes to `portier1` (map container, then the
blob's source table). Fix: `0x021A24E8` -> `portier1` too, as one more site
of the blob table, with `sifflet`. Checked on the bench: the wrapper returns
5 and a battle starts (species 123); confirmed in game by the player. Both changes stay: the live-actor
fallback still covers a full model heap.

## §99 Which weapon a technique needs (ZER-65)

`skilltable.bin` is re-read at load into a table of 12-byte records (ARM9
handler `0x0209A114`, registered for tag `0x66` in the table at `0x020F15E8`;
file read by `0x0209A358`):

    +0  bits 0-10 field 0 (palier id)    bits 11-15 field 4 (nature)
    +2  u16       field 3 (action id)
    +4  bits 0-4  field 1 (TREE)         bits 5-11 field 2 (cost)
        bits 12-19 field 5 (value)       bits 20-24 field 8 (message)
        bits 25-31 cleared (`bic r2, r1, #0xfe000000` at 0x0209A204)
    +8  u16 field 6        +10 u16 field 7

The battle's technique filter (overlay 0, loop at `0x0217C3D0`, `0x93`
entries) looks each learned technique up BY ACTION (`0x0209A624`, key `+2`,
its only caller) and compares `+4` bits 0-4 with the category of the equipped
weapon (`[item] bits 7-10`) and shield; no weapon means category 14; a tree
above 14 (vocation trees) always passes. So the required weapon is the tree
the technique SITS in — hence, with `--aptitudes-chaos`, the arrival tree's
weapon, while the animation (in the action data) keeps the origin weapon.

`--aptitudes-arme-origine` (`scripts/patch_lien_arme.py`): every ability
record gets its ORIGIN tree (vanilla field 1 of its palier id, which travels
with the charge) in bits 5-9 of field 8. The game reads only five bits of the
message number (§88), so nothing shows. Five instructions of the handler
change (no new code) so that field 8 lands on ten bits at `+4` bits 20-29
instead of five with 25-31 cleared; four shifts of the filter
(`0x0217C424`, `0x0217C444`, `0x0217C46C`, `0x0217C488`: `lsl #0x1b` ->
`lsl #2`) read bits 25-29 instead of 0-4. The other handler (`0x0209A228`)
truncates field 8 to five bits; no unmasked read of `+4` bits 20 and up
exists in the ARM9 or the 35 overlays (scan). ALL ability records must be
marked, book techniques included, or the filter would read tree 0.
The handler is emulated on the built ROM and on vanilla
(`scripts/emu_lien_arme.py`, stack filled with garbage). In-game check
pending.

## §100 Spawn modes without code patches (ZER-73)

The encounter files share one structure (`work/zer73/structure.py`): a map
(`0x69` in `encfld`, field 0 of a `0x66` in `encmons`) holds areas (`0x68`);
**an area belongs to one map only** (287 areas, none shared); the leaders of
an `encbtl` area are exactly the field species of the same `encfld` area
(286 / 290); `encmons`, the list of models a map preloads, holds every field
species of its map (208 / 210, as in vanilla).

`--apparitions` picks the mode and sets the low-level options:

| mode | what | code patched |
|---|---|---|
| `aleatoire` | any species at every spawn (the blob, 1.5) | blob, as the app preset |
| `zone` | in each map, each vanilla species becomes one other species, the same everywhere in that map (field, battle leaders and companions, preload) | none |
| `globale` | one permutation for the whole game (1.1) | none |
| `vanilla` | the game's monsters | none |

Without the blob nothing loads a model on demand: a map preloads its list
into a heap of fixed size. `zone` refuses any draw whose model weight exceeds
the map's vanilla weight (40 draws, then a size-matched fallback): 0 maps over
on seed 5. A free global permutation puts maps up to +97 KB over (10 seeds);
vanilla leaves 36 to 99 KB of the model heap unused at each mount (the
remainder `--place` gives back), so `globale` permutes inside bands of model
size, as wide as possible, until no map is more than 32 KB over (seed 5:
4 bands, +32 KB). Checked per map by `rencontres_zone.mesurer`: the mapping
is a function and injective in `zone` and `globale`. In-game check pending:
stability compared with the blob (the player's hypothesis: fewer crashes).
