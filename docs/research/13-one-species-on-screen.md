# 13. One species at a time on screen (§85)

Back to the [index](README.md).

## 85. Never the same species twice on screen

**The rule, the player's (ZER-42, 24 September 2026):** a real randomizer shows
a different monster every time, even when you stay in the same area. When the draw
picks a species that a live monster on the map already has, draw again. It is not
an option: it applies whenever field monsters are randomized.

### Where a field species is drawn

`ChooseFieldMonsterId` (`0x02073FEC`, rewritten by `patch_amorce` as a two-instruction
jump into the draw graft A2 in *return* mode) has exactly **two callers**
(§19, found by scanning every `BL` in the ARM9 and the 35 overlays):

| site | module | what follows |
|---|---|---|
| `0x02073CA0` | ARM9, field tick | `mov r5, r0`, then **one** spawn: `bl 0x021A2128` at `0x02073D3C` with `r2 = r5` |
| `0x021A24CC` | overlay 17 | fallback, only when the caller passed no species (`r4 < 0`) |

Every drawn species therefore becomes exactly one spawn. Both sites hold
`bl 0x02073FEC` in the vanilla ROM and in every ROM built up to 1.5 (checked on
`dq9_15_eq_fix2.nds`).

### The graft

`tirage_unique`, in the blob (`scripts/patch_blob.py`), sits on both `bl`s. Like
the other blob sites, the blob installs it when a field map is set up and removes it
at teardown (§75.4), so towns and battles still run the plain drawer.

```
tirage_unique(r0 = group):          same contract as the drawer
    repeat up to 8 times:
        r0 = ChooseFieldMonsterId(group)
        if r0 < 0: return r0         nothing to draw, unchanged
        if no live actor has species r0: return r0
    return the last draw             a duplicate beats a refused spawn
```

Live actors use the predicate of §82: `variant = [0x020FDD46] & 3`, twelve entries
from `0x70 + 12 * variant` in the slot table `0x020F33E0`, non-null with a
non-negative short at `+2`, which is the species. A dead entry is negative, so it
never matches.

Eight tries is plenty: at most 12 live actors among 256 drawable species gives
less than one chance in 10^10 that all eight draws are duplicates.

The ARM9 site sits in none of the blob's existing cache ranges, so the installer
and the uninstaller now flush and invalidate `0x02073CA0` (32 bytes) as well. Without
that, the CPU would keep executing the old `bl` from its cache (§72, and the ZER-37
trap).

### What it costs, and what is checked

- Blob: +232 bytes, 6,448 to 6,680 without `--boss`, 6,488 to 6,720 with the
  lair pool. The
  ceiling is 8,192 bytes, set by the bootstrap's allocation (§82).
- 16 runtime sites, 17 with `--boss`; the site table holds 17 plus the terminator.
- The build refuses a ROM whose two sites do not hold `bl 0x02073FEC`.
- `scripts/matrice_essais.py`, control `tirage_unique`: the blob's table contains
  both sites, with their original word, and both point to the same function.
- `scripts/diff_roms.py` against the 1.3 release: arm9 and overlays unchanged, only
  `dwc/dq9rand.bin` differs.

**Not yet measured in game** (the player is away): the probe is `scripts/lua/hud.lua`
on a field map, after a cold boot, because the blob changed size and older
savestates no longer match the ROM (§82). Tracked in ZER-44.

This rule controls the **species**. It does not stop two monsters from **looking**
the same: if a model cannot be loaded, the monster borrows the model of another one
already in memory (§70).

## 86. The model before the spawn: no monster without its own model

### Measured: the "double" was a borrowed look, and why it happened

On the player's savestate (`plaine_test15_equilibre_doublon_invisible.State`,
probe `scripts/lua/instantane.lua`), the second "king metal slime" was a
**laidy (331) wearing the king metal slime's model (181)**, stable for three
minutes: no load in progress, laidy simply had no model.

`scripts/lua/trace_gel.lua`, walking left, now logs the live actors at each
spawn. At frame 376: seven live actors, seven distinct species; every one of
the six loaded models is displayed by a live actor, so eviction has no victim;
the load of species 220 ends in `ECHEC allocation du modele (tas plein)` and
220 borrows too. This is a direct consequence of §85: before it, two monsters
of the same species shared one model; now every live monster needs its own.

### The rule (the player's choice, 24 September)

Of three options — let the monster borrow, allow a duplicate species, or do not
spawn it — the player chose: **a monster whose model cannot be loaded does not
appear**; it will appear once another one has freed its place.

### The graft

`tirage_unique` now ends with `modele_pret(species)`:

```
modele_pret(s):
    if FindLoadedModel(s): return 1           0x021A2738 ignores its first argument
    if PLEIN and no evictable slot and loaded count >= PLEIN: return 0
    declencheur(s)                            synchronous for the caller
    if FindLoadedModel(s): return 1
    PLEIN = max(loaded count, 1); return 0
```

and the drawer returns **-1** when it gets 0, or after eight duplicate draws in a
row. Both callers already treat -1 as "nothing to draw" (vanilla): the field
tick (`cmp r5, #-1` at `0x02073CAC`) skips the spawn without resetting its timer
and retries on the next frame; the fallback (`movs r4, r0 ; bmi` at
`0x021A24D0`) returns 0 like its other failures.

`declencheur` is synchronous for its caller: the preloader reads the file over
two or three frames while other threads run, then returns (trace: spawn at frame
188, model stored at 191, found on return). `emprunt` then finds the model at its
first tier.

**PLEIN** (blob word `mots + 36`, reset by `greffe_a` at every setup) stops the
tick from paying a file read on every frame while the heap is full: after a
failure, a new load is only tried when a model can be evicted or fewer models
are loaded than at the failure.

Blob: 6,680 to 6,956 bytes (ceiling 8,192). `diff_roms.py` against the player's
test ROM: only `dwc/dq9rand.bin` differs, the draw is unchanged.

### Measured in game

Player's save, cold boot, Teleport to Ablithia, then a walk loop with battles won
automatically (`instantane.lua`, 60 readings over 3 minutes, 30 spawns, 3
battles): **no borrowed and no invisible model outside battle**. But only **3 to
5 monsters** on screen, against 7 (two of them borrowed) before.

### Why so few: fragmentation, not size

Same run, reading the model heap's free list (ExpHeap: head at `+0x24`, block
size at `+0x04`, next at `+0x0C`):

| reading | models loaded | free | blocks | largest |
|---|---|---|---|---|
| t022 | 1 | 116,112 | 1 | 116,112 |
| t026 | 5 | 32,948 | 3 | 13,416 |
| t028 | 3 | 73,076 | 6 | 18,264 |

At t028 there is room for three or four more models, but no hole larger than
18,264 bytes, and the median field model is 18,320 (5,508 to 61,368, §37).
Loading and evicting models of different sizes cuts the heap into holes. Version
1.1 never hit this: eight species per area were preloaded once and shared, so
nothing was ever evicted.

A size-aware draw (pick a species whose model fits the largest hole) would give
back the density, but it favours small monsters whenever the heap is full.
**Refused by the player**: every monster must have the same chance.
