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
| [09-loot.md](09-loot.md) | §79–§81 | 1.2: `treasure.nsarc`, draw tables, the item catalogue and key items, item names, monster drops and rate classes, star rarity |

## Where to start

- **Monster randomizer as shipped**: §15–§17 (encounter data), then §72–§78.
- **Loot randomizer as shipped**: §79–§81.
- **Before writing any ARM9 patch**: §27 (`CompressedStaticEnd`), §38/§40/§61
  (savestates and file layout), §69 and §72 (code space), §74.1 (validate probes first).
