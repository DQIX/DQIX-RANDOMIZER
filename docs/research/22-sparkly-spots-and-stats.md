# 22. Sparkly spots and monster stats

## 105. Sparkly spots: one item per group of points (ZER-97, 20 October 2026)

**Where.** Two Nitro scripts (the bytecode of `treasure.py`, see §79):

| file | content |
|---|---|
| `data/scenario/flditem.pac` | a NARC with one `Fxxflditem.bin` member per field map (40 maps, `F01` to `F63`), plus `fldbias.bin` and a forgotten **`.svn/` copy of every member** (`text-base`, `prop-base`, `entries`…), which the game never opens |
| `data/bin/izmitm.bin` | the two special zones 98 and 99 |

The ARM9 symbols of the community project `dqix-functions` (`arm9_ram.yml`:
`loadItemPickupDefinitions`, `parseItemPickupDefinitionInstruction`,
`parseItemPickupBiasInstruction`) describe the Japanese ROM; everything below is
measured on the European ROM.

**Opcode `0x66`, one group of points.** 32 integer parameters:

```
p0      zone index (0..99, the index of the save's pickup timer table)
p1      item id (the itemdt id of objets.py)
p2, p3  always 1, 1
p4      0..7: use the default delays of fldbias.bin (mode p4)
        8:    custom delays in p5..p7
p5      respawn delay (30, 60, 90, 120, 240, 360)
p6      respawn group
p7      number of points
p8..    up to 8 positions (x, y, z), integers, zero-padded
```

87 groups on the 40 maps, **one item per group**, 45 different items, all
ordinary items (ingredients, herbs, ores, one mini medal in Forêt de Valmort,
`F04` zone 12, respawn 360). **None is a key item**, so randomizing them
removes no quest item from the game.

`fldbias.bin` holds 8 opcodes `0x67` (one per save group, see below), each
with 8 triples `(respawn delay, respawn group, points)` for modes 0..7.

**`izmitm.bin`, zones 98 and 99.** Two opcodes `0x66` with float positions
only (7 points each, no item), then 8 opcodes `0x68`: `p0` = save group
0..7, `p1..p16` = 16 items. The save group is drawn once when the character
is created (`dispatchItemPickupTimerInitialization`: `UpdateAT() % 8`) and
stored in the save. Common entries in all 8 tables: medicinal herb, angel
bell, emerald moss, holy water, mini medal, narspicious, resurrock, astral
plume; the rest varies (sage's elixir, Yggdrasil leaf, lunaria…). Where
zones 98/99 are in the game is not identified yet.

### 105.1 How the game loads and gives a sparkly item (European addresses)

- **Zone load** `0x0208E530`: for map `R01M07` it runs `izmitm.bin` with the
  opcode table at `0x020F1278` (`0x66` → `0x0208E36C` creates the point nodes,
  `0x68` → `0x0208E454` copies the 16 items of **the save group's** table into
  a `0x20`-byte heap block, pointer at `struct+0x0C`); then, for maps whose
  code starts with `F`, it clears the struct (`0x0208E508`) and runs
  `Fxxflditem.bin` with the table at `0x020F1290` (`0x64`/`0x65` → empty
  functions, `0x66` → `0x0208E0D4`: a `0x70`-byte node, item = `p1` in the low
  16 bits of word 0, zone in bits 16-22, `0x67` → fldbias).
- **Save-timer pass** (all maps, `F%02dflditem.bin`): table at `0x020F1308`
  (`0x66` → `0x0208E8A4` only fills the 100 timer words).
- **Pickup** (overlay 17, `0x021989F0`): if the node's zone is ≥ 98, it calls
  `0x0208E7E0`, which draws `rand(8)` (or `rand(16)` from chapter `0x13` on)
  in the table at `struct+0x0C` and writes the item into the node; then the
  item is `node[0] & 0xFFFF`. **The game already draws an item at each pickup,
  for zones 98/99 only.**
- **The script interpreter** (`0x020307E0`) reads at most **128 parameters**
  per instruction (`cmp sb, #0x80` at `0x020308F4`) into an 8-byte-per-entry
  buffer at `ctx+0x2C`; an opcode missing from the table is skipped.
- **Respawn timer** (code read on the European ROM, matching the community
  description of `updateItemPickupRespawnTimers`, Japanese `0x0208F588` =
  European `0x0208EC88`; European = Japanese − `0x900` for this whole block).
  The save-timer pass (`0x0208E8A4`) stores `delay / 30` (1..12) in bits
  25-28 of the zone's timer word; the pickup (ov17 `0x0219899C`,
  `mov r0, #0x1e`) and the respawn (`0x0208EFC0`, `mov r1, #0x1e`) reload the
  low 9 bits with `step × 30`; the scheduler decrements them once per
  **60.0 s** (float literal at `0x0208F048`) while the zone is not full. So
  the delays 30..360 are **minutes of play**; after loading a save, a zone
  restarts at `step × 3` minutes (community description of
  `applyItemPickupNormalLoadInitialization`, not re-read here). The test ROM v17z3 (not a randomizer
  option) uses `× 1` and `6.0 s`: delay 30 → 6 s, 360 → 72 s.

