# 16. Monster actions and their presentation (§91)

Measured on September 25–26, 2026 (ZER-54), with four test ROMs built from the
vanilla ROM by `scripts/essai_techniques.py` (data only, no code), played by
the player from a cold boot with their save, and one in-battle savestate
searched with `scripts/find_in_state.py`.

## §91 A monster can carry another monster's actions — the effect works, the show does not

### 91.1 The battle reads `mon_moddata.nat`, not `mon_btldata.nat`

`data/prm/mon_moddata.nat`: `u32 count = 438`, then **438 records of 64 bytes**,
same order as `mon_btldata.nat` (`4 + 438 × 64 = 28,036`, the exact file size).

```
+0x00  u16   monster id (index + 1 for the first species)
+0x02  u16   max HP          slime 8, metal slime 4
+0x04  u16   max MP          slime 2, metal slime 255
+0x06  u16   agility         metal slime 89
+0x08  u16   attack          metal slime 35
+0x0A  u16   defence         metal slime 256
+0x10  ..    resistances (same values as mon_btldata +0x6C..)
+0x28  u32   experience,  +0x2C  u32  gold
+0x30  u16   drop rate classes (as mon_btldata +0x02)
+0x32  u16×6 the six action slots (as mon_btldata +0x18)
```

**Evidence.**

- *Test 1*: the six action slots of the slime (index 0) replaced by those of
  Corvus (index 301) **in `mon_btldata.nat` only**. In game the slimes only
  attack. In the player's in-battle savestate, the slime's 64-byte
  `mon_moddata` record is found **whole** in RAM, next to the combatant, with
  its vanilla actions at `+0x32`; the Corvus actions written into
  `mon_btldata` appear nowhere in the battle.
- *Test 2*: the same actions written into `mon_moddata` as well (and 255 MP):
  the slime now psyches up and uses other attacks.
- *Tests 3 and 4*: four species at 600 HP (`+0x02`); the player reports they
  take many hits. So battle HP comes from `mon_moddata` too.

**Consequence**: the stats that `--stats` writes into `mon_btldata.nat`
(`+0x5C..+0x64`) very likely have no effect in battle. This matches the caveat
of §4, a monster set to 111 HP that died from 73 damage. Not yet re-measured
with `--stats` itself. `mon_btldata` keeps the dropped item ids (`+0x04`,
`+0x06`), which do work (1.2).

### 91.2 Action ids and names

`data/prm/actname.nat`: 8-byte header, then pairs `(u32 id, u32 name offset)`
from `+0x0C`; names pool at `0x1554` (English only). `0x0001` Attack,
`0x0014` Kaswoosh, `0x00A0` War Cry, `0x00A1` Psyche Up, `0x00BD` Disruptive
Wave, `0x00E1` Flee, `0x010A` Hellfire. 215 of the 383 action ids used by
monsters have no name in this table (for example `0x00F4`, used by 62
species); "no name" does not mean "boss only".

`actdt_b.gp2` → `actdt_b_<lang>.nat` (members stored raw, **no** control word):
`u16 count|flags` (`0x126A` → 618), then **618 records of 60 bytes**:
`+0x00 u32` name offset, `+0x04 u16` action id in the low 10 bits and a
category in the high 6 bits (0 for most monster techniques, non-zero for
Frizz, Kaswoosh…), then the action's data. `actdt_a` holds a further 63
records (heals among them) in the same layout.

**Measured precisely on 19/10/2026 (ZER-91, `sorts.noms_localises`):** read
from the start of the member, record `i` is at `2 + 60·i`; its action id is
the low 10 bits of the u16 at `+6`, and the name is a u16 at `+2`, relative
to `pool + 2` where `pool = 2 + 60·n` (so the "u32 name offset at +0" above
holds for records counted from file offset 4). The action id is the second
field of the `spelltable` 0x66 record **as is** — without the off-by-one of
`actname.nat`. Witness: 346 of the 358 English names equal `actname`'s, the
12 others differ only by the `<1>` apostrophe tag. This is where the game's
**localised** spell names live (`actname.nat` is English only): all 61
learnable spells are named in the five languages (Omniheal = Omnisoin (fr),
Megaheilung (de), Omnicuración (es), Omnicura (it)).

