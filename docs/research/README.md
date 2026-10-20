# Research notes

Everything measured about the European ROM of Dragon Quest IX (`YDQP`) while building
the randomizer: file formats, addresses, disassembly and the evidence behind each claim.
The player guide is in [`docs/guide/`](../guide/README.md).

The notes are a lab log, kept in the order the work happened. Sections are numbered
§1 to §81 and keep their numbers across files, so a reference like "§57" is stable.
Later sections often **correct** earlier ones; the corrections are kept and flagged
rather than silently rewritten, because the wrong turns explain why the code looks the
way it does.

> **CONFIRMED** means checked against at least two independent clues.
> **HYPOTHESIS** means still to validate, usually by watching the game in the emulator.
> All addresses are for the EU ROM unless stated otherwise.

## Files

| File | Sections | What it covers |
|---|---|---|
| [01-rom-formats-and-monster-table.md](01-rom-formats-and-monster-table.md) | §1–§14 | ROM layout, NitroFS, archive formats (GPC2, NARC, LZ), the monster stats table `mon_btldata.nat`, monster names |
| [02-encounter-tables.md](02-encounter-tables.md) | §15–§18 | `encfld` / `encbtl` / `encmons`, how the field drawer picks a species, the loaded table in RAM |
| [03-spawn-patches-and-zone-lists.md](03-spawn-patches-and-zone-lists.md) | §19–§31 | First code patches, why per-spawn randomness looked impossible, group and preload caps, the `CompressedStaticEnd` trap, the model loader found in the game |
| [04-on-demand-loading-first-attempts.md](04-on-demand-loading-first-attempts.md) | §32–§46 | Loader toolbox, dead-code hunting, container grafts, model size budget, savestates tied to the file layout, first rotation chain |
| [05-heaps-and-rotation.md](05-heaps-and-rotation.md) | §47–§57 | The model heap is a frame heap, cumulative size budget, rotation design, ExpHeap conversion, community symbols, the complete memory plan |
| [06-rotation-freezes.md](06-rotation-freezes.md) | §58–§64 | Rotation tested in play: offset mistakes, freezes and their real causes, the allocator tree wall |
| [07-gatekeeper-and-on-demand-loader.md](07-gatekeeper-and-on-demand-loader.md) | §65–§71 | P3 universal gatekeeper, VRAM watermark, the source table of 438 species, code space inventory, loading through the preloader |
| [08-relocatable-blob-and-eviction.md](08-relocatable-blob-and-eviction.md) | §72–§78 | Code loaded from a ROM file (the architecture of 1.0/1.1), uninstall on battle entry, eviction, the 256-species pool, field records |
| [09-loot.md](09-loot.md) | §79–§81 | 1.2: `treasure.nsarc`, draw tables, the item catalogue and key items, item names, monster drops and rate classes, star rarity; grotto chests (`randTD`, 1.7) |
| [10-equipment-menu-fix.md](10-equipment-menu-fix.md) | §82 | Why live monsters lost their model when the equipment menu rebuilt the field context, and the blob's size ceiling |
| [11-shops.md](11-shops.md) | §83 | `shopdata1.bin`: the 37 shops, their format, the full census of what they sell, and the open questions on places and prices |
| [12-scripted-bosses.md](12-scripted-bosses.md) | §84 | The 98 scripted battles named in story order, which bosses can be fought again, Hexacorne the first boss, the record parser at `0x02074070` where a per-encounter draw would go, and field 7, the battle music, which follows the boss (ZER-94) |
| [13-one-species-on-screen.md](13-one-species-on-screen.md) | §85–§86 | Never the same species twice on screen: the drawer's two callers, the `tirage_unique` graft; the model loaded before the spawn, and the heap fragmentation that limits it |
| [14-skill-trees.md](14-skill-trees.md) | §87–§88 | Skill trees: field 0 of `skilltable.bin` is the palier ID and carries the bonus type, the weapon icon comes from the tree, labels that name the weapon, learning messages and their five-bit number |
| [15-vocations-and-drops.md](15-vocations-and-drops.md) | §89–§90 | Vocations are story flags, the abbey list and the recruit graft; the battle's own copy of the monster records, the rate classes it rewrites, and the per-battle drop graft behind overlay 23, the bestiary's own copy of the drops (`mons_info2.nat`), and where the field rate classes live (`mon_moddata` +0x30/+0x31) |
| [16-monster-actions.md](16-monster-actions.md) | §91-94 | The battle reads `mon_moddata.nat` (stats and the six action slots), action ids and names, and the per-model `.bact` script that presents an action: a foreign technique runs but shows nothing. Where each battle copies the actions (overlay 0, `0x02165AEC`), the spell id range, and the graft that draws spells and techniques per species at every battle; the slot picker and the per-action conditions; `default.bact` and its limits; the other generic cases seen in battle (three freeze) and the reinforcement table; real animations of 256 abilities, about ten per battle (battle heap, copy rules, variants); one draw table and one routine for spells and abilities (§94.8) |
| [17-battle-groups-bosses-drops.md](17-battle-groups-bosses-drops.md) | §95–§100 | Why a blob monster fights alone (`GenerateCompanionByBT`, leaders and companions of `encbtl`) and the template graft; drop rates are vanilla per monster; the three boss families of `eventbattle.bin` and the 1.6 boss modes; why the Whistle spawns nothing with a full model heap; which weapon a technique needs (the tree it sits in) and how to keep the origin weapon; spawn modes without code patches (per map 1-to-1, global) |
| [18-palette-vram.md](18-palette-vram.md) | §101 | Palette VRAM layout (interface, text, one block per party member, map, symbols, preloader), marks and rollbacks, and why the on-demand loader painted monster colours on the hero and the text (graft C removed) |
| [19-alchemy.md](19-alchemy.md) | §102 | Alchemy: `recipe.gp2` decoded (470 recipes, product, three ingredients and quantities), the 22 great-success pairs, where recipe books live and what text will lie once ingredients move |
| [20-mini-medals.md](20-mini-medals.md) | §103 | Cap'n Max Meddlin': his milestone and shop tables in overlay 4, the save counters, how few mini medals the randomized loot leaves, and the medal randomizer |
| [21-boss-field-models.md](21-boss-field-models.md) | §104 | Battle and field model files (`<code>.mon`, `<code>_f.mon`) in `enemy.gp2`; which of the 54 boss models have a field file, which can borrow one from a colour variant, which have none |
| [22-sparkly-spots-and-stats.md](22-sparkly-spots-and-stats.md) | §105-107 | Sparkly spots: `flditem.pac` (one item per group of points, 87 groups) and `izmitm.bin` (zones 98/99, 8 tables of 16 items, one per save); monster stats written to both monster files, resistance values; fixed monster kits with real ability animations in the models' `.bact`, rewriting `enemy.gp2` (raw index) |

## Where to start

- **Monster randomizer as shipped**: §15–§17 (encounter data), then §72–§78, then §85–§86.
- **Loot randomizer as shipped**: §79–§81.
- **Scripted bosses**: §84.
- **Skill trees (1.5)**: §87–§88.
- **Vocations and per-battle drops (1.5)**: §89–§90.
- **Alchemy recipes**: §102.
- **Mini medals and Cap'n Max Meddlin'**: §103.
- **Sparkly spots, monster stats**: §105–§106.
- **Why a savestate stops being valid**: §38, §40, §61 and §82.
- **Before writing any ARM9 patch**: §27 (`CompressedStaticEnd`), §38/§40/§61
  (savestates and file layout), §69 and §72 (code space), §74.1 (validate probes first).
