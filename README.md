# Dragon Quest IX Randomizer

Version 1.7

A randomizer for **Dragon Quest IX: Sentinels of the Starry Skies** (Nintendo DS).
Drop your ROM on the application, pick what to shuffle, and play a new game:
other monsters, other bosses, other loot, other shops, other spells.

**Demo video:** https://www.youtube.com/watch?v=1gUc4pJak4o

## Quick start

1. **Get the right ROM.** Only the **European multilingual** release works
   (English, French, German, Spanish and Italian are all inside):
   `Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds`,
   MD5 `3a63438fff7db282fa3133e8fd020e85`. The file name does not matter; the
   application checks the contents and refuses anything else. No ROM is
   distributed here: use your own copy.
2. **Run the application.** Download `DQIX-Randomizer.exe` from the
   **[latest release](https://github.com/DQIX/DQIX-RANDOMIZER/releases/latest)**
   and double-click it. Nothing to install. Drop your ROM on the window, choose
   a preset, click **Randomize**. About 25 seconds later,
   `DQIX-Randomizer-seed<seed>.nds` is written next to your ROM, in a folder
   of the same name.
3. **Play** that file in an emulator, from a **new game**. Tested with melonDS
   (through BizHawk) and DeSmuME; with DeSmuME, turn off the Dynamic
   Recompiler.

The same seed with the same options always gives the same game: share the seed
and the options, and a friend plays exactly your run.

## What can be randomized

The window has four tabs of options, plus **Create your ROM** (below). Every
option is a checkbox; the two presets tick a sensible set for you.

**Monsters**
* **Field monsters**, in one of three modes:
  * *random at every spawn*: any of the 256 bestiary monsters each time a
    monster appears, never the same one twice on screen at once;
  * *1-to-1 per area*: in each area, a monster is always replaced by the same
    other one;
  * *1-to-1 for the whole game*: a monster is replaced by the same other one
    everywhere.

  The two 1-to-1 modes change only the game's data, not its code.
* Monsters come in **groups**, as in the original game.
* **Monster spells and abilities** (experimental): in every battle, monsters
  draw new spells and abilities, abilities shown with their real animation.
* **Monster stats** (experimental).

**Bosses**
* **Story bosses**: every scripted boss fight is against another boss. Options:
  keep the first boss (Hexagoon, fought alone); story, grotto and legacy bosses
  as often as each other; story bosses only; bosses *or* ordinary monsters; a
  new boss at every attempt. Legacy bosses come at their first level only, so
  they do not crowd out the others; an option brings back all three levels.
  Two lists choose from which story boss on grotto bosses and legacy bosses
  can turn up in story fights (from the start, from a given boss, or never).
  The battle music follows the boss you get.
* **Bosses on the field** (experimental): some bosses wander the map and
  chase you.

**Items & shops**
* **Chests (grotto chests included), pots, barrels, cupboards and monster
  drops** can hold any of the game's regular items, and every one of them can
  be found. Gold amounts are redrawn too. By default any item can come from
  any container; untick *rare items everywhere* to make rarity follow the
  container's rank, and tick *balance equipment and consumables* for about a
  third of herbs, potions and seeds.
* **New drops every battle**: what a monster drops is drawn again each time.
  The bestiary shows the drops of your ROM.
* **Shops** sell a new stock, fixed for the whole run. The flowing dress, the
  watermaul wand and the silver shield stay in their original shops, at their
  original price: a post-game quest asks for them.
* **Alchemy ingredients**: every Krak Pot recipe makes the same item from
  other ingredients, in the same quantities (in both presets).
* **Cap'n Max Meddlin's rewards** (in both presets): his ten milestones and his shop
  give other items, and need a quarter of the mini medals, since medals are
  rare once the loot is randomized.

**Party**
* **Spells** each vocation learns as it levels up.
* **Skill trees**: what each skill-point milestone gives, abilities and stat
  bonuses alike, within each tree or across all of them. Optionally, a weapon
  technique keeps needing its original weapon.
* **Vocations**: all twelve open at the abbey from the start, random vocation
  for recruits and for the hero, or (as a challenge) vocations locked.

**Create your ROM**
* Decide every case yourself: each boss fight, each shop's stock, chests,
  pots and grottos, alchemy, Cap'n Max Meddlin', skill trees, vocation
  spells, vocations, field monsters per area or for the whole game, battle
  drops, and each monster's six actions (fixed, or a spell or ability drawn
  at every battle, from a pool you choose).
