# Dragon Quest IX Randomizer

Version 1.5

This project randomizes **Dragon Quest IX: Sentinels of the Starry Skies**:

* **Field monsters.** Each field monster is replaced with another monster chosen from the game's 256 field monsters. The overworld symbol and model match the randomized monster, and the same monster is never on screen twice at once: stay in one field and you keep meeting new ones.
* **Loot.** Blue chests, pots, barrels, cupboards, red chests and monster drops can give any of the game's 1,090 regular items, weapons and armour included. Every one of the 1,090 items can be obtained. Key items are never moved, and the Magic Key and Ultimate Key stay where they are.
* **Shops.** The 37 shops of the game sell a new stock, drawn once when the ROM is built and fixed for the whole playthrough. 1,082 items can appear, against 330 in the original game.
* **Spells.** The spells a vocation learns as it levels up are redrawn from the game's 61 spells. Levels and counts stay as they are: a Priest still learns seventeen spells, at the same seventeen levels, but not the same ones.
* **Monster drops, at every battle.** When a monster drops an item, the item is drawn anew from the 1,088 obtainable items: the same monster can give something different each time.
* **Vocations.** All twelve vocations are available at Alltrades Abbey from the start, and a companion created at Patty's gets a random vocation. The hero can start with a random vocation. As a challenge, vocations can also be locked: nobody can change vocation (revocation stays).
* **Skill tree abilities and their bonuses.** All 286 skill-point milestones of the 26 trees are redealt: the 147 abilities, and the 139 stat bonuses too (Attack +10, Max MP +30, Block Chance +2%, absolute mastery). A milestone that gave an ability can give a bonus, and the other way round.

Monster stats stay as they are unless you tick the experimental option. Quest rewards and treasure-map grottos are not randomized.

**New since 1.3:**

* **An application.** You no longer need xdelta3 or a command line. Drop your ROM on the window, choose what to randomize, and it writes a playable ROM next to it. The ROM never leaves your machine: the application does everything locally and talks to no server.
* **Spells and skill trees** are randomized, **monster drops** are drawn at every battle, all **vocations** are open from the start, and **story bosses** can be swapped for other bosses.
* **Two presets**, *Balanced* and *Total chaos*, with every rule available as its own checkbox.
* **The window speaks five languages**: English, French, German, Spanish and Italian, switchable at any time from the menu at the top right. Your choice is remembered.
* **Never the same monster twice on screen.** When a monster appears, it is always a species not already walking around you.
* **Field monsters load their own model far more reliably.** Since 1.2.1, loading a monster's model on demand could fill the model memory with copies of the same monster: few different monsters on screen, monsters wearing another one's model, and sometimes a freeze. Fixed.

**How it works, explained for players:** [monsters](docs/guide/MONSTERS.md) - [loot, ranks and rarity](docs/guide/LOOT.md) - [shops](docs/guide/SHOPS.md) - [spells and abilities](docs/guide/SPELLS.md) - [where every chest is](docs/guide/loot/containers_by_rank.md)

The randomizer does **not** rebalance the game's difficulty. Some randomized encounters may be significantly stronger or weaker than the original encounter.

**Demo video** : https://www.youtube.com/watch?v=1gUc4pJak4o

## How to use it

### 1. Check your ROM

The randomizer only works on the **European multilingual** release, and it refuses anything else rather than produce a broken game.

The required ROM is:

`Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds`

You do **not** need an English-only ROM. The English, French, German, Spanish and Italian languages are all included in this single European ROM. The filename does not matter - the application checks the contents.

* **Serial:** `YDQP`
* **CRC32:** `FE8EC0E8`
* **MD5:** `3a63438fff7db282fa3133e8fd020e85`
* **Size:** `268,435,456 bytes`

No ROM is distributed here - use your own copy of the game.

### 2. Run the application

