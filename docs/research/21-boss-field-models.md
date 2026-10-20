# 21. Boss field models

## 104. Which bosses have a field model (ZER-83, 19 October 2026)

**The question.** With `--boss-terrain`, a boss roaming the map has no walking
animation. A community player (KnightWatch, 17 October) suggested borrowing the
animation of an ordinary monster that uses the same model in another colour.

### 104.1 Two files per model: battle and field

`data/pack_lv5/enemy.gp2` (601 `.mon` members) holds, for each model code of
`mon_data_<lg>.nat` (§14), a battle file `<code>.mon` and, **only for models
that appear on the map**, a field file `<code>_f.mon`:

| model | battle | field |
|---|---|---|
| `b003a` Hexagoon (Hexacorne) | `b003a.mon`, 30,008 B | **none** |
| `b003b` octagoon (octocorne), ordinary | `b003b.mon`, 38,500 B | `b003b_f.mon`, 16,440 B |
| `z034a/b/c` cyclops, giant, Atlas | one each | one each (~15.8 KB) |

The letter suffix is the colour variant of one mesh (`b003a`/`b003b`,
`z034a`/`b`/`c`). Listing: `python scripts/gp2.py work/extracted/data/pack_lv5/enemy.gp2`.

### 104.2 The census, over the 89 boss species of `categories_boss`

54 distinct boss model codes:

| case | count | models |
|---|---|---|
| own `_f.mon` | 32 | the 13 legacy bosses and the two claws, the 5 grotto bosses (`z034c` Atlas, `z075a`, `z076a`, `z080c`, `z081c`), `b004b`, `b007b`, `b012c`, `b013b`, `b015a`, `b016a/b`, `b017b`, `b018a/b`, `b019a`, `b021b` |
| no `_f.mon`, but a colour variant has one | 14 | `b003a` (→`b003b`), `b004a`, `b005a`, `b006a`, `b007a`, `b007c`, `b008a`, `b010a`, `b012a`, `b013a`, `b014a`, `b017a`, `b019b`, `b021a` |
| neither | 8 | `b009a` Garth Goyle, `b011a` Grand Lizzier, `b020a` King Godwyn (2nd form), `b022a` and `b023a` Corvus, `b024a` Nodoph, `b025a` Rover, `b300a` Aquila |

Only 14 of the 89 species share a model root with one of the 256 ordinary
monsters. The other variants with a field file are bosses themselves (grotto
bosses that roam their lair, story bosses seen walking in cutscenes).

### 104.3 Seen in play: the field model is there, the behaviour is not

Test ROM v17h (19 October): `--boss-terrain` with **only bosses** in the field
draw (`DQ9_TERRAIN_BOSS_SEULS=1`, development switch in `construire_bitmap`).
The 16 drawable bosses all have their own `_f.mon` except King Godfrey
(`b019b`). The player: they stand still, **with their idle animation**, but do
not move and do not react to the player.

So the field model and its idle animation load fine: what is missing is
**movement and behaviour**. Borrowing a colour variant's `_f.mon` (104.2)
would not be enough on its own. Next lead: the species' field record (§78,
`fld_mondata.bin`) and the behaviour node the blob builds per species at mount
time (`patch_hasard.especes_tirables`); compare a boss with its ordinary
variant (`b003a`/`b003b`, `z034c` Atlas / `z034a` cyclops).

### 104.4 What this does not say yet
- What the loader takes for a boss without a field file (the battle file, or
  nothing).
- The exact layout of a `.mon`. First look: every `.mon` is a **NARC**
  (`4E 41 52 43`, 3 sections), raw inside `enemy.gp2` (its "type 6" is the first
  word of the data, not a compression), with Nitro members, some of them
  LZ-compressed. A field file carries an animation (`BCA0`), a model (`MDL0`)
  and textures (`TEX0`): `z034a_f.mon` and `z034c_f.mon` (cyclops, Atlas)
  have the same 15.8 KB layout, signatures at the same offsets. So the
  plan for the 14 is: build `<code>_f.mon` as a copy of the variant's field
  file with the boss's own textures, taken from its battle file. It still
  needs the NARC members decoded, and it adds 14 members to `enemy.gp2`, which
  changes the file layout and invalidates savestates.

Script: the census was a one-off scratch script (`monnames.charger` +
`montable.ids_par_index` + the member list of `enemy.gp2`).

### 104.5 Movement and behaviour come from `fld_mondata.bin` (20 October)

The field `.bact` of a boss is byte-identical to its ordinary variant's
(`z034c`/`z034a`, `z080c`/`a`, `z081c`/`a`, `z075a`/`b`, `z076a`/`b`): the
walk animation is there. What differs is the field record (§78.4): the 16
field-drawable bosses have **field 2 = 0** and the **low 16 bits of field 3
= 0** (11 of them have field 3 = 0 entirely), the setting of a standing
grotto symbol. Ordinary monsters: field 2 = 99 for 185 of 256, field 3 =
`003cXXXX` for 237.

The **high half of field 3** decides chasing: `0x3c` on chasers, `0` on
monsters that roam without chasing (abyssaure `00000209`, scarlatin
`00001712`, laidy `00000309`). Test ROM v17u gave each boss fields 2 and 3
of an ordinary monster: most moved and chased, Mac Leo (donor abyssaure)
stayed in place. v17v, chaser donors only: all move and chase (player,
20 October). Built into `--boss-terrain` (`patch_blob.donneurs_comportement`):
same-model ordinary first, else the chaser with the nearest model size.

Census of the 148 boss entries (legacy levels included): 19 with their own
`_f.mon` and id < 384 (16 drawable), 93 with their own `_f.mon` but id >= 384
(the blob bitmap stops at 384), 22 with only a colour variant's `_f.mon`, 14
with none. The player keeps the 16 for now.
