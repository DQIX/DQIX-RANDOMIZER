# Dragon Quest IX Randomizer

Version 1.2

This project randomizes **Dragon Quest IX: Sentinels of the Starry Skies**:

* **Field monsters.** Each field monster is replaced with another monster chosen from the game's 256 field monsters. The overworld symbol and model match the randomized monster. Bosses and scripted story battles are unchanged.
* **Loot** (new in 1.2). Blue chests, pots, barrels, cupboards, red chests and monster drops can give any of the game's 1,090 regular items, weapons and armour included. Rarer items come from rarer places: five-star legendary equipment only from the highest-rank chests, the rarest drops and red chests. Every one of the 1,090 items can be obtained. Key items are never moved, and the Magic Key and Ultimate Key stay where they are.

Monster stats, spells, shops, quest rewards and treasure-map grottos are unchanged.

**How it works, explained for players:** [monsters](docs/guide/MONSTERS.md) · [loot, ranks and rarity](docs/guide/LOOT.md) · [where every chest is](docs/guide/loot/containers_by_rank.md)

The randomizer does **not** rebalance the game's difficulty. Some randomized encounters may be significantly stronger or weaker than the original encounter.

**Demo video** : https://www.youtube.com/watch?v=1gUc4pJak4o

**How to install video** : https://www.youtube.com/watch?v=Qsf332pc45g

## Installation

### 1. Check your ROM

The patch only works on the **European multilingual** release, and it will refuse anything else rather than produce a broken game.

The required ROM is:

`Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds`

You do **not** need an English-only ROM. The English, French, German, Spanish and Italian languages are all included in this single European ROM.

The ROM filename does not need to match the name above. The patch checks the ROM contents, not its filename.

The ROM must have the following fingerprints:

* **Serial:** `YDQP`
* **CRC32:** `FE8EC0E8`
* **MD5:** `3a63438fff7db282fa3133e8fd020e85`
* **Size:** `268,435,456 bytes`

You can check the MD5 hash of your ROM with:

```bash
# Linux / macOS
md5sum "Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds"
```

On macOS, you can also use:

```bash
md5 -q "Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds"
```

On Windows PowerShell:

```powershell
Get-FileHash -Algorithm MD5 "Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds"
```

The expected MD5 is:

`3a63438fff7db282fa3133e8fd020e85`

No ROM is distributed here — use your own copy of the game.

### 2. Get xdelta3

You need `xdelta3` to apply the patch.