### 105.3 An item is only given if its NAME was loaded with the map

Measured on October 20, 2026 (savestate `banc/states/v17y_cherubelle_point.State`,
probes `points_brillants.lua`, `ramasse_point.lua`, `ramasse_tous.lua`): with a
127-item table, the pickup draw works (it returned `0x563B`, written to the
message object) but **no message and no item**. Crossed control: the drawn
path with a medicinal herb gives « Papouz obtient une herbe médicinale. »;
the original path with a gold bar gives nothing. Of the 143 items put in the
table one by one, **only the three original items of the map's points** were
given.

At map load, `0x0201648C` builds on its stack (at most 100 entries) the list of
items whose names it loads (`0x020DE9B4`; the names sit in RAM, e.g.
`0x023560F0` « herbe m<'e>dicinale »): the item of every node, or — if the
first node's mode (`w1 & 0xF`) is 9, the special zones — the **first 16**
entries of the table at `struct+0x0C` (`0x02016738..0x02016780`).

So the randomizer keeps the table at 16 items (the original allocation and
copy) and makes the name loader use the table for every map (`0x02016748`,
`bne` neutralised); 40 maps × 16 = 640 slots cover the 143 items.

### 105.4 Sixteen items drawn at every map entry

The player wants different items at the same place on every visit
(20/10/2026). The `0x68` handler (`0x0208E454..0x0208E4C4`, 29 instructions,
literal at `0x0208E4C8` kept) is rewritten in place: it gets the structure
with `bl 0x0208E0B8`, allocates the original `0x20`-byte table, then draws
16 parameters **without replacement** (`rand_below`, the drawn parameter
swapped with the last one in the interpreter's buffer, which is not used
afterwards) — so each map carries a pool of 16 to 127 items (one `0x68`
with up to 128 parameters) and draws 16 of them at every entry; the names of
those 16 are then loaded (§105.3). Checked by emulation (unicorn, 200 pools
of 16 to 127 items: 16 distinct items of the pool every time, structure
written, registers and stack preserved).

### 105.2 The randomizer

`scripts/patch_points.py`, `--points-brillants` (default: **drawn at each
pickup**) extends the zones-98/99 mechanism to every map, without new code:
each `Fxx` member gets an opcode `0x68` with 16 items (its pool), its `0x64` (empty) become `0x65` (empty), and so
do fldbias'; entry `0x64` of the map table becomes `(0x68, 0x0208E454)`, entry
`0x64` of the timer table becomes `(0x68, empty function)`; the `0x68` handler
no longer checks the save group (`0x0208E47C`); the pickup draw uses 16
instead of 8 before chapter `0x13` (`0x0208E7F8`); the map loader loads the
names of the table's 16 items for every map (`0x02016748`, §105.3); and overlay 17 `0x02198A00` (`blo` past the special draw) is
neutralised. `izmitm.bin` keeps a single `0x68`, the pool. Pools come from
the 143 ordinary items of `objets.pool` (no equipment, no key item, no
`HORS_TIRAGE`), a sliding 16-item window of a shuffled list per map (all 143 covered);
`--points-brillants-par-rang` restricts each map's pool to the union of its
groups' one-star bands. `--points-brillants-fixes` instead rewrites `p1`
of the 87 groups and the 128 table entries in place (one fixed item per
group). In-game check pending (ROM v17y). `python scripts/patch_points.py ""
out.csv` lists every group and entry.

## 106. Monster stats are written to both monster files (ZER-58, 20 October 2026)

§91.1 showed that battle reads HP and actions from `mon_moddata.nat`, and §94.4
that species drawn by the blob are read from `mon_btldata.nat`. In the vanilla ROM
both files hold **identical** HP, MP, attack, defence, agility (different offsets,
see `patch_stats.OFF_MOD` / `OFF_BTL`) and identical 24-byte resistance blocks
(`mon_moddata +0x10` = `mon_btldata +0x6C`) for all 438 records: measured,
0 differences.

Resistance values found in the 438 records:

| block | values (count) |
|---|---|
| 7 elements | 0 (7), 50 (301), 75 (206), 100 (1808), 125 (354), 150 (324), 200 (66) |
| 14 ailments | 0 (2020), 5 (186), 10 (98), 15 (65), 25 (385), 35 (23), 50 (1226), 75 (1007), 100 (1100); rare: 1, 30, 60, 150, 200 |

Which column is which element or ailment is **not identified**.

`scripts/patch_stats.py` (`--stats`, `--stats-chaos`) draws the values and
writes them to both files, identical (`patch_stats.verifier`). It never
touches the prologue species (290, 292), the cutscene Aquila and Corvus (800,
801) or the training dummy (900). In-game effect: pending the player's test.

### 106.1 Drawn again at every battle (ZER-96)

At battle start, overlay 0 builds the battle copy (one 0x84-byte `mon_btldata`
record per species present, table count in the low 12 bits of `[r5+0x400]`,
records at `[r5+0x404]`), then (`0x02165A54..0x02165BAC`) rewrites, for each
**zone** species, HP/MP/agility/attack/defence from its `mon_moddata` record
(`0x02165A88..0x02165AAC`), the actions (`memcpy` at `0x02165AEC`) and the
resistances (`memcpy` at `0x02165B8C`). Species drawn by the blob keep their
`mon_btldata` values (§94.4).

`patch_stats.poser_combat` adds no code to overlay 0: it **redirects two
existing calls** to three verified free ARM9 fragments (`0x020F1E40` 72 B,
`0x020E8888` 40 B, `0x020E7C78` 40 B, left over by the abandoned rotation
and graft C):

- `0x02165B8C` (`bl memcpy`, zone species) → copy the resistances, then draw
  the record in `r4`;
- `0x02165A30` (`bl 0x02012FF4`, or the actions graft already there) → draw
  every record of the battle copy, then branch to the previous target. The
  actions graft (`patch_actions`) removes and re-poses this one around its own
  changes, and accepts it at its site.

The ranges live in the record's zero padding, `mon_btldata +0x2C + 4k` (min)
and `+0x2E + 4k` (max), k in the stats order (HP, MP, attack, defence,
agility, the order of `+0x5C..+0x64`); a zero HP max = not drawn. The draw
uses `0x02032380` (`rand_below`), stack kept 8-byte aligned. Resistances are
not redrawn (no room). Checked by emulation (unicorn, three records, ranges
respected, an unranged record untouched, registers and stack preserved,
previous target called once); in-game check pending.

## 107. A fixed kit for each monster, with real ability animations (20 October 2026)

The player asked for spells and abilities drawn **once**, when the ROM is
built, the same for every monster of a name ("all slimes have the same
kit"), as an alternative to the draw at every battle (§92-94).

**Data only.** `patch_actions.fixer` uses the same slots as the per-battle
draw (`remplacer` / `ajouter`), draws them with its own generator, writes
the actions into `mon_moddata` and `mon_btldata` and leaves both masks at
zero, so no overlay 0 graft is posed. 25 bestiary names have several records
(slime: 1, 266, 267, 291): one draw per English name, on the first record
with slots to draw, copied to the others. MP = max(original, 3 × the cost of
the dearest drawn action), as the graft does.

**Black screen at every battle** (test ROM v17z5): the drawn abilities were
attached to the generic cases of `default.bact` with lists of 40 ids, the
1.6 measurement. The `op01` handler copies a list onto 0x40 bytes of stack
(§94.7): **32 ids at most**. Lists of 32 (`LISTE_PILE`) and the battle frame
heap raised by 16 KB (the literal of §94.7) fixed it (v17z6, 662 commands).

**Real animations in the monster's own model.** A battle loads each
monster's full model `<code>.mon` (a NARC in `data/pack_lv5/enemy.gp2`:
`.bact`, `.cchr`, `.cmot`) and compiles its `.bact` (overlay 0
`0x021662D8`, into an allocator of the monster object, `object+0x44`); a
case in the model's `.bact` wins over `default.bact`. With a fixed kit the
abilities of each species are known at build time, so
`patch_kits_animes` copies the real case of each one into the species'
model `.bact`, with the copy rules of §94.7 (`corps_cas`). Model `.bact`
files pad the commands and the string pool to 16 bytes with `0xFF`
(measured on the 312). Budget: 400 added commands per model, cheapest
cases first; seed 17 gives 499 abilities in 255 models, 2 stay generic.
Checked in game on the heaviest case (manguini sanguinaire, 391 commands,
4 abilities; v17z12) and on slimes / will-o'-wisps (v17z11).

**Rewriting `enemy.gp2`.** Its index is compressed (type 2, CompressB),
unlike the item archives (type 0). The archive opener (`0x020D91EC`) reads
the 0x14-byte header, checks `(headerLength + decompressedFileInfoLength) ×
4 + 4` against its buffer (0x30000 for models), then reads and decodes the
index (`0x020D8EF4`, block types 0 to 4 dispatched at `0x020D87D0`); a
member is read at `firstFileOffs × 4 + offset × 4` (`0x020D9468`). An index
re-encoded as **type 1** (literal-only LZSS, the encoding of the item
prices) made **every monster invisible**, on the field and in battle
(v17z10), although our decoder reads it back. Written **raw (type 0)**, as
in the item archives, it works (v17z11, v17z12). `gp2_ecrire.reecrire_index`
rebuilds the index, copies the name table, and rewrites `fileInfoLength`,
`firstFileOffs` and the total; untouched members are copied byte for byte.