* Start from the original game, from your options or from a file; re-roll
  one category; a case you change by hand stays pinned. Save it all in a
  file to share: the same file always gives the same ROM.
* Anything goes, even unbalanced. Only what would make the game
  unfinishable is locked, and the locks can be lifted.
* The button follows the tab you are on: from **Create your ROM** it builds
  your custom ROM (the options of the other tabs do not count); from the
  other tabs, it uses their options.

How it works, for players: [monsters](docs/guide/MONSTERS.md) -
[loot](docs/guide/LOOT.md) - [shops](docs/guide/SHOPS.md) -
[spells and abilities](docs/guide/SPELLS.md) -
[where every chest is](docs/guide/loot/containers_by_rank.md)

## The two presets

| | **Balanced** | **Total chaos** |
|---|---|---|
| Loot | anything anywhere, legendary gear in the first barrel (since 1.7, in both presets) | same |
| Shops | each shop keeps its specialty and its price range | anything in any shop, at any price |
| Spells and skills | weak spells early, strong ones late; skills stay in their tree | no order; skills move between trees |
| Bosses | untouched | every boss fight against another boss |
| Alchemy | new ingredients for every recipe, same quantities | same |
| Cap'n Max Meddlin' | rewards within one star of the original, a quarter of the medals | any item, a quarter of the medals |

"Balanced" is still a randomizer, and it is still hard: the game's difficulty
is not rebalanced.

## What never changes

* **Key items** and the items the story needs (the dragon warrior equipment,
  Sterling's whistle): never handed out by chests, drops or shops.
* The **chronocrystal shop**, and the **prologue** fight.
* Four- and five-star items are only sold in Dourbridge's secret shop and the
  two Stornway stalls that open after the final boss, in every mode.

## Troubleshooting

| Problem | Solution |
| --- | --- |
| "Not the supported ROM" | Only the European release above works. |
| "Windows protected your PC" | The application is not code-signed: *More info*, then *Run anyway*, or build it yourself. |
| Your antivirus quarantines the .exe | A known false positive with packaged Python programs. Building it yourself avoids it. |
| Crash on DeSmuME | Turn off the Dynamic Recompiler. |

## Known issues

* Tested from a fresh game start only, and on emulators only.
* In *random at every spawn* mode, when the model memory is full, a new monster
  waits until another one leaves before it appears.
* An emulator savestate only works with the exact ROM it was made on.

## Building from source

```bash
pip install ndspy keystone-engine capstone
python interface.py                      # the window
python randomizer.py --help              # every command-line option
pip install pyinstaller tkinterdnd2
python scripts/build_exe.py              # writes dist/DQIX-Randomizer.exe
```

## Sources

- [ArchipelagoDQIX](https://github.com/kid2407/ArchipelagoDQIX/tree/main) by kid2407
- [dqix-decomp](https://github.com/ZevyaDev/dqix-decomp/tree/naming-pass) by ZevyaDev
- *Guide to RNG systems in DQIX for game manipulation* by hurblub
- The research notes behind every change: [docs/research](docs/research/README.md)

## Disclaimer

This project does not distribute any copyrighted game ROM or other copyrighted
game assets. You must provide your own legally obtained copy of **Dragon Quest
IX: Sentinels of the Starry Skies**. The randomizer is provided as-is; use it
at your own risk.