Download `DQIX-Randomizer.exe` from the
**[latest release](https://github.com/DQIX/DQIX-RANDOMIZER/releases/latest)** and double-click it. Nothing to install: Python and every library it needs are inside the file.

> Windows may show a blue **"Windows protected your PC"** banner the first time. That is SmartScreen reacting to a new program that nobody has signed, not a virus report. Click **More info**, then **Run anyway**. If you would rather not, build the application yourself - see *Building* below.

Then:

1. **Drop your ROM** on the window (or click *Browse...*, or drop the ROM on the application's icon). The fingerprint is checked straight away.
2. **Pick a seed**, or leave the random one. The same seed with the same options always produces exactly the same game, so a seed is all you need to share a run.
3. **Choose a preset**, and adjust the checkboxes if you want something else.
4. Click **Randomize**. It takes about 25 seconds and writes `DQIX-Randomizer-seed<seed>.nds` next to your ROM.

### 3. Play

Run the produced `.nds` file in your Nintendo DS emulator and start a **new game**.

With DeSmuME, disable the Dynamic Recompiler. A crash that disappears once that option is off was caused by it.

The randomizer has been tested with **melonDS through BizHawk** and **DeSmuME**. Unmodified save files are not supported, and it has not been tested on real Nintendo DS hardware or flashcarts.

## The two presets

| | **Balanced** | **Total chaos** |
|---|---|---|
| Loot | rarer items come from rarer places: five-star legendary equipment only from the highest-rank chests, the rarest drops, and red chests that already held something that rare. Consumables get a real share of what containers give: about a third of the weight, against one tenth without it | any item from any container - legendary gear can come out of the first barrel of the game, and nine containers out of ten give equipment |
| Shop prices | a shop never offers anything pricier than what the original game sells there. The 37 shops are ordered by story progression, so an early armoury stays affordable | no price bound: the first village can stock expensive gear, up to 3 stars |
| Shops | every slot keeps its family, so an armourer never sells a sword and a grocery keeps its count of accessories; four and five-star items are reserved for Dourbridge's secret shop and the two Stornway stalls that open after the final boss | any item in any shop, except that 4- and 5-star items still stay in those three shops |
| Spells | a vocation still learns weak spells early and strong ones late -- the power scale is the game's own (the median level at which vanilla teaches each spell) | Omniheal can land at level 1 |
| Skill trees | every milestone of a tree -- abilities and stat bonuses alike -- is shuffled **within** that tree, so a sword tree still grants sword techniques, which matters since a weapon technique needs that weapon in hand | milestones move across all 26 trees, by cost band: a sword technique can show up in the whip tree. A bonus that names the tree's weapon ("Attack +10 with") stays in a weapon tree |
| Monster drops | drawn at every battle; 4- and 5-star items stay rare (about 1 drop in 60) | any item, legendary gear included |
| Vocations | all twelve at the abbey from the start; the hero and every recruit get a random vocation | same |
| Monsters | the 256 bestiary monsters roam, and only them | same |
| Boss battles | untouched | every scripted boss battle -- story, lairs, fixed fights -- is fought against **another boss**, never against an ordinary monster |

"Balanced" is a comparison with total chaos, not with the original game: it is still a randomizer, and it is still hard.

Every checkbox can be set individually - the preset then shows **Custom**.

| Checkbox | What it does |
|---|---|
| Field monsters | which monsters appear where |
| Chest and pot contents | chests, pots, barrels and cupboards, plus the item each monster carries |
| mostly equipment | the game has six times more equipment than consumables. Without this box, the randomizer gives consumables about a third of what containers hold; with it, nine containers out of ten give equipment |
| rare items everywhere | a container's rank no longer limits rarity: legendary gear can turn up in the very first barrel |
| red chests without guarantee | a red chest no longer keeps the star rating of the item it held (give or take one), so a late dungeon can hold a training vest |
| New drops every battle | the item a monster can drop is drawn again at every battle. Drop chances do not change |
| 4- and 5-star items as common as the rest | otherwise a 4- or 5-star item is kept only once in eight draws (about one drop in 60) |
| Shops | what the 37 shops sell |
| expensive gear for sale from the start | shops are no longer bound by what the original game sells there (4- and 5-star items still stay in the three endgame shops) |
| any item in any shop | shop families no longer apply: an armourer may sell herbs. 4- and 5-star items still stay in the three endgame shops |
| Story bosses | the 89 boss references of the game's scripted battles. A boss is always replaced by another boss. A story boss keeps its stand-in until you beat it; the three Gittish generals face you with a new one for the rematch; the twelve **lair bosses** get a new one every time you enter their lair. The prologue fight - two slimes and a cruelcumber against a level 1 hero with no party - is never touched, in any mode |
| keep the first boss | Hexagoon stays himself. He is the first boss and the only one fought with no party, so any other boss in his place can make the run impossible. On by default |
| Spells | the spells each vocation learns by levelling. The three vocations without magic (Warrior, Martial Artist, Gladiator) stay without magic |
| powerful spells from the start | a vocation's spells are no longer ordered from weak to strong |
| Skill trees | what each skill-point milestone gives - ability or stat bonus alike - in battle and in the menus |
| mix the trees together | milestones move between trees |
| Vocations | the abbot of Alltrades Abbey offers all twelve vocations from the start. The unlock quests still work |
| random vocation for recruits | a companion created at Patty's gets one of the twelve vocations at random; her menu only offers "Random" |
| random vocation for the hero | the hero starts a new game with a vocation drawn from the seed instead of Minstrel. During the prologue the hero is still shown as a Guardian, as in the original game; the drawn vocation shows after the fall |
| locked vocations | the abbot refuses to change anyone's vocation, in all five languages; revocation (back to level 1 in the same vocation) stays. Everyone keeps the vocation they got. The unlock quests still work, but quests that need you to practise another vocation can no longer be done. Off in both presets |
| Monster stats (experimental) | HP, attack, defence, agility, experience and gold are swapped between all monsters, bosses included, with no bound: an early slime can get a late boss's HP. It works, but nobody has played a run with it yet. Off in both presets |

Two things are never randomized, in any mode: **key items**, and the **chronocrystal shop** - both would let you break the story. And in every mode, 4- and 5-star items are only sold in Dourbridge's secret shop and the two Stornway stalls that open after the final boss.

## Sharing a run

A seed plus the list of options is enough: anyone with the same European ROM gets the same game, byte for byte. The application also has an **"Also create an .xdelta patch"** box for sharing a run as a patch; it needs `xdelta3` on your `PATH` or next to the application, and it is not required for anything else.

## Building

### From source

You need Python 3, and:

```bash
pip install ndspy keystone-engine capstone
```

Then, for the window:

```bash
python interface.py
```

or, for the command line:

```bash
python randomizer.py "<your European ROM>.nds" --seed 1 --sans-rotation --place --blob --plafond 1 --garde 163840 -o "DQIX Randomizer.nds"
```

Any given seed always rebuilds the same ROM, byte for byte, on any machine. (To rebuild the **1.3** release exactly, check out the `v1.3` tag: 1.4 changed how boss battles draw, so the same seed now gives a different game.) Loot and shop randomization are on by default; add `--sans-objets` or `--sans-boutiques` to leave either of them alone, or `--chaos-total` (with the five monster options above) for the Total chaos preset. See every option with `python randomizer.py --help`.

### The application

```bash
pip install pyinstaller tkinterdnd2
python scripts/build_exe.py
```

writes `dist/DQIX-Randomizer.exe`. The application also accepts a command line directly, which is handy for scripting several seeds:

```
DQIX-Randomizer.exe --cli "<rom>.nds" --seed 1234 --sans-rotation --place --blob --plafond 1 --garde 163840 --chaos-total -o out.nds
```

## Troubleshooting

| Problem | Solution |
| --- | --- |
| "Not the supported ROM" | The fingerprint does not match the European release above. American and Japanese releases will not work. |
| Windows SmartScreen warning | The application is not code-signed. *More info*, then *Run anyway*, or build it yourself. |
| Your antivirus quarantines the .exe | A known false positive with PyInstaller-packaged programs. Building it yourself avoids it. |
| The .xdelta box does nothing | `xdelta3` was not found. Put `xdelta3.exe` next to the application, or share the seed instead. |
| The game crashes on DeSmuME | Disable the Dynamic Recompiler. |

## Known issues

* **European multilingual release only.** Other regions have different addresses; the randomizer refuses to touch them.
* When several monsters are on screen and the model memory is full, a monster can still appear with another monster's model until one of them leaves the screen.
* Large monster models are more likely to cause visual/model issues.
* Sometimes a battle's command window turns light blue with dark text, or a monster shows the wrong colours. The cause has not been found yet.
* The randomizer has only been tested from a fresh game start.
* Blue chests, pots, barrels and cupboards get their content when you enter a room, like in the original game. In a room with no monsters around, leaving and coming back quickly can give the same content again: the game's random number generator only moves when something happens (monsters, walking NPCs, battles).
* Emulator savestates only work with the exact ROM they were made on. A savestate from an older patched ROM can show item messages without the item name.
* Some randomized encounters can be considerably stronger or weaker than the original encounters because the game is not rebalanced.

## Release files

Since 1.5, each release attaches `DQIX-Randomizer.exe`. Releases up to 1.3 attached a fixed-seed `.xdelta` patch instead, with spreadsheets of where every item comes from.

## Sources

This project was made possible thanks to the following resources:

- [ArchipelagoDQIX](https://github.com/kid2407/ArchipelagoDQIX/tree/main) by kid2407
- [dqix-decomp](https://github.com/ZevyaDev/dqix-decomp/tree/naming-pass) by ZevyaDev
- *Guide to RNG systems in DQIX for game manipulation* by hurblub

## Disclaimer

This project does not distribute any copyrighted game ROM or other copyrighted game assets.

You must provide your own legally obtained copy of **Dragon Quest IX: Sentinels of the Starry Skies**.

The randomizer is provided as-is. Use it at your own risk.
