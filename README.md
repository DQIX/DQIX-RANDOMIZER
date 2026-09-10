# Dragon Quest IX Randomizer

Version 1.0

This project randomizes the field encounters in **Dragon Quest IX: Sentinels of the Starry Skies**.

Each field monster is replaced with another monster chosen from the game's 256 field monsters. The overworld symbol and model are also changed to match the randomized monster.

Bosses are excluded from randomization. Monster stats, items, spells, and equipment are unchanged. Scripted story battles are also unchanged.

The randomizer does **not** rebalance the game's difficulty. Some randomized encounters may be significantly stronger or weaker than the original encounter.

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
* `DQIX-Randomizer-v1.1.xdelta`

Then open PowerShell in that directory and run `.\xdelta3.exe`.

### 3. Apply the patch

Download the patch:

`patch/DQIX-Randomizer-v1.1.xdelta`

#### Linux / macOS

```bash
xdelta3 -d -s "Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds" "DQIX-Randomizer-v1.1.xdelta" "DQIX Randomizer.nds"
```

#### Windows PowerShell

If `xdelta3.exe`, the ROM and the patch are all in the same directory:

```powershell
.\xdelta3.exe -d -f -s ".\Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds" ".\DQIX-Randomizer-v1.1.xdelta" ".\DQIX Randomizer.nds"
```

The ROM filename can be different. Replace the filename in the command with the actual name of your ROM.

The `-f` option allows the output file to be overwritten if it already exists.

The resulting file should be:

`DQIX Randomizer.nds`

The expected output size is:

`268,435,456 bytes`

The expected MD5 hash of the patched ROM is:

`13a9bf614263eaabbec58d80b0b45282`

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
python randomizer.py
```

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
| The output ROM has the wrong size | Make sure you are using the correct European ROM and the correct `DQIX-Randomizer-v1.1.xdelta` patch.                                      |

If the ROM does not match the fingerprints listed above, do not continue. The patch is designed specifically for that ROM revision.

## Known issues

* **European multilingual release only.** The patch targets the European `(En,Fr,De,Es,It)` release. Other regions have different addresses; the patch refuses to apply to them.
* If more than 6–7 monsters are visible on screen at once, the game may borrow models from other monsters.
* Large monster models are more likely to cause visual/model issues.
* The randomizer has only been tested from a fresh game start.
* Some randomized encounters can be considerably stronger or weaker than the original encounters because the game is not rebalanced.

## Disclaimer

This project does not distribute any copyrighted game ROM or other copyrighted game assets.

You must provide your own legally obtained copy of **Dragon Quest IX: Sentinels of the Starry Skies**.

The patch is provided as-is. Use it at your own risk.