| Platform | Installation                                                                                                                                                   |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Linux    | Install `xdelta3` using your distribution's package manager                                                                                                    |
| macOS    | Install `xdelta3` using Homebrew                                                                                                                               |
| Windows  | Download the `xdelta3.exe` Windows binary from the [xdelta releases](https://github.com/jmacd/xdelta/releases) or the [xdelta-gpl releases](https://github.com/jmacd/xdelta-gpl/releases), or install it with Scoop/WinGet if available |

On Windows, you do not need to install xdelta3 system-wide.

You can simply put `xdelta3.exe` in the same directory as:

* your Dragon Quest IX ROM
* `DQIX-Randomizer-v1.2.xdelta`

Then open PowerShell in that directory and run `.\xdelta3.exe`.

### 3. Apply the patch

Download the patch from the
**[latest release](https://github.com/DQIX/DQIX-RANDOMIZER/releases/latest)**:

`DQIX-Randomizer-v1.2.xdelta`

A copy is also kept in this repository at `patch/DQIX-Randomizer-v1.2.xdelta`, but
the release page is the place to get it: that is where every version stays
available, with its checksums.

#### Linux / macOS

```bash
xdelta3 -d -s "Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds" "DQIX-Randomizer-v1.2.xdelta" "DQIX Randomizer.nds"
```

#### Windows PowerShell

If `xdelta3.exe`, the ROM and the patch are all in the same directory:

```powershell
.\xdelta3.exe -d -f -s ".\Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds" ".\DQIX-Randomizer-v1.2.xdelta" ".\DQIX Randomizer.nds"
```

The ROM filename can be different. Replace the filename in the command with the actual name of your ROM.

The `-f` option allows the output file to be overwritten if it already exists.

The resulting file should be:

`DQIX Randomizer.nds`

The expected output size is:

`268,435,456 bytes`

The expected MD5 hash of the patched ROM is:

`8df5d3ff03b2575c47e3962f6a579717`

On Windows, you can verify it with:

```powershell
Get-FileHash -Algorithm MD5 ".\DQIX Randomizer.nds"
```

On Linux / macOS:

```bash
md5sum "DQIX Randomizer.nds"
```

### 4. Play

Run:

`DQIX Randomizer.nds`

in your Nintendo DS emulator. ⚠️ If you want to use DeSmuME for its HD rendering, just disable the Dynamic Recompiler to test. You may get a crash if this option is on — if it disappears after deactivating it, that will pretty much confirm the cause.

Start a **new game**.

The randomization is applied when the patch is created, so every patched ROM can contain a different set of randomized encounters.

The randomizer has been tested with **melonDS through BizHawk**. and **desmume**

Unmodified save files are not supported.

The randomizer has not been tested on real Nintendo DS hardware or flashcarts.

## Building

If you want to build the randomizer yourself, you need:

* Python 3
* `ndspy`
* `keystone-engine`
* `capstone`

Install the Python dependencies with:

```bash
pip install ndspy keystone-engine capstone
```

Then run:

```bash
python randomizer.py "<your European ROM>.nds" --seed 1 --sans-rotation --place --blob --plafond 1 --garde 163840 -o "DQIX Randomizer.nds"
```

This rebuilds the released ROM byte for byte (MD5 `8df5d3ff03b2575c47e3962f6a579717`). Change `--seed` for a different randomization. Loot randomization is on by default; add `--sans-objets` to randomize the monsters only, as in version 1.1.

See the available command-line options with:

```bash
python randomizer.py --help
```

## Troubleshooting

| Error                             | Solution                                                                                                                                   |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `XD3_INVALID_INPUT`               | Wrong ROM or corrupted patch — check the fingerprints above. The American and Japanese releases will not work.                             |
| `xdelta3: not found`              | xdelta3 is not installed or is not in your `PATH`. On Windows, if `xdelta3.exe` is in the current directory, use `.\xdelta3.exe`.          |
| `No such file or directory`       | A file or directory specified in the command cannot be found. Check the current directory and all filenames.                               |
| The command appears to hang       | Make sure you are using a compatible xdelta3 binary and that the ROM and patch are accessible. The patch should normally complete quickly. |
| The output ROM has the wrong size | Make sure you are using the correct European ROM and the correct `DQIX-Randomizer-v1.2.xdelta` patch.                                      |

If the ROM does not match the fingerprints listed above, do not continue. The patch is designed specifically for that ROM revision.

## Known issues

* **European multilingual release only.** The patch targets the European `(En,Fr,De,Es,It)` release. Other regions have different addresses; the patch refuses to apply to them.
* If several monsters are visible on screen at once, the game may still borrow a model from another monster: measured at about 1 appearance in 80.
* Large monster models are more likely to cause visual/model issues.
* The randomizer has only been tested from a fresh game start.
* Blue chests, pots, barrels and cupboards get their content when you enter a room, like in the original game. In a room with no monsters around, leaving and coming back quickly can give the same content again: the game's random number generator only moves when something happens (monsters, walking NPCs, battles).
* Emulator savestates only work with the exact ROM they were made on. A savestate from an older patched ROM can show item messages without the item name.
* Some randomized encounters can be considerably stronger or weaker than the original encounters because the game is not rebalanced.

## Release files

Each release also attaches spreadsheets for its patch (`;` separated, open in Excel): `items.csv` (every item, its rarity and how many places give it), `item_sources.csv` (every place each item comes from), `containers.csv` and `vanilla_containers.csv` (every container of the game, randomized and original).

## Sources

This project was made possible thanks to the following resources:

- [ArchipelagoDQIX](https://github.com/kid2407/ArchipelagoDQIX/tree/main) by kid2407
- [dqix-decomp](https://github.com/ZevyaDev/dqix-decomp/tree/naming-pass) by ZevyaDev
- *Guide to RNG systems in DQIX for game manipulation* by hurblub

## Disclaimer

This project does not distribute any copyrighted game ROM or other copyrighted game assets.

You must provide your own legally obtained copy of **Dragon Quest IX: Sentinels of the Starry Skies**.

The patch is provided as-is. Use it at your own risk.
