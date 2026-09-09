# Dragon Quest IX Randomizer

**Version 1.1** — every monster you meet in the field is drawn at random from the
whole bestiary, and it really is the monster you see.

Dragon Quest IX only keeps a handful of monster models in memory at a time, and
it decides which ones when a map loads. That is why a naive encounter randomizer
either shows you the wrong sprite or crashes. This patch rewrites the loading
path so that a species can be drawn from all **256 field monsters** at any
moment, loaded on demand, evicted when nothing is using it, and given its real
behaviour parameters — so it moves, chases and flees the way that species
should.

## What it changes

- **Field encounters.** Any of the 256 bestiary monsters can appear anywhere.
  The draw is uniform: no species is rarer than another.
- **The model matches the monster.** The symbol you see on the map is the
  species you will actually fight, whatever it is.
- **Bosses stay bosses.** The bestiary numbers its monsters 1 to 256 and puts
  bosses beyond that; everything past 256 is excluded, including the seventeen
  bosses that roam as grotto symbols in the unmodified game.

Statistics, items, spells and equipment are untouched. This release randomizes
encounters only. Scripted story battles keep their own pool, difficulty is not
rebalanced, and the game can be finished normally.

---

## Installing

### 1. Check your ROM

The patch only works on the **European** release, and it will refuse anything
else rather than produce a broken game.

| | |
|---|---|
| Serial | `YDQP` |
| CRC32 | `FE8EC0E8` |
| MD5 | `3a63438fff7db282fa3133e8fd020e85` |
| Size | 268,435,456 bytes |

```bash
# Linux / macOS
md5sum "Dragon Quest IX ... .nds"       # or md5 -q on macOS
```
```powershell
# Windows
Get-FileHash -Algorithm MD5 "Dragon Quest IX ... .nds"
```

No ROM is distributed here — use your own copy of the game.

### 2. Get xdelta3

| Platform | |
|---|---|
| Windows | `scoop install xdelta` or `winget install xdelta3`, or the binary from [the releases page](https://github.com/jmacd/xdelta-gpl/releases) |
| macOS | `brew install xdelta` |
| Debian / Ubuntu | `sudo apt install xdelta3` |
| Arch | `sudo pacman -S xdelta3` |

If you would rather not touch a terminal, [Delta Patcher](https://github.com/marco-calautti/DeltaPatcher/releases)
is a graphical front end for the same format: pick the ROM as *original file*,
the `.xdelta` as *patch*, press *Apply patch*.

### 3. Apply the patch

Download `patch/DQIX-Randomizer-v1.1.xdelta` from this repository, put it next
to your ROM, and run:

```bash
xdelta3 -d -s "Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds" \
            DQIX-Randomizer-v1.1.xdelta \
            "DQIX Randomizer.nds"
```

On Windows, the same on one line:

```powershell
xdelta3 -d -s "Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds" DQIX-Randomizer-v1.1.xdelta "DQIX Randomizer.nds"
```

The patch carries only the differences, so it needs your ROM to produce
anything. The result should be 268,435,456 bytes with MD5
`13a9bf614263eaabbec58d80b0b45282`.

**If it fails:**

| Message | Cause |
|---|---|
| `XD3_INVALID_INPUT` | wrong ROM — check the fingerprints above; the American and Japanese releases will not work |
| `xdelta3: not found` | step 2 was skipped, or the terminal was opened before installing |
| `No such file or directory` | the ROM filename does not match exactly; quote it, spaces and parentheses included |

### 4. Play

Open `DQIX Randomizer.nds` in a DS emulator and **start a new game**. Developed
and tested on melonDS (through BizHawk). Save files from an unmodified game are
not supported, and real hardware and flashcarts are untested.

---

## Known issues

This is an early release. What is known:

- **A model can be borrowed.** The model heap holds six or seven monsters at a
  time. If more than that are alive on screen at once, the next one to appear
  may wear the appearance of another loaded monster. It is still the right
  monster in battle.
- **Large monsters make that more likely.** The heaviest models are around
  42 KB; several of them together is the situation most likely to fall back to
  a borrowed appearance.
- **European release only.** Other regions have different addresses; the patch
  refuses to apply to them.
- **Only tested from a fresh start.**

If you hit a freeze, a black screen, or a monster that does not move, please
open an issue and say where it happened and what was on screen. A savestate
taken at the moment it breaks is worth more than any description.

## Building it yourself

`randomizer.py` produces the patched ROM from an unmodified one:

```bash
python randomizer.py "Dragon Quest IX ... .nds" \
    --seed 1 --sans-rotation --place --blob --plafond 1 --garde 138240 \
    -o "DQIX Randomizer.nds"
```

`--seed` picks the permutation; change it for a different game. The remaining
flags select the on-demand loader, which is what makes the full bestiary
reachable. Requires Python 3 with `ndspy`, `keystone-engine` and `capstone`.

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