### 91.3 Presentation lives in each model's `.bact`

Every battle model `<code>.mon` in `data/pack_lv5/enemy.gp2` is a NARC of three
files: `.cchr` (model), `.cmot` (motions) and **`.bact`**, a command script:
header `u32 ?, u32 string pool offset, u32 ?, u32 ?`, then commands
`u16 opcode, u8 argc, u8 arg types (2 bits each: 1 int, 2 float)` followed by
`argc` 32-bit arguments; the string pool holds effect paths and motion names
(`effect/z013000.chr`, `attack0a`, `breath`…).

After a default block, **`op11` opens the list of per-action cases, each one
starting with `op01 [action id]`**. The funghoul (`z013a`) has
`op01 [228]`, i.e. `0x00E4` Sweet Breath, its own technique: it loads
`effect/eb2040.chr`, `effect/z013010.chr`, `effect/z013011.chr` (`op12` takes a
string pool offset), moves the camera (`op30`–`op32`) and plays its `breath`
motion.

**Measured in game** (tests 3 and 4, one action ×6 per species):

| species | action | text | animation | effect |
|---|---|---|---|---|
| slime | Kaswoosh `0x14` (spell) | yes | yes | yes |
| slime | Hellfire `0x10A` (breath) | no | camera only | damage taken |
| she-slime | Disruptive Wave `0xBD` | no | camera only | — |
| dracky | Corvus `0x21C` | no | camera only | damage taken |
| dracky | `0x00F4` (62 species) | no | camera only | yes |
| funghoul | Corvus `0x25B` | no | camera only | seems to act twice |
| funghoul | War Cry `0xA0` | no | camera only | party debuffed |

So: **an action with no case in the monster's `.bact` still runs** — damage,
debuffs — but shows no message and no animation, only a default camera move.
Spells are presented by a generic path that does not need the `.bact`.
No freeze in any test.

### 91.4 What it means for a technique randomizer

- Spells can be given to any monster today, as data only (`mon_moddata` +
  `mon_btldata`, `+0x32` / `+0x18`), with full presentation.
- Giving a technique with its presentation means adding a case to the target's
  `.bact`, with a motion the target has (`attack0a`) instead of the donor's
  (`breath`). That rewrites `enemy.gp2`, which belongs to the monster
  machinery (model sizes, loader), so it would need its own validation.
- Which field of `actdt_b` separates "generic presentation" from "needs a
  `.bact` case" is not settled: the category bits are non-zero for Frizz and
  Kaswoosh, but zero for Kabuff, whose presentation has not been tested.

## §92 Spells drawn at every battle (ZER-56)

Measured on September 26, 2026 with `scripts/lua/guet.lua` and a probe
(`work/zer54/debut_combat.lua`) on the test-3 ROM and its savestate, then on the
ZER-56 test ROM from a cold boot with the player's save.

### 92.1 Where the battle gets a monster's actions

Two copies, not one:

1. **At zone load**, `0x020A8FE0` (ARM9, called from overlay 17 at
   `0x021B5620`) reads the whole `mon_moddata.nat` into the static buffer
   `0x0211E33C` and copies **one 64-byte record per species of the zone** into a
   heap table (`bl memcpy` at `0x020A914C`, stride `0x40`), then sorts it.
   Measured: four records (indices 0, 1, 3, 8 of the test ROM) copied to
   `0x022F2C18..` when entering the Plicatoise region. Randomizing there would
   hold for a whole zone visit.
