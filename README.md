# Dragon Quest IX Randomizer

**Version 1.0** — every monster you meet in the field is drawn at random from the
whole bestiary, and it really is the monster you see.

Dragon Quest IX only keeps a handful of monster models in memory at a time, and
it decides which ones when a map loads. That is why a naive encounter randomizer
either shows you the wrong sprite or crashes. This patch rewrites the loading
path so that a species can be drawn from all 253 field monsters at any moment,
loaded on demand, evicted when nothing is using it, and given its real behaviour
parameters — so it moves, chases and flees the way that species should.

## What it changes

- **Field encounters.** Any of the 253 field monsters can appear anywhere. The
  draw is uniform: no species is rarer than another.
- **The model matches the monster.** The symbol you see on the map is the
  species you will actually fight, whatever it is.
- **Bosses stay bosses.** The 256 numbered bestiary entries are the pool;
  everything beyond is excluded, including the seventeen bosses that roam as
  grotto symbols in the unmodified game.

Statistics, items, spells and equipment are untouched. This release randomizes
encounters only.

## What it does not change

Nothing else. Scripted story battles keep their own pool, difficulty is not
rebalanced, and the game can be finished normally.

## Requirements

- A legally obtained copy of the **European** release
  (serial `YDQP`, CRC32 `FE8EC0E8`, MD5 `3a63438fff7db282fa3133e8fd020e85`).
  No ROM is distributed here.
- [`xdelta3`](https://github.com/jmacd/xdelta) to apply the patch.
- Any DS emulator. Developed and tested on melonDS (through BizHawk); real
  hardware and flashcarts are untested.

## Applying the patch

```
xdelta3 -d -s "Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds" \
            DQIX-Randomizer-v1.0.xdelta \
            "Dragon Quest IX - Randomizer.nds"
```

Start a **new game**. Save files from an unmodified game may work but are not
supported, and the patch has only been exercised from a fresh start.

## Known issues

This is a first release. What is known:

- **Behaviour is per species, but only for maps that carry monsters.** Towns,
  buildings and other peaceful maps are deliberately left alone.
- **A handful of models can be borrowed.** The model heap holds six or seven
  monsters at once. If more than that are alive on screen at the same time, the
  next one to appear may wear the appearance of another loaded monster. It is
  still the right monster in battle.
- **Very large monsters.** The heaviest models are around 42 KB; several of
  them appearing together is the situation most likely to fall back to a
  borrowed appearance.
- **Only tested from a fresh start on the European release.** Other regions have
  different addresses and will not work at all — the patcher refuses to apply if
  the ROM is not the expected one.

If you hit a freeze, a black screen, or a monster that does not move, please
open an issue and say where it happened and what was on screen.

## Building it yourself

`randomizer.py` produces the patched ROM from an unmodified one:

```
python randomizer.py "Dragon Quest IX ... .nds" \
    --seed 1 --sans-rotation --place --blob --plafond 1 --garde 138240 \
    -o dq9_randomizer.nds
```

`--seed` picks the permutation. The remaining flags select the on-demand loader,
which is what makes the full bestiary reachable. Requires Python 3, `ndspy`,
`keystone-engine` and `capstone`.

## How it works, in one paragraph

The ARM9 binary has almost no free space, so the randomizer's code lives in a
file added to the ROM's filesystem, read into a heap allocation when a map
mounts, and installed by rewriting fourteen call sites at runtime. It removes
itself when the map is torn down — the memory it lived in is reclaimed, and a
stale pointer there is what a crash looks like. On top of that sit a gate that
accepts any species, an on-demand model loader with eviction, and a graft that
makes the game build the real behaviour record for every drawable species.
`docs/RESEARCH.md` documents the file formats, the addresses and, more usefully,
the measurements and the dead ends.

## Credits

Reverse engineering, patching and documentation done from scratch against the
European release. The `dqix-functions` naming work of the Dragon Quest hacking
community was a helpful cross-check on a few ARM9 symbols.
