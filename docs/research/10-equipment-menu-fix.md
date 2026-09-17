# 10. The equipment menu wipes the loaded models (§82)

Part of the [research notes](README.md). Sections keep their original numbers.

## 82. Live monsters lose their model when the field context is rebuilt

Reported by the player on 1.2: with monsters around, opening the menu, entering
**Equip** and leaving it makes every monster on the map invisible and
unfightable — their `!` notice still shows, but no battle starts. Reloading the
zone fixes it.

### What the equipment screen does

It **tears down the field context and rebuilds it on exit** — it needs the memory
to display the character in 3D. Measured with `scripts/lua/menu_equipement.lua` on
the player's savestate, counting the calls at `0x021A2FA0` (setup),
`0x021A316C` (teardown), `0x021A28A8` (preloader) and the bootstrap:

```
on leaving Equip : teardown=3  setup=1  preloader=2  bootstrap=1
```

The monsters already on the map are **not** removed by that, so the actor slots
keep their species.

### Why our build broke and vanilla does not

Vanilla's setup reloads the map's preload list, so `0x021A2B1C` — called on
preloader exit — reattaches the models to the actors that are still alive.

Our preloader loads `BORNE` species instead (one in the shipped build, §70), drawn
fresh. The live actors' species are not among them, so `FindLoadedModel` returns 0
for each of them: the actor exists with no model attached (§36), which is exactly
invisible and, having no model, nothing to collide with.

| | models loaded | live actors |
|---|---|---|
| before the menu | 10, 41 | 10, 41 |
| after, on 1.2 | **328** | 10, 41, 163 |

### The fix: the preloader serves the live actors first

Two grafts change, both in the blob:

- **`greffe_e`** (the `GetSpecies` site, `0x021A2974`) returns, in normal mode, the
  species of the i-th live actor for the first indices, then falls back to the
  map's list with the index reduced by the number of actors served — so the list is
  never read past its own count.
- **`greffe_borne`** (the shared count site, §71 defect 2) adds the number of live
  actors to `min(count, BORNE)`, capped at **6** models. A field model costs about
  21 KB and the reserve is 160 KB.

Live actors are enumerated with the predicate of §50: `variant = [0x020FDD46] & 3`,
then twelve entries from `0x70 + 12 * variant` in the slot table; an entry that is
non-null with a positive short at `+2` carries a monster, and that short is its
species.

Measured after the fix, same sequence, teardown and setup confirmed:

| | models loaded | live actors |
|---|---|---|
| before the menu | 170, 182, 85 | 170, 182, 85 |
| after | **170, 182, 85, 165, 201** | 170, 182, 85, 165, 201 |

### The trap this uncovered: the blob has a size ceiling, and a savestate hides it

The fix grows the blob from 5,920 to 6,124 bytes, and the first measurements showed
it not installing at all. Cause, found by dumping the blob from RAM and comparing it
to the file in the ROM: **identical up to 0x1720 = 5,920 bytes, garbage after** —
the literal pool, so every game address the blob calls.

Two distinct facts, both worth keeping:

- **A savestate freezes the file table.** The state was taken on the previous ROM,
  where `dq9rand.bin` was 5,920 bytes long; the game therefore read only the first
  5,920 bytes of the new, longer file. Same family as §38 and §40: *a savestate is
  only valid for the ROM it was taken on.* The fix had to be validated from a cold
  boot, on a savestate taken on the new ROM.
- **The read buffer bounds the blob.** The reader places the file content inside the
  buffer the bootstrap allocates (§78.6), so the usable size follows
  `TAILLE_TAMPON`. It went from 8 to 12 KiB, taken from the model heap and returned
  with it at teardown. Checked at a cold boot: the 6,124 bytes in RAM match the file
  exactly, apart from the one byte the installer writes itself.