2. **At the start of every battle**, overlay 0 (`0x02165A54..0x02165BAC`)
   looks each present species up in that zone table (`0x020A93AC`) and
   overwrites the battle copy of its `mon_btldata` record (`0x84` bytes per
   species, §90.1) with the `mon_moddata` values:

   | battle copy | from `mon_moddata` |
   |---|---|
   | `+0x5C` HP, `+0x5E` MP, `+0x64` agility, `+0x60` attack, `+0x62` defence | `+0x02`, `+0x04`, `+0x06`, `+0x08`, `+0x0A` |
   | `+0x10` bit fields (7 fields) | `+0x0C` |
   | **`+0x18` the six actions** — `bl memcpy` at **`0x02165AEC`** (`r0` = copy+0x18, `r1` = record+0x32, `r2` = 12) | `+0x32` |
   | `+0x6C` resistances (0x18 bytes) | `+0x10` |
   | `+0x08` exp, `+0x0C` gold, `+0x02`/`+0x03` drop rate classes | `+0x28`, `+0x2C`, `+0x30`, `+0x31` |

   Measured with a read watch on the zone table: at the battle's first frame,
   `0x02165A84` reads record+0x02 and the memcpy called from `0x02165AEC` reads
   record+0x32 into `0x02362004` = copy `0x02361FEC` + 0x18.

This explains §91.1: test 1 wrote the actions into `mon_btldata.nat` only,
and this code overwrote them with the `mon_moddata` ones at every battle.

**One record per species**: every copy of a species in a battle shares it.

### 92.2 The spell list is a range

The characters' battle spells occupy action ids **`0x09..0x3E` with a single
gap, `0x1D`** (§91.2 table: Frizz `0x09` … Kamikazee `0x1B`, Magic Burst
`0x1C`, Heal `0x1E` … Kazing `0x27` from `actdt_a`, Tingle `0x24`,
Cock-a-doodle-doo `0x25`, Kerplunk `0x28`, Buff `0x29` … Divine Intervention
`0x3E` from `actdt_b`) — 53 spells. Field spells (Zoom `0xCA`, Evac `0xCD`…)
and techniques (`0x3F` Dragon Slash onwards) are outside it. Monster-only
duplicates of spells exist (`0xF6` Frizz, `0xF7` Crack, `0x12A` Kerfrizz,
`0x1C7..0x1D4`); they are left out.

### 92.3 The graft (`scripts/patch_actions.py`)

> **Layout superseded by §94.3**: the graft moved to `0x02155710` and the
> hook block now holds a 1,024-bit technique table; the principle below is
> unchanged.

No free space is safe at battle start: the ARM9 paddings are taken, overlay 0
fills its slot up to `0x021842A0` (the next slot's base), overlay 17's BSS
ends exactly at `0x021D8A40`, and the overlays found in the other slots at
that moment are leftovers of the previous battle (13 and 23 in our run).

But the block `0x02165AB0..0x02165B7C` (52 instructions) copies the seven bit
fields of record+0x0C one at a time. Written equivalently in 21 instructions
(the last four fields are contiguous: `D[8:18] = S[9:19]`, one shift), it
leaves room for the graft in the same block:

    bl graft                 ; replaces the memcpy, r0-r2 already set
    <bit fields, 20 instructions>
    b 0x02165B80
    graft: memcpy, then 6 x (rand_below(54) + 9, redrawn on 0x1D) into
           copy+0x18, then copy+0x5E (MP) = 255

`verifier_equivalence()` runs the original and the rewritten block under
unicorn on 2,000 random records: every byte of the battle copy outside the
actions and MP is identical; a mutation test (three single-instruction
faults) is caught.

**Measured in game** (cold boot, player's save, Ablithia plain, two battles):
the graft runs once per species at each battle start; before/after of the
copy: `09 01 01 01 01 01` → `24 12 23 0C 2C 29`, MP `3 → 255`, HP unchanged;
next battle, two species, two different draws. No freeze.

### 92.4 Battle flag for probes on ROMs without the blob

`0x020F1F7C` (u32) is **0 in battle, 1 on the field** — same value in two
battle and two field savestates. The overlays in the shared slots are NOT a
battle flag: they stay loaded after the battle. `guet.lua` uses the word with
`DQ9_SANS_BLOB=1`.

## §93 How a monster picks its action, and why useless spells are never cast

Measured on September 26, 2026 (read watch on the battle copy's action slots,
then disassembly).

### 93.1 The slot picker

Each turn, `0x0208A380` (ARM9) picks one of the six slots:

- the monster's **AI type** is 3 bits of its record: `mon_moddata +0x0C`
  bits 0-2, copied to battle copy `+0x10` bits 5-7 (§92.1); a table of
  method pointers at `0x020F10B0` dispatches it (`0x0208A92C`);
- types 0, 1, 2 and 4 draw `rand_below(256)+1` against a **6-byte weight
  table** (`0x020E8CBA`, one row per type): 0 uniform `43 42 43 43 42 43`,
  1 decreasing `68 58 48 38 27 17` (281 of 438 species), 2 slot-0 heavy
  `210 29 10 4 2 1`, 4 `70 70 70 16 15 15`; type 3 (`0x0208A53C`) plays the
  slots in rotation (counter at combatant `+0x38`); types 5-7 are other
  routines, not decoded;
- the chosen slot is checked by `0x0208A04C`; if refused, the picker tries
  the lower slots, then the higher ones, and falls back to the default
  action (`0x02154A04`).

There is no seventh slot: the weight tables are fixed at six.

### 93.2 The conditions live in each action

`0x0208A04C` checks the action's MP cost (`[action+8]` low byte, 255 = all
MP) against the caster's MP, silence and similar states, then asks the
**target selector** `0x021F66CC` (overlay 24, the battle-turn overlay): the
action record's `+0x0C` / `+0x0E` (one per side) is a **target type** that
indexes a table of 0xA1 handlers (`0x021FF790`). A handler that finds no
useful target refuses the action. Read in the code:

| type | used by | condition |
|---|---|---|
| `0x0B` | Heal, Midheal, Moreheal, Fullheal | an ally below **50 %** HP (ratio against the float `0.5`) |
| `0x06` | Kamikazee, Magic Burst (monster side) | the caster's max HP ≥ 2 × current HP |
| `0x10` | Zing, Kazing | a dead ally |

Every status spell has its own type (`0x0D` Squelch, `0x0E` Tingle, `0x0F`
Cock-a-doodle-doo, `0x12`-`0x3C` one per buff/debuff and per side). A spell
drawn for a monster keeps its action record, hence its conditions. Observed in
game on the ZER-56 test ROM: monsters cast varied spells, no heal at full HP
reported.

### 93.3 MP of monsters that have spells

Over the 107 bestiary species with spells and less than 255 MP, MP is
**2 to 4.5 times the cost of their most expensive spell**, median **3**
(median 2.4 times the sum of their distinct spell costs). Only one cannot cast
its own spell (the « sorciergrif », 17 MP for Kaboom at 28). Rule kept by the
player: MP = max(original, 3 × cost of the most expensive drawn action),
capped at 255, "all MP" actions not counted.

## §94 Showing a technique on any monster

### 94.1 Where the presentation comes from

The presentation of an action is looked up **in the model's `.bact` first**,
then in **`data/bin/actdef.nsarc` → `default.bact`**, a shared script of
generic cases (`op01 [action ids...]` … `op02`), loaded by overlay 0
(`0x02165018`: the archive is read into the static buffer `0x0211E33C`, then
compiled by `0x0216D1C4`). With no case anywhere, the action runs but shows
only a camera move and no text: that is case `op01 [0]` of `default.bact`.
Spells have their own generic path and need no case.

Measured in game (test ROMs `dq9_zer57_essai1..8`, she-slimes and slimes at
9999 HP):

- Disruptive Wave added to the list of case 161 (Psyche Up): « La gluante émet
  une Perturbonde. », Psyche Up's aura, then « Tous les effets magiques
  affectant Papouz et Cie se sont dissipés. »;
- action `0xF4` added to case 934 (a generic hit): « La gluante attaque. »,
  a hit effect on the hero, « Papouz subit 20 points de dégâts. »;
- a monster's own case wins: funghouls with Sweet Breath added to case 161
  still play their own breath cloud;
- `0xEB` 40th in a list of case 934: « La gluante A charge à fond de train ! »
  then the miss message.

### 94.2 The `.bact` format, and its limits

Header `u32` × 4: command count, string pool offset, pool size, string count.
A command is `u16 op, u8 n, u8 types` (2 bits per argument: 1 int, 2 float);
**when n > 4, a word `0xFFFFFFtt` precedes the arguments and carries the
types of arguments 4..7**. Label commands (`op09 [label, x]`, `op0a [label]`)
use label numbers, not offsets, and string arguments are pool offsets, so
commands can be inserted as long as the header's count and pool offset are
rewritten. Two `op01` in a row are not a union: the first gets an empty case
(text only, no hit).

Limits measured (battle freezes on a black screen at its first frame):

| `default.bact` | result |
|---|---|
| 596 commands (vanilla), 608, 650, 662 | runs |
| 740, 818, 915, 1 088 commands | freezes |
| one `op01` list of 40 actions; two lists of 40 | runs |
| one `op01` list of 50, 60, 100, 209 actions | freezes |

So a list holds at most 40 actions (the limit is between 40 and 49), and the
file at most ~660 commands.

### 94.3 What the randomizer does (`scripts/patch_actions.py`)

The technique pool is the techniques carried by bestiary monsters plus the
characters' techniques (`0x3F..0xC9`), without spells, Attack, Defend, Flee,
items or system actions (≥ 900), and only actions whose record says who they
target (`actdt` byte 11, low nibble: 9 = the other side, 0xA = self or allies,
0xE = heal). 268 qualify; `default.bact` has room for 4 lists of the generic
hit (case 934, the original list extended to 40 and three copies of the case)
and 2 of the aura (case 161): **159 + 73 = 232 techniques**, named ones first.
650 commands.

At battle start the graft draws, for each slot marked in `mon_moddata +0x3F`,
a technique from a 1,024-bit table (one bit per action id). The code lives in
overlay 0, in the room freed by rewriting two more bit-field copies
(`0x021556D4`, 50 → 15 instructions; `0x021557C0`, 53 → 19), both proven
equivalent under unicorn (memory and live registers), a mutation test
catching all five injected faults. Measured in game (ROM `dq9_zer57_tous`,
six techniques per species): the battle loads, draws `B7 54 75 B2 4A 97`,
sets 78 MP, the monster uses `0xB2`; no freeze.

### 94.4 With the blob, the zone table does not cover the battle's species

Measured on the Balanced build (seed 42, blob): at battle start the overlay-0
loop walks the **zone** table (7 species in the Ablithia plain) and, for each,
looks it up in the battle copy table (`0x02070FE0`); the species actually in
the battle were drawn by the blob and are **not** in the zone table, so every
lookup fails and the `mon_moddata` values are never copied: **with random
encounters, monsters fight with their `mon_btldata` values** (HP, MP, stats,
actions). Two consequences:

- the graft must not depend on the `mon_moddata` copy. Masks moved to
  `mon_btldata +0x82/+0x83` (always zero in the 438 records, end padding,
  copied with the 0x84-byte battle record), and a **second site** at
  `0x02165A30` (`bl 0x02012FF4`, right after the battle copy table is built
  for every present species) walks the table (`[r5+0x400]` count in the low
  12 bits, `[r5+0x404]` records) and draws for each record, then tail-calls
  `0x02012FF4`. The first site still redraws for zone species, whose actions
  the `mon_moddata` copy overwrites. Measured: five records drawn at each of
  four battles, no freeze;
- ZER-58: `--stats` (which writes `mon_btldata`) does affect battles in
  random-encounter builds, for the blob's species; it does not for vanilla
  zone species. In vanilla the two files hold identical actions, HP and MP
  for all 438 records.

### 94.5 The battle message of an action

`actmsg.gp2` (5 members, type-1 compressed, `scripts/lz_dq9.py`) holds the
battle messages as a message table (`textes_dq9.messages`); the message
number of an action is **bits 2-11 of the u16 at `actdt` record byte 35**.
Checked: `0xEB` → 297 « charge à fond de train ! », `0xF4` → 1 « attaque. »,
`0xBD` → 202 « émet <ACTION>. », `0xE4`/`0x10A` → 81 « exhale <ACTION>. »,
`0x40` → 11 « utilise <ACTION> ! », `0x14` → 46 « lance le sort <ACTION>. ».
It tells what the 55 unnamed techniques are: attacks of ordinary monsters
(« donne des coups de griffes », « encorne … et l'envoie valdinguer »,
« déclenche un Raz-de-marée »…). Message **0x37 « demande du renfort. »** is
carried by nine actions (`0xF2`, `0x158`-`0x15B`, `0x15D`, `0x160`, `0x1D6`,
`0x1DA`): the reinforcement depends on the species, and given to another
monster nobody comes (seen in game by the player). They were first left out
of the pool; since §94.6 they are back in it (player's decision).

### 94.6 The other generic cases, seen in battle, and the full pool

Measured on September 26, 2026. One test ROM per case (`work/zer57a/c<case>.nds`,
built by `work/zer57a/voir_cas.py`): every bestiary species carries
`0x135` (« donne des coups de griffes ! ») in its six slots, 9999 HP, and
`0x135` is added to the list of ONE case. All ROMs have the same size, so a
single savestate on the Ablithia plain, taken from the player's save
(`work/dumps/z57a_plaine.State`), replays the same battle (a hammerhood,
first action around frame 7 700). A freeze shows as a battle that never
reaches its second action choice (`0x0208A9BC`) and a screen that stops
changing.

| case | what it shows (the claw misses every time, so no hit on the target) | freeze |
|---|---|---|
| 921 | scene darkens, a « ! » above the monster | no |
| 922 | golden flame aura on the monster, dark scene | no |
| 924 | — | **yes** |
| 925 | the monster flashes pink | no |
| 928, 932 | dark scene, nothing else visible | no |
| 931, 933 | close camera on the monster | no |
| 939, 942, 943 | no freeze (not looked at in detail) | no |
| 944 | the monster's strike motion | no |
| 945 | camera on the target, wrapped in a purple cloud | no |
| 242 (`0xF2`'s case), 347 (`0x15B`'s case) | the reinforcement show waits for a monster that never comes | **yes** |

930 was not measured (no encounter in that run). So a generic case can only
be used after it has been seen: three of fifteen freeze.

**Reinforcements.** The called species comes from a table in overlay 0,
`0x02182E6C`, 8 bytes per entry (`s16` action, `s16` species, `-1`,
`s16` count), 17 entries ending with action `-1` (`0x158` → 35, `0x159` →
145, …); `0xF2` and `0x1DA` are not in it (special cases, `0x0215FB9C`). The
target handler of type `0x74` (`0x021F45C8`, overlay 24) reads it through
`0x0215FB54` and refuses the action unless the called species is one of the
four species groups already loaded in the battle (`0x02162D88`,
`[battle+0xEB8]`), and unless the group has room (5, or 8 for one species).
A reinforcement of another species therefore needs its model in the battle:
a random reinforcement is a loading problem, not a data one.

**What the randomizer does now.** The pool is all 268 qualifying techniques.
The 36 that do not fit in the four lists of case 934 (ordinary monsters'
attacks, all unnamed) go by family to cases 944 (plain strike, 27), 945
(sprays and clouds: sand, vomit, ink, lick, blinding light, web; 6) and 921
(intimidation: evil eyes, funny face, piercing cry; 3); the nine
reinforcement calls go to the aura (161), never to 242. Still 650 commands.

### 94.7 Real animations, about ten per battle (`scripts/patch_animations.py`)

Measured from September 26 to October 11, 2026, and checked in game by the
player on 54 test ROMs (5 abilities each) and a full Balanced game.

**The limit of `default.bact` is a heap.** The file is compiled at battle
start (`0x0216D1C4`, called at `0x02165070`) into a frame heap (`HMRF`) whose
size is a literal of overlay 17: `0x1F7DC` bytes at `0x021B727C`, taken from
the ExpHeap `0x022A3200`. A compiled command costs about 15 bytes; once the
battle is loaded, about 900 bytes are left — hence the black screens past
~660 commands. The parent heap has 77 KB free right behind it: the literal
is raised by 16 KB (no other change). Also, the `op01` handler (`0x02169BF0`)
copies the action ids of a list into 0x40 bytes of stack: **32 ids at most**;
longer lists overflow onto saved registers.

**A foreign ability shows its real animation** when its own case (`op01 [id]
... op02`, taken from the `.bact` of a monster that has it, or from the
heroes' one-animation files `data/skill/act*.nsarc/spNNN.bact`) is copied into
`default.bact`. Of the 256 abilities of the pool, 173 come from monsters, 83 from heroes.

**Copy rules** (each one fixed a failure seen in game):

| what | rule | failure without it |
|---|---|---|
| pool strings (`op03`, `op12`, `op14`, `op15`, `op21`, `op22`, `op3b`, `op5b`, `op70`, `op75`) | re-pointed into the target pool | wrong effect, wrong path |
| `op03 [7, motion]` (the caster) | motion replaced by `attack1a` unless it is `attack1a`, `damage` or `death` (all 312 battle models have them) | the caster waits for a motion it lacks |
| `op21 [7, model]` | moved to a free slot (41+) | a hero model hooked to a monster corrupts a heap: data abort at `0x020AF260`, the ARM9 halts |
| third argument of `op15` | **never changed**: it is the name of the effect's animation (`0`, `cut_01`, `attack1a`) | the effect never ends: battle stuck after the damage, or first part of the animation missing |
| `chara/...` paths missing from NitroFS | kept: they live in `data/pack_lv5/chara_mp.gp2` | — |

**About ten per battle.** The whole archive `actdef.nsarc` is read into a
static buffer (`0x0211E33C`), so the 256 cases cannot share one file. The
randomizer writes 26 archives `rnd/aNN.nsarc` (a new root folder: no file id
moves), each holding the original `default.bact`, the cases of about ten
abilities and, after the string pool, the 128-byte draw table of those
abilities. Two hooks in overlay 0 call code placed in ARM9: `choisir`
replaces the load of the archive path (`0x02165018`) and returns the path of
a variant drawn at random; `copier` replaces the call of the compiler
(`0x02165070`), copies the variant's table over the draw table of
`patch_actions` (§94.3) and compiles. The draw that follows (§94.4) thus picks
every monster's abilities among the variant's. The code lives in the ARM9
constructor `0x02089234..0x02089348`, rewritten equivalently in 33
instructions instead of 70 (six `bic` on the same halfword make one mask),
proved under unicorn on 2,000 random objects, five injected faults caught.

**Method that found the failures**: a battle that freezes has its ARM9 halted
in the BIOS (`0xFFFF0108`); a watch on the exception vectors gives the faulting
address. A battle that is stuck still runs: the player tested ROMs with slices
of one animation removed and found the slice that blocked it. A replayed
field savestate keeps the monster actions of the ROM that made it (the zone
copy, `0x022F2D3E` for the slime): actions must be written in RAM after
loading, and the bench validated on one ability that passes and one that
freezes.

### 94.8 One draw table for spells and abilities (ZER-93, 20 October 2026)

For « Create your ROM » the spell pool had to become editable, but overlay 0
has no free space: block 3 (`0x021557C0`) was full, 212 / 212 bytes, with
two draw functions (spells: a fixed range `0x09..0x3E` minus `0x1D`;
abilities: the 1,024-bit table). Spell ids never reach the table (abilities
are `>= 0x3F`), so the spells now live in the **same table**, and one routine
draws both:

```
tire_sort:  mov r0, #0x3F    ; b tire          ids 0..0x3E
tire_tech:  mov r0, #0x3F0                     ids 0x3F..0x3EF
tire:       r5 = r0 ; loop: r0 = rand_below(r5)
            reject r0 < r5 >> 4                (0x3F for abilities)
            reject bit r0 of the table == 0    (ldrb r1, [table, r0, lsr #3])
```

Spells: bits 0..8 and `0x1D` are never set, so the bit test alone rejects
them. 17 words instead of 19, block 3 now 204 / 212. Both draws stay
uniform over their pool (rejection sampling). Proof: `patch_actions.py
--emuler` (1,500 random slot sets with a 20-spell pool; a routine without
the minimum check is caught). An empty pool with a slot drawn from it would
loop forever: `config_actions` refuses it.

**The real-animation variants copy their own table over this one at the
start of every battle** (§94.7), so each variant table carries the spell
pool too (`patch_animations.patcher(sorts=...)`), and every variant holds at
least one ability. The split into variants now depends only on the ability
pool (its CRC is the shuffle seed), so the same configuration gives the
same ROM whatever seed drew it.
