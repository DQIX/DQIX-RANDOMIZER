# 23. Scenario scripts: NPCs, dialogue and quests

## 110. Where NPCs, their placement and their dialogue live (30 October 2026)

Groundwork for a new NPC and a new quest. Everything below is read from the vanilla ROM
with the generic Nitro script reader (`treasure.lire_script`: parameter types 0 = string
offset into the data area, 1 = int, 2 = float) and checked against the player's
savestates (`banc/states/quete_*.State`).

### 110.1 Map ids and file codes

`zones.noms_zones` (from `data/map/maplist9.bin` and `mapname.gp2`) gives the file code of
every map. RAM `0x020FDD44` (u16) holds the current map id. Measured on the savestates:

| savestate | map id | code | place |
|---|---|---|---|
| `quete_5_ablithia` | 100 | `C01` | Angel Falls (FR *Ablithia*) |
| `quete_1_gluant` | 1700 | `M07` | Mount Ruinous village (FR *Pic Lata*) |
| `quete_2_orion_express` | 10100 | world map | the Starflight Express offers the Realm of the Almighty |
| `quete_4_boss_parle` | 41201 | grotto | a legacy boss |

The Realm of the Almighty is `X03` (`X03M01`-`M02`, temple `X03M03`/`M04`/`M09`); after the
ending the Starflight Express asks "Vous rendre au royaume du Tout-Puissant ?" on the world
map, so the realm is reachable on a finished save.

### 110.2 `data/scenario/<code>.npc`: the NPC list and their placement

A NARC with two Nitro scripts.

`<code>npc.bin`, opcode `0x03`, one per NPC: `[npc id, kind, comment (Shift-JIS), model,
param]`. Kind 0 = person (models `n001a`...), 1 = object or statue (no model), 2 =
special (`s00x`), 5 = event model (`z000a`, `b009a`, found in `data/event_lv5/ev*<model>.chr`).

`<code>place.bin`, per map of the town:

| opcode | params | meaning |
|---|---|---|
| `0x03` | map, npc, x, y, z, angle | default position |
| `0x05` | from (3 ints), to (3 ints), kind, map, npc [, x, y, z, angle] | position or presence over a stretch of the story |
| `0x06` | npc, x, z, x, z [, n] | walking segment |
| `0x08` | npc, angle, speed | idle facing |
| `0x0B`, `0x0E`, `0x0F`, `0x11` | | not decoded yet |

### 110.3 `data/scenario/<code><stage>0.gp2`: dialogue, one archive per story stage

Letters B..Q follow the story; `Q0` is the post-game. Members `<npc id>_<lg>.bin` are Nitro
scripts, one message per instruction, inline text with the usual tags:

| opcode | params | meaning |
|---|---|---|
| `0x01` | from, to, condition, text | plain line (`1, 99, 16` = day, `1, 99, 1, 16` = night...) |
| `0x02` | quest id, quest state, condition, text | line of a quest (`<QUEST=105>`, `<YESNO>`, `<NO>`) |

Example, Mount Ruinous NPC 21 (`M07Q0.gp2`, `021_fr.bin`): the stone collector of **quest
105** ("trouve-moi un morceau de lazarite"): offer with `<YESNO>`, return, completion. A
fetch quest of the same kind is the template for a new one.

### 110.4 Quest tables (`data/scenario/`)

| file | opcode | entry for quest 105 |
|---|---|---|
| `questidtbl.bin` | `0x68` | `105, 49` |
| `questorder3.bin` | `0x66` | `105, 1700, 21, 19, 2, 1, -1, 0, 0, 1, 0`: giver map 1700, NPC 21, from story stage 19 |
| `questcancel.bin` | `0x67` | `105, 1, 1` |

Also: `questmsg.gp2` (quest log texts), `quest_btl*.stb` (`SB2` bytecode, battle-side quest
triggers such as the chimaera feather, §80.3), `data/bin/quest_msg.bin`,
`data/event/evl_quest*.bin`. Not decoded yet.

### 110.5 Game flags

Bit field at game object `0x02108844 + 0x8C`, getter `0x0206DFC0`, setter `0x0206DF7C`
(§102.2), +11724 in each save slot.

## 111. A quest from end to end: quest 105, "D'une pierre trois coups" (30 October 2026)

Quest 105 (Mount Ruinous, NPC 21 "Pierre": show him a lazarite, an enchanted stone and an
agate of evolution, get a rusty shield) decoded through every file it touches, then checked
in RAM on the player's savestates (`quete_1_gluant`, `quete_5_ablithia`).

### 111.1 Three numbers for one quest

| number | where | quest 105 |
|---|---|---|
| internal id | `questorder3`, `questcancel`, triggers, dialogue `0x02`, state array | 105 |
| displayed number | `questidtbl.bin` (`0x68`: internal, displayed) | 49 |
| quest log text | `questmsg.gp2`/`questmsg_<lg>.bin`, opcode `0x67`, **keyed by the displayed number** | entry 49: title, summary, in-progress text, completion text |

`dbg_quest_<lg>.gp2` holds a debug copy of every quest's dialogue, one member per
internal id (`105.bin`), each line tagged with its NPC file (`M07021`).

### 111.2 Quest state

Four bits per quest at `0x02108844 + 0x2CC` (204 quests, two per byte, even id in the low
nibble). Bits 0-1 are the state, bits 2 and 3 are flags. Getter `0x0206E130`. The data
(dialogue lines `0x02`, trigger tests `0x35`-`0x3D`) do **not** write the raw value; the
comparison `0x0206475C` maps it:

| value in the data | raw | meaning |
|---|---|---|
| -1, 5 | 0 | not open yet |
| 3 | 1 | can be offered |
| 0 | 2 | in progress |
| 2 | 3 | completed |
| 1 | bit `0x4` | flag (meaning not settled) |

Measured on both savestates: quest 105 raw 1 (never taken), quest 6 raw 3 (done).

### 111.3 `questorder3.bin`: when the quest opens

Opcode `0x66`, handler `0x02094D98` (command table `0x020F1444`, read on every map load by
`0x02095588`):

`quest, map, npc, story_a, story_b, flag, prerequisite, f1, f2, f3, f4 [, trigger tests...]`

- the entry only counts on `map` (event maps `0xC3B5`-`0xC4E5` excepted);
- `story_a*100 + story_b` must be <= the story progress (`0x02109404` +3, +4);
- `prerequisite` >= 0: that quest must be completed (raw 3);
- trailing parameters are extra test nodes in the trigger grammar below (e.g.
  `0x00310008, 15` on quests 31 and 35).

Quest 105: `105, 1700, 21, 19, 2, 1, -1, 0, 0, 1, 0`: Mount Ruinous, NPC 21, from story
stage 19.2, no prerequisite. `questcancel.bin` (`0x67`): `105, 1, 1`, not decoded.

### 111.4 `data/scenario/trigger<code>.bin`: the quest logic

The condition numbers of the dialogue lines (193, 194, 195...) are not built into the code:
they are set by the map's trigger file. That file is also where the quest checks items,
accepts, completes, gives and takes. Loader `0x0206462C`; triggers live in a list at
`0x02108844 + 0x47C`.

It is a generic Nitro script (§110.2). Each instruction `0x01` is a trigger, handler
`0x0205F9DC`:

`map, from_a, from_b, to_a, to_b, kind, node, node, ...`

- `map` must be the current map (`0x02108844 + 0x484`);
- `from_a*1000 + from_b <= story <= to_a*1000 + to_b`;
- `kind` 0 = evaluated when the player talks, before the line is picked (sets the NPC's
  dialogue condition); 1 = after the line is spoken (accept, finish, give, take); 11 = after
  an event, test `0x08` (event id); 15 = after a battle is WON, test `0x0C` (battle
  number, measured §112); 3, 16 = not settled.

**Node encoding.** Every parameter is a u32 read as two halfwords, **high half first**:
`0x00370015` gives `0x37, 0x15`. The first halfword of a node is its opcode, and the node
takes `ARITE[op]` u32 parameters (padding included). An opcode below `0x64` (or from `0x1F4`)
is a **test**; all tests of a trigger must be true (evaluator `0x0205FB04`, 100-case switch,
nodes of 0x10 bytes, next at `+0xC`). From `0x64` it is an **action** (executor
`0x02061C14`, nodes of 0x1C bytes, next at `+0x14`; opcodes `0x72`-`0x7C` are queued by
`0x0206446C` and run by `0x0206F834`).

The arity table was **measured by running the game's own parser** (`0x0205EC80`) under
unicorn, one opcode at a time. Proof: `scripts/declencheurs.py --tout` consumes all 76
trigger files exactly, no parameter short or left over. Opcode `0x45` could not be measured
(unmapped read) and is not used by any file. RAM nodes dumped by
`scripts/lua/quete_noeuds.lua` on `quete_1_gluant` are halfword for halfword the decoded
file.

| opcode | args | meaning | evidence |
|---|---|---|---|
| test `0x06` | npc | NPC talked to == npc (context +0) | `0x0205FDEC` |
| test `0x07`-`0x0C` | v | context field +4...+0x18 == v; `0x0B` = condition of the line just spoken (+0x14) | handlers |
| test `0x08` | event | the event that just ended (kind 11) | usage |
| test `0x10` | n | answer to the last choice == n (0 = yes / accept) | `0x0205FF0C` |
| test `0x12` / `0x13` | item | has / does not have the item (bag count > 0, `0x02086AFC`) | `0x0205FF54` |
| test `0x14` / `0x16` | quest | quest raw 2 (in progress) / raw 3 (done) | `0x0205FF94`, `0x02060000` |
| test `0x35` | npc, quest, state, line, answer | `0x06` + state + `0x0B` + `0x10` | `0x02060C8C` |
| test `0x36` | npc, quest, state, item | `0x06` + state + `0x12` | `0x02060D34` |
| test `0x37` | npc, quest, state | `0x06` + state | `0x02060DAC` |
| test `0x57` | 1 / 0 | quest log full (8 active quests) / not full | `0x020617E4` |
| action `0x72` / `0x73` | item | give / take ONE (count forced to 1) | `0x020622D4`, `0x0206FCD0` |
| action `0x74` / `0x75` | item, count | give / take `count`; taking empties the bag first, then the party's inventories | `0x0206FD84` |
| action `0x76` | npc, cond | NPC's dialogue condition := cond (0 = default line) | usage |
| action `0x77` | event | plays event `ev<event>` (ids of `data/event/evl_quest.bin`) | usage |
| action `0x7D` | quest | accept the quest | `0x02062368` |
| action `0x7F` | quest | complete the quest | usage |

The first matching trigger of a kind wins, in file order.

### 111.5 Quest 105, assembled

`triggerM07.bin`, map 1700, story 19.1-19.99:

| kind | tests | actions |
|---|---|---|
| 0 | NPC 21, quest 105 offerable, log full | NPC 21 condition := 0 |
| 0 | NPC 21, quest 105 offerable, log not full | NPC 21 condition := 195 |
| 1 | NPC 21, quest 105 offerable, line 195, answer 0 | accept quest 105 |
| 0 | NPC 21, quest 105 in progress, has `0x5660` lazarite, has `0x5641` enchanted stone, has `0x565F` agate of evolution | NPC 21 condition := 193 |
| 1 | NPC 21, quest 105 in progress, line 193, answer 0 | complete quest 105, give `0x5211` rusty shield |
| 0 | NPC 21, quest 105 in progress, has one of the three stones (three triggers) | NPC 21 condition := 194 |

and `M07Q0.gp2/021_<lg>.bin` holds the matching lines (`0x02`: quest, state, condition):

| line | when | text |
|---|---|---|
| `105, 3, 16` | offerable, log full (condition 0 = default 16) | offer, then "come back when you have fewer quests" |
| `105, 3, 195` | offerable | offer, `<UKEYAME>` accept / refuse, `<QUEST_SE>` accepted |
| `105, 0, 16` | in progress, nothing yet | reminder |
| `105, 0, 194` | in progress, some of the stones | "a good start" |
| `105, 0, 193` | in progress, all three | `<YESNO>` show them, reward text, `<QUEST_HAN>` |
| `105, 2, 16` | completed | after-quest line |

Pierre only looks at the stones: nothing is taken. The **take** pattern is the same kind-1
trigger with `0x73`/`0x75`; in Angel Falls itself (`triggerC01.bin`, map 117, NPC 70,
quest 6): *line 192, answer 0 -> complete quest 6, take medicinal herb, strong medicine and
moonwort bulb, give a coin of Ouadi*. `scripts/declencheurs.py <code>` prints any map.

### 111.6 Recipe for a new fetch quest

1. a quest id and a displayed number (`questidtbl`), a `questmsg` entry, a `questorder3`
   entry (map, NPC, story stage) and a `questcancel` entry;
2. the NPC's lines in `<code>Q0.gp2/<npc>_<lg>.bin`: `0x02` lines for states 3, 0, 2 with
   conditions of our own (192-218 are used by vanilla files, per map);
3. in `trigger<code>.bin`: kind-0 triggers that set the conditions (offer, all items, some
   items), kind-1 triggers that accept, take (`0x73`/`0x75`), give (`0x72`/`0x74`) and
   complete.

Not tested in game yet: no new quest has been written.

### 111.7 Writing scenario files: scripts, archives, a new NPC (30 October 2026)

- **Nitro scripts** (`scripts/nitro_script.py`): header, instructions, then the string
  section. The code is padded with `0xFF` to 16 bytes and has **no terminator** (a 48-byte
  code is followed directly by the data); unused type bits are 0. Writing back what was read
  gives the same bytes on **1,178 of 1,178** files (all triggers, NPC lists and placements,
  four dialogue archives).
- **GPC2 archives with new members** (`gp2_ecrire.ajouter`): the name hash is **CRC32**
  (checked on every name of C01B0, C01Q0, M07Q0, itemname); the index is sorted by hash; the
  high bytes of the offset and size fields carry the **offset of the name in the name table**
  (`itemname_en.nat` at 16, right after `itemname_de.nat\0`), not a tree; the header's bits
  12-15 hold `floor(log2 n) + 1`. Dialogue archives store their index compressed (type 2);
  we write it raw (type 0), like 1,243 of the game's archives. **Measured in game**: with
  `C01Q0.gp2` rebuilt this way, the Angel Falls priest talks and saves normally.
- **A new NPC**: one `0x03` line in `<code>npc.bin` (id, kind, comment, model, param), one
  `0x03` (map, id, x, y, z, angle) and one `0x08` (id, angle, speed) in `<code>place.bin`, a
  member `<id>_<lg>.bin` in each stage archive `<code>?0.gp2`. Kind 5 uses an event model
  (`z000a` = the Mount Ruinous slime, `data/event_lv5/ev01000z000a.chr`); `n0xxg` models
  are ghosts.
- **Game flags** from triggers: test `0x00` set / `0x01` clear, action `0x64` set / `0x65`
  clear, bit field at `0x02108844 + 0x8C` up to the quest states (`+0x2CC`): 4,608 flags.
  Triggers cite 0x000-0x1DF; the player's finished save has 0x1E0 set (by an event) and
  0x1E8-0x1FF clear. Test `0x30` = has at least *n* of an item, laid out **(item, 0, n)**
  (`triggerC01`, map 114: `[22015, 0, 3]`), whereas actions `0x74`/`0x75` are (item, n, 0).
  Writing `0x30` as (item, n, 0) reads "at least 0": always true (first in-game try).
- **Item names live twice.** `itemname.gp2` is not enough: the key-item menu shows the name
  from the item records of `itemdt.gp2` (and `itemdt_t.gp2`): 32-byte records from `+0x10`
  (count in the low 12 bits of `+0x00`), record `+0x00` = offset of the (singular) name in
  a string pool that ends the member, pool length at member `+0x08`. Renaming only
  `itemname` left "permis de conduire" on screen; `patch_pages.py` writes all three.
- **The item icon** is the reference at record `+0x0C`: category letter << 20, then
  id % 1000 twice on 10 bits (permit `0x0692C4B1`). The debug stones have no image
  behind theirs. **The description** also lives twice: `itemexpl.gp2` and the identical
  `itemexpl_<lg>` member of `iteminfo_<lg>.gp2`, which is the one shown.
- **When an NPC appears**: see §111.8 (read in the code).
- **Celestria** already exists in the post-game temple: NPC 6, model `s061`, map 4304; she
  only speaks for quest 198.

### 111.8 How `<code>place.bin` is read (30 October 2026, from the code)

Overlay 17 (`0x021A2D38`) walks the members of `data/scenario/<code>.npc`; the one
whose name contains `place.bin` goes to `0x0206DA90` with the story (a, b, c from
`0x020107AC/E0/0x02010814`) and the current map. That function fills a context at
`0x02108CEC` (`+0` c, `+1` b, `+2` a, `+0x0A` entry counter, `+0x0C` map, `+0x10`
NPC list) and runs the script with the handler table at `0x020F0994` (op, handler):

| op | handler | effect |
|---|---|---|
| `0x03` (map, id[, x, y, z, angle[, ...]]) | `0x0206C020` | if map = current map: create the entry and add it to the list (`0x0206DB58`); with fewer than 3 parameters, **remove** the NPC (`0x0206DD78`, unlink by id) |
| `0x05` (a, b, c, a', b', c', *k*, map, id[, x, y, z, angle]) | `0x0206C2D0` | applies only if `a*1000+b*10+c` <= story <= `a'*1000+b'*10+c'`, and by *k*: 0 when `[game+0x3DC]` != 0, 1 when it is 0, 2 always. Then: map != current map → **remove** the NPC; no coordinates (fewer than 10 parameters) → **remove**; else a new entry at those coordinates |
| `0x08`, `0x0B` | `0x0206C704`, `0x0206CA4C` | modify the entry the previous `0x03`/`0x05` created (matched by the entry counter, `+0x44`); `0x0B` ORs its values into the entry's flags (`+0x0C`) |

So a short `0x05` means *absent then*. The game's ghosts (Stornway NPCs 26 and 27) carry
`0x05 (2.7.1-19.9.99, k = 0)` and are absent when `[game+0x3DC]` != 0, i.e. by day:
they are night-only through their data, not their model. Our ghost with *k* = 2 was
removed always (essay 5); without any `0x05` it stays (`scripts/simu_place.py`: present
in both cases, 14/15 NPCs on map 100). NPC ids are bytes (`strb`): at most 255.

**At most 10 NPC models per map (measured in play).** Stornway outside (map 100) loads
exactly 10 distinct models after the story, by day and by night. Our ghost (`n005g`,
shared at night with ghost 26, which is absent by day) made 11 by day: NPC 1 (`n002a`)
lost its model — invisible, yet it still answers when spoken to. The same ROM with the
ghost on `n005a` (already loaded by day by NPC 213) shows NPC 1 again. Where the cap
lives in the code was not looked for. Rule for new NPCs: count the distinct models the
map shows at that moment (`scripts/simu_place.py`, day and night) and stay at 10.
## 112. A new boss and a new NPC model (30 October 2026, ZER-116)

**A free species.** Index 437 of `mon_btldata` (id 900, 32,000 HP, no name, model `z060c`,
the unused "Sacksquatch") is cited by no encounter table nor `eventbattle` record, and no
other species uses `z060c`. A new boss can live there without replacing anyone.

**`mon_data_<lg>.nat` +0x02** is the string pool size / 16 (English: 8,784 bytes -> 549). A
name appended past that bound is not read (the debug viewer shows an empty name): pad the
pool to 16 and update the field. **`mon_list_<lg>.nat`** (`mon_list.gp2`) is the bestiary
list: 345 records of 32 bytes (+0x04 model code offset, +0x08 name offset, +0x0C species,
species 1-514 only), pool right after the records, +0x02 = pool / 16 too.

**NARC header.** The game writes `fe ff 00 01` at +4 (BOM 0xFFFE, version 1.0); ndspy writes
`ff fe 01 00`. A `.mon` rebuilt by ndspy froze the debug viewer on open, even the original
`z060c.mon` read and rewritten unchanged.

**Debug menu (EUR).** The Action Replay codes `12000EC8 00001001` and `12000EF0 00001000`
turn two `mov r1,#6` before the call `0x0200FBA4` into `#1` and `#0`: the game boots into a
"XENLON project ver035 Apr 14 2010" screen, then a menu (Debug, Start, Create, Delete,
Title, Chara Viewer, Movie). Chara Viewer > Load > Monster lists `data/bin/charaview4.bin`
(tagged table, category 6 = monster, field 1 = species, Shift-JIS labels; species 900 is
first, "サンドバッグくん"). The viewer code is overlay 15. Animations play with R+A.

**NPC models (kind 2, `data/chara_sub/<model>.chr`).**
- A model in a subfolder (`z/zenus`) does not show; the same content under a root name does.
  A file added at the end of `chara_sub` shifts the ids of everything after it: the game
  opens files by path, so this is safe once every later folder's `firstID` is bumped
  (ndspy does not do it). Checked: 7,508 files read back identical by path.
- The idle NPC plays its **`stand.nsbca`** (a zoomed A/B shows the same `cut10suwal` pose
  with or without `walk.nsbca` in the file, and a different one with the original
  `stand`). A first reading "it plays `walk`" came from comparing screenshots too small to
  tell: zoom in before concluding. Seen from the game's high camera, the cutscene "sit"
  pose `cut10suwal` reads as standing with arms spread. Members are found by extension
  (arm9 strings `.nsbmd .nsbca ... .bcfg %s.%s`), not by the model name.
- A town's NPC list is read when the town is entered: moving between two maps of the same
  town (4303 -> 4302 -> 4303) does not show an added NPC.

**Hero position in RAM** (field): `0x022CD2E0` x, y, z (fx32), `0x022CD2F0` angle (fx32
radians, pi = facing -z). Measured by RAM diffs over four steps (`scripts/lua/pos_heros.lua`).
Throne room of the Temple of the Almighty (map 4303): hero stops at z = -7.44 against the
throne, floor y = 1.143.

**Events.** `data/event/evNNNNN.gp2` (523) hold a `.stb` script in the SB2 format and the
texts in five languages; trigger op `0x77(N)` plays `evN`. `eventbattle` field 0 is a
battle number (0-140, unique; Aquila 131, cutscene Corvus 135). SB2 is not decoded: no
opcode carries the battle numbers in clear, and no dialogue tag starts a battle.

**Launching a scripted battle: trigger action `0x78(n)` (CONFIRMED, 30 October 2026).**
- **Static.** The action runner `0x0206F834` dispatches `op - 0x72` through a jump table at
  `0x0206F8B0`; case 6 (`0x78`) is `0x0206FBCC`. It fills a 0x18-byte battle request on
  the stack (`+0` = 1, `+2` = `0xFFFF`, `+4` = `n + 5 + 0x8000`, `+8` = `n`, the parameter
  halfword `[node + 2]`) and hands it to overlay 17 `0x021B7104`, which copies request
  `+8` into the battle object's `+0x28`. The builder `0x021B7284` (caller `0x021B798C`) then
  reads `[obj + 0x28]` (`< 0` = ordinary battle) and looks the record up by field 0
  (`0x02074124`, only ever called from overlay 17). `0x021B848C` can overwrite `+0x28`
  later with its 4th stack argument (seen with 34 on a grotto boss).
- **In the game files.** 66 triggers use `0x78`, always with an `eventbattle` number: after
  an event (kind 11, e.g. `08[28800] ; ... ; 78[131]` = Aquila), or straight after a line
  of dialogue (kind 1, e.g. `06[104] ; 0B[192] ; 78[33]`, a grotto boss).
- **Measured** (`combat_lance.lua` on `quete_1_gluant`, the Mount Ruinous slime's trigger
  rewritten in RAM): `0x78(131)` starts the Aquila battle as soon as the slime is spoken
  to, and the game returns to the field afterwards. A **new record** appended to
  `eventbattle.bin` (`144, 900, 1, -1, 0, -1, 0, 24, 0`) is found the same way:
  `0x78(144)` starts a battle against species 900. With the secret boss model, name and
  declared size of `work/boss_secret/s060/zenus_mon.py`, the screen shows "[boss]
  s'approche !", the model, damage taken, and "[boss] attaque." on its turns (32,000 HP).
  Builder: `work/zenus_combat/combat_zenus.py`.
- **`0x8E` is NOT settled** (correction of an earlier reading). The RAM test that
  "refuted" it never ran it: the action node written at `0x023026B4` was not linked, since
  the list's only node (`0x023026A4`) has its next pointer at **+0x14** (`0x023026B8`),
  which was 0. The attitude learned came from event `0xCFB6` itself.
- Trigger nodes can be rewritten in RAM after loading a savestate (`DQ9_POKE` in
  `combat_lance.lua`): list at `0x02108844 + 0x47C` (`scripts/lua/quete_noeuds.lua`), test
  nodes 0x10 bytes (next at +0xC), action nodes 0x1C bytes (next at +0x14). **Replace a
  linked node; a node written next to it is not run.**

**The FAT is cached in RAM** (EUR: `0x023BB100`, 7,543 entries of start/end, a copy of the
ROM's FAT made at boot). A savestate keeps the FAT of ITS ROM: loaded under a ROM where a
file grew, the game reads the old bounds. Measured: `eventbattle.bin` grown from 4,336 to
4,384 bytes, the cached end still 4,336, record 144 read truncated: a nameless, invisible
monster that "disparaît" on its first turn. Rewriting the differing FAT entries in RAM
right after loading (`work/zenus_combat/fat_pokes.py <rom of the state> <rom tested>` ->
`DQ9_POKE`) makes the savestate usable even when 36 files moved (the secret boss model grows
`enemy.gp2` by 6.5 KB). Not a cure for everything: data the game already holds in RAM
(model heap, loaded tables) stays the old one. **The overlay table is cached too**: an
overlay that grew (the page-drop graft appends 88 bytes to overlay 23) is loaded at its old
size, and the game freezes at the end of EVERY battle (witnesses: same savestate, vanilla
bench ROM wins battle 26 and returns to the field; the modified ROM freezes; with overlay 23
left vanilla, it does not). Bench ROMs keep the savestate's code identical.

**After the battle: victory, defeat, retry (measured 30 October 2026, bench ROM
`work/zenus_combat/banc_combat.py --allee`, the slime moved to the throne aisle of map
4303 and its item tests removed, savestate `quete_2_orion_express` + `DQ9_FAT`).**
- A trigger of **kind 15** runs on the map after a battle is **won**; test `0x0C(n)` = the
  battle number (the game: `15: 0C[33] ; 82[...]` after grotto boss 33). Measured: the secret boss
  at 1 HP beaten, back on the field the kind-15 trigger `0C[144] ; 01[0x1FE] ; 64[0x1FE]`
  sets the flag (byte `0x0210890F` 0x20 -> 0x60).
- **Defeat**: the party wakes at the last church (map 109, Ablithia, for that save), no
  freeze, flags untouched (`0x1FD` set at the "yes" stays, `0x1FE` stays clear).
- Hence the quest with a battle (`zenus_royaume.declencheurs(combat)`): "yes" takes the
  stone and pages, sets `0x1FD`, launches the battle; victory sets `0x1FE`; with `0x1FD`
  and not `0x1FE`, the slime offers to go back (line 203, "yes" -> `0x78` again). Each
  branch was played on the bench: the dialogue, the battle, the flags.
- Species 900 as the secret boss: Nokturnus' resistances, experience (74,600) and gold (2,490), and
  his level-99 stats (the game scales legacy bosses by level at run time; Dragon Quest
  Wiki gives Nokturnus base 8,250 HP / 780 att / 610 def / 350 agi and level 99
  16,572 / 1,567 / 915 / 560; this ROM has 700 attack, so 1,406). Beaten, he gives the
  experience: "Athore passe au niv. 76".

**The empty world (31 October 2026, `scripts/patch_monde_vide.py`).** After the secret boss is
beaten (flag `0x1FE`), no NPC and no monster anywhere. Two ARM9 relays of 28 bytes, read
the flag at a fixed address (`0x02108844 + 0x8C + flag/8`, bit `flag & 7`):
- **NPCs**: overlay 17 `0x021A2D94` calls `0x0206DA90` (the `place.bin` runner); its 5th
  argument (`[sp]` at the call) is the current map. The relay writes 0xFFFF there: the
  runner still resets the list, no `0x03` matches. Measured on a cold boot of the player's
  save (Ablithia church, map 109) with the relay keyed to `0x1E0` (set in that save): no
  priest, no dialogue; keyed to `0x1FE` (clear): the priest opens his menu.
- **Monsters**: the field tick (ARM9 `0x02073C48`) and the overlay-17 fallback
  (`0x021A24B0`, Whistle, spawns without a species) both get the group table from
  `0x02073ED4` and give up when it is 0. The relay returns 0. Measured (`combat_lance.lua
  DQ9_ENTREES`, savestate `quete_3_combat_fin`, 4,000 frames after the battle): witness
  131 calls of the chooser (`0x02073CA0`) and 131 spawns (`0x021A2128`); with the relay
  injected in RAM, 0 and 0. Screenshots could not tell (the harness sees few monsters).
- Space: the first free 28-byte slots among regions the project validated (tail of the
  rewritten chooser, `0x020F1E40`, `0x020E7C78`, `0x020E8888`), whichever this build's
  options left blank. `0x020F1CB8` (written at run time by the blob) and `0x020F1D2C`
  (`patch_place`) are never taken.
- **The Starflight Express keeps its NPCs** (31 October 2026). Leaving the realm means
  walking back into the Express (map 6401, `S14M01`, "Carriage 1") and using the dashboard,
  the modelless NPC 106 of `S14.npc`: that is the "!" prompt (not Stella, corrected in §113.15).
  The first relay emptied every map, the train included, and the player was stuck in the realm. The NPC relay (44 bytes)
  now leaves maps 6400-6405 alone. Measured with both relays injected in RAM on
  `quete_2_orion_express`, flag `0x1FE` set (`work/monde_vide/arrivee.lua`): realm 0 NPCs
  created, train 8; with the old relay, train 0. The realm's modelless NPCs (X03 1-5,
  200-202) are inscriptions, the temple door and statues, not Express points.

**Stella's presence: action `0xA2`, flag `0x113B`.** Handler `0x020630A4`: `A2(v)` sets
game flag `0x113B` to 1 when v = 0 and clears it when v = 1. The game runs `A2(0)` when
Stella leaves (after the ending on map 20207, story 14.4, 4.7-5.1) and `A2(1)` when she
comes back, including at the end of quest 039 "The phantom fish" (internal 201,
`questidtbl` `201, 39`; event `0x72DA` on map 6401). Measured: with `0x113B` set (byte
`0x02108AF7` bit 3), Stella is gone from the battle records screen (she normally stands on
the right and talks) but she still stands in Carriage 1.

**The save event `ev29320` is the epilogue.** `data/evspt_lv5/ev29320.gp2` (playable by
trigger `0x77(29320)`, like the other `evspt_lv5` events) asks "Voulez-vous sauvegarder les
faits marquants...?", saves ("Sauvegarde du journal réussie"), then plays the post-credits
scene (map 20207). Not usable as a plain save. The alchemy pot saves from its own code
(overlay 6, `0x0215D370`-`0x0215D488`, `str_ren` messages 24, 54, 55): state 0xE calls
`0x020A9EB4(ctx + 0x3C)`, state 0xF calls `0x020AAD2C(ctx + 0x3C, 0x0211E33C, 8 or 0x14,
0)` every frame until it returns 1, around `0x0202F7A8/7D8/7B8/7F8`.

**No save tag.** Saving only goes through the church menu, opened by the text tag
`<ADD><CHURCH=n>` at the end of a priest's line (n = 1-7, the priest's manner; 210 uses of
1). The engine's tag table (ARM9 `0x020F0600`-`0x020F0C00`) has no save command
(`<INN=n>`, `<SHOP=n>`, `<BANK>`... but no `SAVE`).

**Showing / hiding an NPC (not measured).** Trigger actions `0x95(a, b)` and `0x96(a, b)`
(handlers `0x02062D90`, `0x02062E0C`) are mirror images: `0x0206EA9C(ctx, a, b + 0x80,
1/0)` then `(ctx, a, b, 0/1)`, or `0x02013390(a, 0/1)`. Grotto maps use them in kind-20
triggers (`09[map] ; ... ; 95[0, 12, 0] ; 96[0, 11, 0]`), probably "on map load": hide
or show NPC b. Which is which is to measure.

## 113. Saving without a question, NPCs on flags, monster turns (31 October 2026, ZER-116)

All measured on the bench (`zc_ba1`, `quete_2_orion_express`, then cold boots of a save
written in the realm), scripts in `scripts/patch_sauvegarde.py`, `scripts/zenus_royaume.py`,
`work/zenus_combat/`.

### 113.1 The church facility and its manners

A line ending in `<ADD><CHURCH=n>` opens the church after the text (facility list parsed
by `0x0206F588`, table `0x020F0AFC` + 4k: 1 INN, 2 CHURCH, 3 BANK, 4 SHOP, ...; dispatch
`0x0206F6DC`, church = overlay 17 `0x021BA8E0`, process in **overlay 3**). The manner is
`n - 1` (church object `+0x5A0`) and picks the message file `data/scenario/str_ch<m>.gp2`
(`str_ch%d_<LG>.nat`). Text uses: `<CHURCH=1>` 210, `=2` 40, `=3` 1, `=4` 12, `=5` 12,
`=6` 57, `=7` 10, **`=8` and `=9` never**.

- **Manner 2 (`<CHURCH=3>`) is the prologue's journal on the table** (M01 NPC 217, no
  model, line = the tag alone). It sets `+0x5B4` (save without the priest's menu) and
  goes straight to the confession, *before* the speaker's line is shown: from an NPC
  with text, the text is never displayed. Its message 1000 is the question ("Le journal
  est ouvert sur la table. Voulez-vous enregistrer votre aventure ?<YESNO>"), shown
  joined to message 100 (`<YES>Sauvegarde du journal en cours...<ADD>\n<NO><CLOSE>`), and
  confession state 2 waits for the answer (window `+0x9A0` 6 then 5, choice 0): without
  `<YESNO>` it waits forever.
- Opening sequence (overlay 3, `+0x580` sub-state): state 3 loads, then (journal) jumps
  to the confession at `0x021599D4`, or (priest) state 4 waits for the NPC's line to end
  (`[window+0x9A0] == 3`) before the menu.
- **Kind-12 triggers run inside the church save**, just before writing (`0x02159F58`,
  `0x020649C0(mgr, 12, ...)` then the action queue): what they give or set is in the
  save. Tests on the talk context (NPC, line, answer) fail there; flags and items work.
  Kind-1 triggers do **not** run after a line that opens a facility.
- `.nat` of `str_ch<m>`: `u32 (pool size << 12) | count`, then `count` pairs (id,
  offset), entry 0 = (0, 0), pool of zero-terminated strings (1010 and 1016 share one).
- Save sequence (any church): `0x020A9EB4(work)` then `0x020AAD2C(work, 0x0211E33C,
  mode, 0)` each frame until 1 (8-byte work; mode 1|0x14 church, 8|0x14 alchemy pot).

**The forced save** (`patch_sauvegarde.py`): manner 8 (`<CHURCH=9>`), a new
`str_ch8.gp2` (journal messages with 1000 empty, 100 = "en cours" and 1011 = "réussie"
taken from `ev29320`, five languages) and two overlay-3 sites: `0x02159A24` (state 4,
line finished) → a 28-byte relay at `0x02180C84` (overlay tail; `0x02180C80` ends the
"\n" string at `0x02180C7F`) that sets `+0x5B4` for manner 8 and reuses the game's
"go to confession" at `0x021599DC`; `0x02159EDC` tests `manner != 2` instead of
`+0x5B4 == 0` (identical for the game, manner 8 no longer waits). Measured cold on the
final ROM: line, YES, the gift lines, "Sauvegarde du journal en cours", "réussie", back
on the field; NO: "tant pis", nothing. Cold boot of the written save: flag set, items
taken; witness (save before): church 109, flag clear.

### 113.2 Showing an NPC on flags: `place.bin` op `0x11`

Handler `0x0206D4F0`. Odd parameter count: pairs `(type << 16 | flag, wanted)`, then
moment (2 = always), map, id, x, y, z, angle; even count: the same plus one trailing
value. Type 1 = scenario flag (`0x0206DFC0`), type 2 = another bitfield (`0x0206EBA8`).
Any pair that does not match → the NPC is not created. 534 uses in the game. Measured:
the secret boss (`0x11 [(1:0x1FD)=1, (1:0x1FE)=0, 2, 4303, 8, ...]`) absent before the gift,
present after a map change **inside the same town** (4303 → 4302 → 4303) or a cold
boot, gone after the victory.

Not for NPCs: trigger actions `0x95`/`0x96` (kind 20, map load) set and clear bits of a
map-object bitmap (`ctx + 0x41B`, two banks of 32 bytes; `0x0206EA9C`), measured with
no effect on NPC 8 while the kind-20 trigger itself ran (witness flag set). `0x15` is
the same placement keyed on a **quest** state (`0x0206E130`).

Other ops read: `0x08 (id, angle, r)` is a **patrol**, not a scale: movement type
`+0x1F = 8` between two points at ±r along the angle (`0x0206C704`); without it the NPC
stands still. The gluant and the first secret boss moved because of it.

### 113.3 Save file offsets (per 32 KB slot, three CRC32 of §103)

Scenario flags at `+11724` (= RAM `0x02108844 + 0x8C`; flag `0x1FE` = `+11787` bit 6,
found by diffing a save before and after the gift); resume map u16 at `+11476` (a
church save resumes at that map's entrance); common items: ids `+7664` (u16 ×152,
**empty = 0xFFFF**), counts `+7968`.

### 113.4 Monster turns and size: what did NOT work

- `mon_moddata +0x0C` holds seven bit fields (unpacked at overlay 0 `0x02165AB0..`):
  AI 0-2, 3-8, **9-11**, 12-13, 14-16, 17-19, 20-21. Bits 9-11 are 0 for 287 species, 2
  for story and legacy bosses, 3 for grotto bosses and legacy levels 2-3; they index an
  8-byte table (`0x0215F57C`, values `0 ? 1 2 ...`). Setting 3 on the secret boss: **one** action
  per turn, measured by counting the picker `0x0208A380` (0, 1, 1, 1 over four turns)
  and once "Totalement subjugué, [boss] observe ..." (a lost turn). Not the number of
  actions.
- Every legacy boss carries one action with no name, no message, no case, type "self",
  effect 7 and a u16 at fiche `+50` (Nokturnus `0x31C` → `0x301`, Corvus `0x25B` →
  `0x2EF`...): probably what makes them act again (§91 saw Corvus' "seem to act twice");
  the u16 indexes no action fiche. Not decoded.
- Model size: `pos_scale` (MDL0 info `+0x1C`/`+0x20`) and the box scale (`+0x38`) ×1.35
  change **nothing** in battle (same pixels, cold boot), although the SBC has `0x0B`.
  `mon_btldata +0x27..+0x29` (`10 02 04` for Nokturnus and Aquila, `00 00 00` for the
  unused species 900) copied: no visible change either. Nokturnus' box is 52 × 40,
  the secret boss's 32 × 30 (s060).

### 113.5 Party commands and the party AI (31 October 2026, measured on the bench)

The "charm" of ZER-116 (a companion acts on its own against its own party). EUR addresses,
battle `b33_24.State` (`dq9_ch_33.nds`, the secret boss reduced to "Attack").

- **Command of a party member**: `*(actor + 0x19C)` (`0x02053DD0`), an array at
  `0x02397178`, 12 bytes per party index (actor `+4`; here Papouz 0, Athore 1,
  Melchior 2, Freyja 3). Bytes: `u16` action, `u8` **target actor id**, `u8` group.
  Party ids are 0-3, monster ids start at `0xC0`; the group is 0 for the party.
  Measured: the hero's "Attack" on the secret boss = `01 00 C0 00`; Freyja's *Sun eruption*
  (all enemies) = `BB 00 00 00`. Menu writer: overlay 0 `0x021699A4`
  (target in `0..3` → group 0, id = index; monster → group `[ui+0x1D]` through the
  tables at `+0x4D1C`/`+0x4D3C`).
- **Turn queue**: entries of `0x28` bytes from `0x023399CC` (in turn order, not by
  index). `+0` = the action (`u16`), no target. The AI writes the action to both.
- **Party AI**: the pre-check `0x021F9030` (overlay 24) runs for each member; then
  overlay 0 `0x021578A0` calls the tactic dispatcher `0x021F8F20` (r0 AI context,
  r2 = index, r3 = queue entry; only when the entry's action is 1) which calls the
  tactic routine through a table (`0x021F8144` = Ruthless …); the best candidate
  (12 bytes: action, score `+4`, group `+0xA`, target `+0xB`) is copied by
  `0x021F691C`; the fallback `0x021F8628` attacks a monster (`01 00 C0+n g`).
  The dispatcher returns at `0x021F9020`. All decisions happen in 3 frames when the
  last command is entered; the frame after, the action is compiled for execution
  (`0x021540F4`, `0x021EAAAC`): a later write to the command or the queue is ignored.
- **Retargeting works**: written at `0x021F9020` for Freyja (`r7 = 3`), command
  `01 00 02 00` + queue `01 00`: "Freyja attacks twice in a row", "Melchior takes
  42 damage", next turn normal, **no freeze**. With *Sun eruption* kept and the
  target set to `02`: the spell still hits the monster side (an area action ignores
  the target id).
- **Swapping the side lists freezes**, twice: during the whole AI pass (the dispatcher
  is then never called, Freyja keeps the menu's `01 00 00 00`), and narrowed to the
  dispatcher call only (the AI still picks *Sun eruption*, which hits the secret boss, then a
  freeze during the hit). Dead end; do not retry without a new idea.
- **The charm rule, measured on the three companions** (`etat_macro.lua` `DQ9_REDIR`,
  `work/zenus_charme/banc_charme.py r1|r2|r3`): at `0x021F9020` for the charmed index
  (`r4` = actor, `r6` = queue entry), an action on ONE monster (target id ≥ `0xC0`) keeps
  its action and gets a random target among the three other members (group 0); any other
  action becomes Attack (`1`) on one of them. Melchior: *Sizz* (`0x0A`) on Athore, 43
  damage; Athore: *Sizzle* (`0x0B`) on Melchior, 68 damage, 18 MP; Freyja: *Sun eruption*
  turned into Attack on Athore, 37 damage. MP are spent; no freeze; next turn normal.

### 113.6 The charm graft: menu skip, forced tactic, rule B, pose (31 October 2026, measured cold)

`scripts/patch_charme.py`, measured on `work/zenus_charme/dq9_cm_*.nds` (v18e seed 18 +
`rom_joueur.py` with a forced kit + the graft), cold boot from `apres_don` into battle 144.

- **Party statuses** live in `fiche+0x14` (bit `0x20` confusion, set by `0x020883DC`:
  `+0x5E` = 3, `+0x81` = 0, then `|= 0x20`; getter `0x021543F4`, 8 callers). The confusion
  handler of a spell is `0x021DD828` (overlay loaded only while the turn is compiled):
  target id in `r2`, success flag on the stack, message queued by `0x02159EAC`.
- **The menu does not skip a confused member.** At the start of a member's menu
  (overlay 26, `0x021DCD94`, member index in `sb`) the member is skipped if `fiche+0x14`
  bit `0x10` (`0x02088308`), `fiche+0x22` bits 2-5, or `fiche+0x14` bit `0x08`
  (`0x021DCE1C`, called at `0x021DCDC8`). Forcing that call to 1: "OK!", command
  `01 00 00 00`, queue action 1, no freeze.
- **The turn compiles actor by actor in turn order** (decide, then resolve): a status set by
  a faster monster acts on a slower member in the same turn. Per-actor decision in
  overlay 0 around `0x02157C20` (`r7` actor id, `sb` queue entry with the chosen action);
  `0x02157C24` calls the confusion getter, which replaces a confused member's action
  (`0x0215F67C`) and `0x02154150` randomises its target; the countdown and waking are at
  `0x02158470`.
- **Tactic dispatcher** `0x021F8F20` (overlay 24): returns at once if the queue action is not
  1 or if the tactic `[member+0x94C]` is 5 (Follow orders); > 5 goes to the fallback
  `0x021F8628`, 0-4 to the tactic table. The pre-check `0x021F9030` reads the same byte
  (`and r4, r0, #0xff` at `0x021F9078`).
- **Battle turn counter**: `0x023919BC` (0 at the first menu, +1 per turn); per member,
  `[actor+0x19C]+8` is a u32 count of turns played (0 at the first menu). The 12-byte command
  has no free byte (`+4..+7` cleared by a memset, `+8` that counter).
- **Overlay residency** (byte match on the battle and field dumps): overlay 11 is loaded on
  the field AND in battle; overlay 0 only in battle (3 on the field); slot 22-30 swaps
  23/24/25/26 during a battle. The tail of slot 7-14 behind overlay 11
  (`0x02188B80..0x0218B5A0`, 10 784 bytes) is zero in all 58 dumps of the project.
- **The graft** (440 bytes appended to overlay 11, state = 4 bytes per party index after the
  code): `0x021DCDC8` → G_MENU (skip if charmed; clears the member's state when its turn
  count is 0), `0x021F9078` / `0x021F8F6C` → tactic 0 if charmed, `0x021F9020` → rule B and
  one charmed decision used, `0x02157C24` → if a monster chose the charm action, one living
  companion (index 1-3, never the hero) gets 1-2 charmed decisions. The state only counts
  while actor `0xC0` is species 900 (the secret boss); otherwise it is cleared.
- **Measured** (`cm2`, charm on Fuddle 0x33): Athore charmed acts after the secret boss the same turn;
  next turn Melchior charmed is skipped by the menu (3 orders), his AI (tactic forced from
  Follow orders) casts *Sizzle* on the secret boss, rule B turns it on Athore (38 damage); Freyja
  charmed the same turn "attacks twice" Papouz (55). With `0x220` (eyes glow, damage to all
  + paralysis), `0xFB` (same text, ~4 damage + paralysis) and `0x169` ("fait un grand
  sourire malicieux", no effect) as the charm action: charm works, no freeze.
- Not yet measured: the state after a victory (cleared by design at the next battle's first
  menu), a rule B target that is dead. A full battle lost on the player ROM (~90 actions,
  defeat, back at the temple) runs without a freeze.
- **The charm's line** (`patch_charme.replique`). Action `0x1F6` is carried by nothing (no
  species, not in the technique pool, no name, message 0). It gets the record of `0x169`
  (no effect), with the id bits kept and **message `0x26F`**, a new entry after the game's
  last one (`0x26E`). Entry 0 of `actmsg` is a `DUMMY` with id `0x390000`, and the other ids
  are sorted, so the new entry goes at the end (`textes_dq9.ajouter_message` now checks the
  last id, not the largest). Its `.bact` case is copied from `0x220` (the eyes glow).
  `actdt_<x>_<lg>.nat` members are stored without a control block: rewrite with
  `gp2_ecrire.reecrire(..., brut=True)`.
- **Aquila's style does not work in an action message** (measured cold, 31 October,
  `work/zenus_charme/variantes_replique.py`, same ROM, only message `0x26F` changed):
  a plain line is shown during the animation and advances by itself; `//Name// text` shows the
  text **without** the name; `text<PAD_WAIT_NOCUR><CLOSE>` shows **nothing** and the battle
  waits for a key on an empty window (the line is compiled in RAM, `0x021181A9`). Aquila's
  `0x1EE` and Corvus's `0x211`, the only two such lines in `actmsg`, belong to the cutscene
  fights and are shown by another path (not found: no immediate `0x1EE` in the code). The line
  kept writes the name out: « [boss] tonne : Obéis-moi, tu es ma création ! ».

### 113.7 The void: a companion erased for good (1 November 2026, measured cold)

`scripts/patch_charme.py` (same overlay-11 block, now 916 bytes) + `zenus_royaume.declencheurs(combat)`.
Bench: `work/zenus_neant/banc_neant.sh` (cold boot from `apres_don`, battle 144, flag byte
`0x0210890F` read at every step), ROMs `work/zenus_neant/dq9_ne_*.nds`.

- **Patty's farewell, read in the code.** Leaving the party (overlay 3 `0x02163E4C`, index in
  `[obj+0x482]`): `0x021B6BB8(id)` puts the member's carried items (8 u16 at member
  `+0x454`) into the bag (`0x020A096C(save, item, 1)`); `0x021B6D60(id, record)` fills the
  572-byte record (`0x020830DC`) and takes the member out of the party (resets the object,
  frees its model, updates the followers: `0x02190264`, `0x02191108`); `0x02086788` adds the
  record to Patty's list. Farewell (`0x021668FC`): for the 8 equipment slots of the record
  (`+0x160`, slots `0,1,4,5,6,7,8,9`, categories `2,3,5,6,4,0,1,7`, tables overlay 3
  `0x0217F494` / `0x0217F4A6`) `0x0207C388(save+0x1D4, item, 1, category)`, then
  `0x02086A14(save, id)` deletes the list entry (id set to 0x3F, count `save+0x2C8C` - 1,
  compacted). `save = 0x02010838(mgr)` = `mgr + 0x2A04`; party count at `save+0xF7C`.
- **One actor per id, field and battle.** `mgr = 0x020F33D8`, actor `[mgr+8+4*id]`, flags u16
  at `+0`: `0x80` in battle (`0x0200FE78`), `0x100` in the party (`0x0200FF2C`), `0x1000` a
  created companion; `[mgr+0x3AC]` = hero id (0). The battle uses the same objects (HP record
  `[actor+0x138]` = member object `+0x94`): there is no copy back after a battle.
- **Monster targets** are built by overlay 0 `0x02154A04(ctx, actor id, action, out list)`
  (count in r0, ids as s16), NOT by the party's `0x021540FC` (traced: called only for ids
  1-3). A record whose byte 11 is `0x0A` (e.g. `0x169`) targets its user: no builder is
  called and `<DEF_ART_TARGET>` names the user ("[boss] réduit [boss] au néant").
- **Trigger actions that reach the runner.** The runner `0x0206F834` only receives queued
  nodes; an op whose runner case is the default (`0x92`) is never queued (traced: runner
  list empty). `0x80` and `0x89` have real cases (aliases of `0x77` / `0x79`) and no game
  trigger uses them: `0x80` is redirected (jump-table entry `0x0206F8E8`).
- **The graft.** The secret boss's decision (`G_POSE`): HP ≤ 2000 and no victim marked → a random
  living member that is not the hero is marked in flags `0x1FA-0x1FC` (id + 1; byte
  `0x0210890F` bits 2-4) and the action becomes `0x1F7` (record of `0x22D`, single target;
  message `0x270` "[boss] réduit <DEF_ART_TARGET> au néant...", five languages; `.bact` case
  of `0x220`). `G_CIBLE` at `0x02154A04`: for `0x1F7`, the list is the victim alone and its
  HP is set to 0. Trigger action `0x80` (`G_EFFACER`): the three farewell steps on the marked
  id, without adding the record to Patty's list, then the mark is cleared.
- **Measured.** Victim Athore (id 1): "[boss] réduit Athore au néant...", Athore dies, the others
  win, experience to three; back on 4303 the kind-15 trigger (`... ; 80`) runs: flag byte
  `0x28 → 0x60`, actor id 1 gone, party count 4 → 3, menu and followers show three, the
  save area gains eight equipment entries (six new, two counts + 1) and the carried items.
  Defeat path: mark set by hand (byte `0x6C`, Melchior id 2), leave 4303 and come back: the
  kind-20 trigger erases him (two members left). Not measured: a real defeat then the walk
  back; a save written after the erase and cold-booted; a victim revived during the battle
  (it would act again, and is still erased after).

### 113.8 The void, fixed: queue byte +9, damage hook, the question inside the church (1 November 2026, evening)

Bench: `work/dumps/nr_debut.State` / `n3_debut.State` (battle 144 start), traces with
`etat_macro.lua`; ROMs `work/zenus_neant/dq9_n2/n3/n4g/n5g.nds`.

- **Queue entry byte `+9`.** The game sets it to 0 whenever it replaces an action
  (confusion, `0x02157B90`, `0x02157BCC`, `0x02157C44`). A monster's targets for its
  next action can be drawn at the END of the previous turn (`0x02154A04` called from
  `0x021EDF94`, e.g. the secret boss's `0x21F` after his `0x219`): replacing only the action id
  keeps those targets and the old effect ("[boss] réduit Papouz au néant…" then the
  `0x21F` bolt on the whole party). Setting `+9` to 0 makes the game rebuild the
  targets (our `0x02154A04` hook runs) — but left at 0, the entry was never decided
  again: the secret boss repeated the void every turn on the dead victim and the game redirected
  the hit to a living member (the player's "void on Papouz, no effect"). Fix: keep the
  entry, its action and `+9`, give them back at the next menu.
- **Damage application** `0x0215A004(ctx, attacker id, target id, damage)` (overlay 0):
  `HP - damage`, clamped at 0, written at `0x0215A114`; every effect handler goes
  through it (15 callers), misses included with damage 0. Hooked at its entry: a monster
  hitting the pending void victim deals 9 999 (defence irrelevant), the victim is marked.
- **Clearing actor flag `0x80` (in battle) on a dead member freezes** within a turn
  (`n3_apres.State`, poke `0x022DE95C = 0x43`). Battle-side member list candidate:
  `0x0239521C` (ids `00 03 02 01`, twice), read by battle code around `0x0217xxxx`.
- **A line `<YESNO>…<ADD><CHURCH=9>` opens the church on NO too** and everything stays
  locked. The game's own pattern (journal, manner 2) asks INSIDE the church: message
  1000 = the question, 100 = `<YES>…<ADD>\n<NO><CLOSE>`, the confession waits for the
  answer when `+0x5B4` is set (original test at `0x02159EDC`). Manner 8 now does the
  same with the slime's question; text after `<NO>` needs `<PAGE>` before `<CLOSE>` to
  be shown. Measured: NO → "tant pis", control back, the question comes again; YES →
  gift lines, saving, "réussie", flag set.

### 113.9 The displayed damage, the visible charm, the erased member out of the battle (5 November 2026, measured cold)

`scripts/patch_charme.py` (now 1 988 bytes behind overlay 11, 12 sites). ROMs `work/zenus_neant/dq9_n9.nds`
(2 001 HP; byte-identical to the player's `dq9_zenus_v3_rapide.nds`) and `dq9_c9.nds` (kit forced to the charm).

- **The turn is compiled in one go, then replayed.** All damage of a turn goes through `0x0215A004` within the same
  frame, at the start of the turn; the screen shows it afterwards. Anything counted at compile time is already over
  when the player sees the action: a companion charmed for one decision had its counter back at 0 before its action
  was shown, and never appeared charmed. Display state must be separate from logic state.
- **Displayed damage.** The effect caller, overlay 24 `0x021EC92C` (`blx ip`, r1 attacker, r2 target), keeps the damage
  in `[sp+0x54]` and passes a copy in `[sp]`. The physical effect `0x021DA9E0` takes it as its 5th argument, and the
  number shown comes from there, not from `0x0215A004`'s argument. Writing 9 999 to both at the entry of `0x021DA9E0`
  (only from that caller, `lr = 0x021EC930`): "Athore subit 9999 points de dégâts", "Athore meurt !".
- **Battle status panels** (bottom screen, engine B). Panels are BG1; every text is an OBJ whose palette is the colour:
  OBJ palettes 0 white, 3 grey, 4 yellow, 5 orange, 6 red; glyphs use index 15, digits indices 2-7. `0x02170C7C`
  (overlay 0, `r0` = display record) returns the colour of a line: 6 dead, 5 under 8 % HP, 4 under 25 %, else 0.
  The palette numbers used in five battle states: 0, 3-7, 11, 13; rows 1 and 2 were never seen.
- **The UI object** `O = [0x02184290]`. `O+0x958`: display records of `0x448` bytes per id (`+8` max HP, `+0xC` HP,
  `+0x28` copy of the statuses, `+0x4C` id, negative = skipped by every loop). `O+0x6C`: the 4 ids in bar order;
  `O+0x70`: same, -1 for an absent member; `O+0x79`: number of bars.
- **Status icon.** It comes from the copy `record+0x28`. `0x02174550` syncs it from `[actor+0x138]+0x14` only at the
  menu (caller `0x021D9D98`, overlay 26); `0x021706B8` reads it about every other frame per member, menu and replay.
  Bit `0x20` shows the confusion stars (OBJ palette 13, indices 3-8; `0x0217FF34` is a different path, not the panel).
- **Removing a member at runtime.** Setting `record.id = -1`, compacting both lists and decrementing the count takes
  the bar out: the others close up at the next redraw, and the ally target cursor and the Tactics list no longer offer
  it. Measured with the victim last (Athore) and in the middle (Freyja).
- **Clearing the actor's flags freezes** (three measurements). `0x80` alone: a null actor reaches `0x02010098`
  (`actor->[+0x138]->[+0x14]`, about 60 callers) at the next turn compile. `0x80 | 0x100`: a null at `0x0208AA8C` as
  soon as the state runs. These getters are assumed to succeed all over the code. The actor is therefore kept, dead.
- **Revive.** Kazing is action `0x27`. Control (no lock, forced on the dead Athore): status written at `0x02089058`, HP
  at `0x02089070`, both from `lr = 0x021DD400`. With `0x021EC92C` returning 0 for the erased id (the game's own
  "no target" result): the spell is cast, no write, no message, no freeze. A party AI action on him becomes Attack on
  the secret boss (rule at `0x021F9020`), measured by forcing tactic and target (`DQ9_REG`, `DQ9_POSE`).
- **End of the fight, measured end to end.** Victory: flags `0x28 → 0x20 → 0x60`, back in 4303 with three members.
  Real defeat: "L'équipe est exterminée", back at the temple, three members revived, flags `0x28 → 0x20`.
- **Not measured.** An ordinary battle on these ROMs (the hooks run in every battle; the first two turns of battle 144
  are the same path, nothing marked or charmed); a save written after the erase and cold-booted. Blue goes on at
  compile time, so it can show slightly before the charm's line when the secret boss is not first in the turn.

### 113.10 One void per save, and a forced cycle for testing (5 November 2026, measured cold)

- **Once per save.** The mark used to return to 0 once the companion left the party, so a rematch after a defeat
  could erase a second one. It now goes to 7 (`VICTIME_FAIT`, not a member id), read as "no victim" by every hook and
  ignored by trigger action `0x80`. It lives in the game flags, so it is saved. Measured on the same 2 001 HP ROM
  (`dq9_zenus_v4_rapide.nds`). Control from `apres_don`: flag byte `0x20 → 0x28` (void, 9 999, Athore erased), a real
  defeat, back at the temple with three members, `0x28 → 0x3C`. Second fight from a save with the mark at 7
  (`work/zenus_neant/save_neant_fait.py`, byte `0x3C`): the secret boss under 2 000 HP, no void, four bars kept, his normal kit,
  byte unchanged.
- **Forced cycle (`ZENUS_CYCLE=1`, bench only, `patch_charme._cycle`).** Every decision of the secret boss is forced to charm,
  void, Defend; members are set to 999 HP at their menu (`[actor+0x138]`: `+4` max HP, `+0` HP, shown on the panels).
  22 turns without a freeze: three voids in a row, hero alone, then Defend only. The mark holds one victim, so only
  the last one is locked and leaves the party after the fight.
- **Defend is action `0x03`** (`actdt_b`, message "se défend", targets its user); no `.bact` case is needed for its
  text. `noms_actions` names id 5 "Defend", an id absent from the table.

### 113.11 Actions per turn and Aquila's dialogue box, read in the code (5 November 2026)

- **Actions per turn: `mon_btldata +0x10` bits 8-10**, corrects §113.4. Overlay 0 `0x0215F57C(ctx, id)` returns the extra
  actions (caller `0x0215DDB0`, the turn builder): it indexes an 8-byte table (`0x02182A6C`, `00 00 01 02 00 00 00 00`)
  by those bits, after patching it. 0 → none; 1 → one if `0x0207430C(ctx, 2)`; 2 → one; 3 → two; 4/5 → one/two if bit 0 of
  `[actor+0x138]+0x3C` is set; 6/7 → one/two if it is clear. §113.4 wrote `mon_moddata +0x0C` bits 9-11 instead; that
  record is only copied for species of the zone table (§94.4), so a scripted fight reads `mon_btldata`. Measured by
  tracing the decisions (`0x02157C24`, r7 = actor): Nokturnus `C0 2 0 3 C0`; the secret boss `C0 1 2 0 3` until `+0x10` low bits
  became `0x228` (`work/zenus_tours/rom_btl.py`, `banc_tours.sh`), then `C0 ... C0`. The nameless "effect 7" action
  (`0x31C`) has nothing to do with it (measured). What it does is still unknown.
- **The box of Aquila and Corvus**: not an action message. Overlay 0 `0x0215FC60(ctx)` returns 1 for species 800 and
  2 for 801 at the head of the fight (`ctx+0x81FE`). Overlay 25, start of a replay (`[sl+0xEAC] == 1`, r4 = ctx):
  `0x021DB0AC` tests it; on turn 1 (`[ctx+0x8E20] == 1`) with actor `0xC0` first, it resets the replay helper, frames the
  actor (`0x0216DF00(sl+0xC18, actor, 0, 0, 1.8f)`), hides the panels (`0x021626A0` twice) and sets flag `0x1000000`
  (`0x02160FA8`, word `ctx2+0x55F4`), then loads the message: box at `sl+0xA40`, `0x0216FE48` reset, `0x0216FDF8(box, id)`,
  `0x0216FD0C` start. The ids are the literals `0x021DB44C` (`0x1EE`) and `0x021DB450` (`0x211`). While the flag is up, the
  frame polls `0x0216FD38`, gets the text (`0x0216FCFC`), formats it with the hero's name (`0x02003CE8`, `[hero+0x134]`) and
  opens the talk window `0x0204501C(talk, text, 0, 0xE3)`, `[talk+0x998] = 1`; when that goes back to 0 the flag clears
  and the replay goes on.
- **Using that box in any turn** (`patch_charme`, measured cold, three failures first). Reusing Aquila's framing, or just
  the flag and the message once the turn is prepared: the box shows, then the replay never resumes (state `[sl+0xEAC]` = 3,
  `0x021DC590` forever, `0x021E9528` false because `helper+4` stays set). The box object `sl+0xA40` is also the loader of
  the turn's own messages (`0x021EA0F8`), so it must run BEFORE `0x021DBE10` prepares the turn. Then `0x021E8A54` (the
  loader's heap) returns 0, the text comes back null and the window never opens: pass `sl+0x30`, reset first with
  `0x02032698`, as `0x021DBE10` itself does. While the flag holds, state 1 must not run again (`0x021DB09C`). The result:
  four lines in five languages, no freeze, fight goes on to victory or defeat.

### 113.12 The boss kit, stats and size (5 November 2026, measured cold)

- **Action `0x1F7` is not free** (corrects §113.7). Its record is empty, but the turn builder puts it in the queue of an actor that
  cannot act yet (overlay 0: `mvn fp, #0`, `add r0, fp, #0x1F8` at `0x0215DDD0`, stored at `0x02157BCC`). With 2-3 actions per turn it
  shows up every turn, and the target builder `0x02154A04` is called for it (caller `0x021549F0`). The void now uses `0x386`
  (empty record, no immediate in the battle code, `work/zenus_tours/ids_libres.py`), and its hook also requires that this turn's
  decision posed it. Measured: 20 000 HP, no mark over 8 turns; 2 400 HP, a real void on a companion below 2 000 HP.

- **Decision.** `G_POSE` draws from `patch_charme.TABLE` (10 actions, the record's six slots are not used; PM 255: at 24, Melchior's staff drained them and the heal failed with "not enough MP"): never the
  same action twice in a turn, the charm only if nobody is charmed, the heal once per fight under 40 % HP. Up to three
  replaced entries are kept and given back at the next menu (§113.8).
- **Elements.** Action records `+12` (u16), bits 6-8, 1-based: fire 1, ice 2, ... dark 6 (`0x217` "nuage de ténèbres"), light 7
  (`0x219` "nuage de lumière"). The 7 element bytes follow that order: Nokturnus has dark 50 %, light 150 %. The secret boss has the
  reverse. Only read in the data, not measured with a spell in battle.
- **Damage on the player's save** (levels 56-75, 320-440 HP). Attack 1 406: a plain hit deals 650-900. Attack 800: 380.
  Fixed-power techniques do not move with attack: lightning (`0x21F`) about 175 to all, cloud (`0x219`) about 175 to all.
  Defence 915: the party deals 1-90. Defence 500: about 150 per hit.
- **Size.** `pos_scale` does nothing in battle (§113.4). A constant scale on the root node of every animation does
  (`zenus_mon.nsbca_echelle`: root body copied to the end of the file, scale pairs added, node table repointed). Nokturnus'
  box is the same on the field and in battle (`b112a`, `b112a_f`: 39.9 high), the secret boss's 29.6; ×1.4 in battle, ×1.25 seated on the
  throne.

### 113.13 Scripted turns, the dying line, the void's own effect (5 November 2026, measured cold)

- **Replay state 1 runs once per ACTION, not per turn** (`[sl+0xEAC]`: 1, then 3, 4 or 6, then 3). A box can open before any action.
  State 2 shows up only in some final turns: not a usable marker.
- **The dying line.** Everything is compiled before the replay, so HP is already 0 when the killing turn starts. `G_POSE` counts the
  actors compiled (`+56`), `0x0215A004` notes the rank of the lethal one (`+57`), the replay counts its actions (`+58`) and opens the box
  just before that rank, on the same path as the thresholds. Not after the blow: no state-1 pass follows it, "defeated" comes at once.
- **A separate effect file.** `effect/em0500.chr` (Whack) copied as `data/effect/zn0500.chr` with its inner names and palettes changed;
  the `.bact` case points at it, and `op75`'s second float scales the flames. The game's own Whack is untouched.
- **Treasure maps in a save** (community editor layout): count (byte) at `+24204`, 28-byte entries at `+24206`: `+0` state | kind << 3
  (legacy = 2, discovered = 2), `+21` place, `+23` boss (Nokturnus 10), `+24` level, `+26` u16 turns.

### 113.14 MP, the charm's target, the monster list, a new battle theme (5 November 2026, measured cold)

- **255 MP never go down**: spells and Melchior's staff leave them at 255 (control: start at 40, then 26, 18). `0x25B`, the nameless action of species 319,
  gives no MP back.
- **A target needs an effect that is not cancelled.** Returning 0 from `0x021EC92C` makes the game frame nothing: the camera shows a wall. Record of `0x169`
  (no effect) with byte 11 = 9 gets a real target and the camera on the companion.
- **The monster list** is `data/prm/mon_list.gp2` (`mon_list_<lg>.nat`: u16 count in 12 bits, u16 pool size / 16, records of 32 bytes, then the pool): `+4` model code,
  `+8` name, `+0xC` species, `+0xE` sort rank, `+0x12` family, `+0x1A` number, 1 to 308 (`0x134` in the code, also the index of the defeat counters in the save). Rhapthorne
  is 307, so 308 is free. `mons_info2.nat` holds the motion list per species (count `+12`, table index `+44`), the gold on 16 bits.
- **A new theme in `bgm.sdat`**: slot 25 is empty in SEQ, BANK, WAVARC and GROUP. One looping IMA-ADPCM wave held by one note. In this battle, a 446 KB wave is not loaded,
  a 312 KB one is (read in RAM).

### 113.15 Full heals, facing an NPC, the train's dashboard, voices (5 November 2026, measured cold)

- **Only two actions heal fully.** Overlay 24 `0x021DB3EC`: `cmp r0, #0x21 ; cmpne r0, #0x310 ; ldreq r0, [r4, #0x138] ; ldrheq r6, [r0, #4]`: the amount becomes max HP.
  Any other action stops at 999, whatever its power (`+30`: 20 000 still gives 999). The heal itself is `0x0215A16C`. Hooking that compare for one more id gives the real amount on screen (14 006 of 20 000 HP: "5994").
- **A heal record works in `actdt_b`.** Records of `actdt_a` keep their layout when copied to a free slot of `actdt_b`; the name offset (`+2`) is relative to each file's pool, so a message with `<ACTION>` would read the wrong name: write the name in the message.
- **`<N_TURN>` keeps an NPC from turning** when spoken to (text tag, ARM9 `0x0206A490`, clears `+0x19B6`; Stella uses it). `0x0B` values 0x4, 0x8, 0x10, 0x20, 0x40, 0x100, 0x1000, `0x12` 0-3, the NPC's kind and fifth parameter do not. `0x20` makes the NPC translucent; kinds 0 and 5 drop this model.
- **The train's "!" is NPC 106**, a modelless zone on the dashboard (`0x06` zone, `0x0B 0x40`; its only line: "cannot read the controls"). With NPCs 2 (Stella), 203 (Aster) and 210 removed and the flag set: "!", realm, world map, "Descend here?", on the ground.
- **`0x11` removes an NPC when its map is not the current one** (`0x0206D66C`), with pairs of flags as conditions: at the end of `place.bin`, a conditional removal.
- **Loudness.** A theme of the game opens 16 tracks (`FE FF FF`, then `93 n offset24`). One DS voice is already at its maximum, so a one-voice wave sounds faint; n tracks playing the same wave stay in phase. Read on the ARM7 bus (`SOUNDxCNT`, `scripts/lua/canaux_son.lua`): 4 active channels, volume 126, format 2.
- **Above-maximum HP overflows the field gauge** (test ROM writing 999 to max HP in battle: 824/430 afterwards, a line past the bar).

### 113.16 Party targets, stat steps, a multi-stat effect, bestiary texts (6 November 2026, measured cold)

- **The party's target builder** (overlay 0 `0x021540FC`, the party's counterpart of `0x02154A04`) reads the action
  record from `0x02079E3C(0x020797EC(), id)`: side `([rec+8] >> 8) & 3` (1 = the other side, 2 = own side), scope
  `[rec+0x14] >> 28` (2 one target, 3 all, 4 a group, 5 Attack: 3, 4 or 2 depending on the weapon, checked at
  `0x021541C0`). In this RAM record the id is at `+4`, so file offsets read by `_rang`-style code are 2 lower.
  The computed scope sits in `r2` at `0x021541FC` (`cmp r2, #1`); `0x0215E9FC(ctx, list, 8, 1)` lists the living party,
  `0x02154348` is the common end. A charmed companion's zone spell routed through that list hits every teammate but
  himself; a teammate's Bounce sends it back to the caster, as in the game.
- **Stat steps** live at record `+0x58` of a fighter: attack bits 0-2, defense 3-5, agility 6-8 (signed). Setters
  `0x020877D0` / `0x020878C4` / `0x020879B8` (fighter, delta) clamp to ±2 and set a 5-turn counter; `0x0208777C` /
  `0x02087870` / `0x02087964` say whether the step can still move. Oomph's effect (`0x021DB5EC`) takes its delta from
  the action record (`+0x30` in RAM): Oomph gives 2 at once.
- **Effects called by `0x021EC92C` return the message queue** they filled (`0x0215E958`); returning anything else
  freezes the turn compile (measured). `0x021E1ED4` raises several stats into ONE queue, one message each
  (`0x021E94C4` attack, `0x021E95D4` defense, `0x021E96E4` agility, pushed by `0x0215A88C`), then ends with
  `0x0215CD44`. A copy with the three setters at +1 gives "[boss] sees his attack / defence / agility increase slightly".
- **Bestiary texts** `mon_trv1` (how it fights) and `mon_trv2` (what it is): per language, a u32 (entry count on 12 bits,
  pool size on 20), pairs u32 (list number, pool offset) sorted by number (duplicates for shared numbers), then the pool.
  Number 307 is the last; an entry for 308 appended at the end keeps the order. Up to ~135 characters per text.

### 113.17 Knight Watch, the paladin's coup de grâce (6 November 2026, measured cold)

- **Action 0x201** (French "Paradin", English "Knight Watch"). Forced on Freyja at her decision during the turn compile
  (`etat_macro.lua` `DQ9_ACTION=3=201`): "Freyja porte son coup de grâce... Paradin !", then "La colère aveugle [boss] !
  Il ne lâche pas Freyja des yeux !". Its effect (overlay 24 `0x021E1DE8`, called by `0x021EC92C` with r1 = paladin,
  r2 = 0xC0) targets the **monster**: if `0x02088E14(record)` allows it (`+0x14` bits 0x1, 0x8, 0x10, 0x20, 0x80000
  clear), `0x02088E58(record, n)` stores the duration in `+0x7E`, clears `+0xA1` and sets `+0x18` bit `0x1000`; then
  `record+0x2E` = the paladin's id. `n` = random between the monster's battle record (`[actor+0x148]`) `+0x28` and
  `+0x29` (2 and 4 for the secret boss; 3 measured). `0x02088E74` clears all three.
- **The redirect**: the monster single-target picker (overlay 0 `0x02154F30`, r1 = monster id) returns the paladin when
  the monster has `+0x18 & 0x1000` (`0x02155154`) and the actor of `+0x2E` exists, is alive (`+0x14` bit 0 clear,
  `0x02010098`) and lacks `+0x18 & 0x2000` (`0x02153C0C`). A target chosen by our own code (the secret boss's charm, G_POSE /
  G_CIBLE) bypasses it: that is how the charm "went through" Knight Watch.
- **Bench note**: a party member's menu command (`[actor+0x19C]`, 12 bytes per id from `0x02397178` here) is copied
  again when the last order is validated; poking it is useless. The decision hook `0x02157C24` (r7 = id, sb = queue
  entry) sees every actor, party included, and rewriting `[sb]` there works.
- **What the secret boss does under Knight Watch** (player's choice, 6 November): he still casts the charm, but it goes to the
  paladin and fails. `patch_charme` G_POSE: if `paradin(record)` (the same four tests) gives an id, the charm's only
  target is the paladin (state `+59`) and no counter is set. Measured cold with Freyja's real Knight Watch: the rings
  land on Freyja, "Le Paradin protège Freyja !", nobody charmed, 6 turns without a freeze. Without a target the
  charm hit the secret boss himself ("Mais rien ne se passe"). Charming another companion instead was tried: the game
  cancelled it ("Mais rien ne se passe", nobody charmed); not understood, dropped. The void ignores Knight Watch.
- **Poking the status alone is not Knight Watch**: `+0x18 | 0x1000`, `+0x2E`, `+0x7E` written by hand redirect the secret boss's
  attack to Freyja, but she takes the damage (710, dead) and `0x02158644` then clears the status (paladin dead). The
  invulnerability comes from elsewhere in the real effect (not found); bench with the real action.

## 114. Items: attack from equipment, the item table at runtime, adding an item (6 November 2026)

For the secret boss's weapon (ZER-116). Measured cold on `work/zenus_joueur/base_v18e.nds` + `depart.SaveRAM`
(`work/arme/`): Papouz swaps the executioner's axe for the king's axe in the Equip menu, attack 551 -> 531.

### 114.1 Where the attack is computed (read in the code, write watched)

- A party member's runtime record (Papouz: `0x020F5478`) holds the displayed stats at **`+0x6C`** (u16),
  `+0x6E`, **`+0x70` attack**, `+0x72` defence, `+0x74` agility. Write watch on `+0x70`: `0x020845A8`
  (`strh r4, [r7, #0x70]`), in an ARM9 function that recomputes everything when equipment changes.
- **The sum** (`0x02084500`-`0x020845A8`): attack starts from a base stat of the record, then for each of the
  **11 equipment slots** (`record + 0x194 + 32*i`; `+0x18` = equipped item id, > 0) it adds the **signed 10-bit
  field bits 0-9 of word `+8`** of that slot's equipment record (defence: bits 10-19), then a bonus
  (`0x02085CE0(record, -1)`, skills), and **clamps to 0-999**. So an equipment attack can be at most **511**.
- The slot's equipment record is a 32-byte copy (`0x0208359C`: slot = `+8 & 0xF` of the item, 0 = weapon -> slot 8)
  of the item's **equipment record**, itself copied at menu time from the item file in RAM.

### 114.2 `itemdt_<lg>.nat` (member of `data/prm/itemdt.gp2`), read in the loader

Loader `0x020DE8xx` / `0x020DE5C0`, header size `0x020DE7B4`. **Records start at `+0x0C`, not `+0x10`**
(the old reading, `patch_pages._fiche`, works because it only uses fields shifted by 4: its `+0x14` is the real `+0x18`).

```
+0x00 u16  number of item records N (low 12 bits)            1423
+0x02 u16  number of equipment records E | 0x8000 (= a 0x58-byte extra block follows them)   1189
+0x04 u32  0
+0x08 u32  string pool length | 0x80000000
+0x0C      N item records, 32 bytes, SORTED BY ID (binary search, 0x020DE660 with getter 0x020DE57C = ldrsh +0x18)
           E equipment records, 32 bytes
           0x58 bytes (u16 list, not read here)
           string pool
```

Item record (32 bytes):

| off | meaning |
|---|---|
| `+0x00` | **equipment record index** (-1 = none); the loader turns it into a pointer: `table + 32*index`, table = right after the N item records |
| `+0x04` | name offset in the pool (relocated to a pointer by `0x020DE584`) |
| `+0x08` | flags; low nibble = equipment slot type (0 weapon), bits 13-15 price class (§83.11) |
| `+0x0C` | low 12 bits flags (`0x0E3` weapons, `0x1E3` armour, `0x063` items); **bits 12+ = list number** 1..1176: the save editor's `wardrobeIdx` = number + 6 for all 944 equipment items. 0 for the 183 `14xxx` copies and the debug items (not in any list). The "found" bit field (`WARDROBE_FOUND_OFFSET`, 944 bits) is full |
| `+0x10` | `letter << 20 | n << 10 | n`: for weapons n = the model number (`p_w%03d` / `d_w%03d`); swords that share a model share n |
| `+0x18` | u16 **id**, u16 sell price (§83) |

Equipment record (32 bytes; weapons are indexes 0-267, then shields, torso, …):

| off | meaning |
|---|---|
| `+0x00` | class word (sword `0x10000081`, axe `0x10000481`, …) |
| `+0x04` | **bits 0-11 = vocation mask** (`0xFFF` = all; warrior armour `0x001`, martial artist `0x008`); bits 12-15 = class (sword 1, spear 6, axe 7, …, armour 2). **Every weapon has mask 0** (vocations by class) |
| `+0x08` | attack bits 0-9 (signed), defence bits 10-19 |
| `+0x18` | 8 bytes, unknown |

Weapon classes by id: knives 19050-19071, clubs 19150-19168, **swords 20000-20029** (`0x10000081` /
`0x18001000`), fans 201xx, axes 202xx, whips 203xx, staves 204xx, spears 205xx, wands 206xx, boomerangs 207xx,
claws 208xx, bows 209xx. `itemdt_w_<lg>.nat` (also read by the ARM9) has the same format, weapons only (268 / 268).

### 114.3 The other per-item tables (all sorted by id)

The ARM9 names: `itemdt`, `itemname`, `itemexpl`, `item_tmn`, `itemdt_t`, `itemdt_w`, `itemsort`, `itembtlprm.nat`,
`item_fn_div.nat`, `iteminfo_<lg>`.

- `itemname_<lg>.nat`: `u32 = count | pool size << 12`, 16-byte records (name, plural, grammar flags, **id at
  `+0x0C`**), pool. 1178 records sorted by id.
- `itemexpl_<lg>.nat` (and the `iteminfo_<lg>.gp2` copy that is shown): same header, 8-byte records (id, offset).
- `itembtlprm.nat`: u32 1423, then 1423 × 44 bytes, **id at `+40`**, parallel to `itemdt`.
- `itemsort_<lg>.bin`: a Nitro script table (`66 00 01 01` …), 1178 records (+ the 0x64/0x65 head).
- The bag in the save stores ids (weapons: 272 slots for 268 weapons), not ranks.

So **an item added at its id's place** in every table moves no name: nothing is indexed by rank, every lookup
found here is by id. The other unknowns (whether all of them are binary searches; a weapon with a mask) need a test.

### 114.4 Weapon models

`data/pack_lv5/chara_pc.gp2` holds `p_wNNN.nsbmd` (200, 0.7-1.8 KB compressed), `chara_pd.gp2` holds `d_wNNN.nsbmd`
(178, larger). NNN = the item's model number (`+0x10`). `data/bin/wpnpos.bin` (832 bytes) is **one entry per weapon
class** (12), not per model: a new sword takes the swords' hand position. Adding a member to a GP2 archive:
`gp2_ecrire.ajouter` (index written in clear, type 0).

**Measured (6 November)**: of `letter << 20 | a << 10 | b`, **`b` (bits 0-9) is both the model and the icon**; `a`
changed alone shows nothing. The icon is the NitroFS file `data/ani/d_w%03d.spr` (494 bytes: header, 24×24 4-bit pixels
at `+0x28` in a tiled layout not decoded yet, 16-colour BGR555 palette at `+0x150`, a BMP-like header at `+0x170`).
Model numbers without a file give an empty icon. The weapon models are one bone and one shape, blade along Z; their
display lists use `VTX_16`, `VTX_XY`, `VTX_XZ`, `VTX_YZ` and end the MDL0 block (`work/arme/gx.py`).

### 114.5 Who may equip a weapon (read in the code, measured)

`0x020DD500(member, item)` returns refusal flags. For a weapon or shield (`item +8` low nibble 0 or 1) it never reads
the vocation mask: it asks `0x020DD210` (exceptions) then `0x020DD164` → `0x020DD1AC(vocation, class)`: allowed if
one of the vocation's 4 skill trees (`0x020DD12C`) maps to the class (byte table `0x020EE710`, trees 1-14), class =
equipment word 0 bits 7-10. Other slots test the mask. The "Suits" panel (overlay 23 `0x021DF2F4`) repeats the same
choice for its icons. Every vanilla weapon and shield has mask 0.

### 114.6 Drops of a scripted fight, and the drop graft

A scripted fight keeps `mon_btldata` drop classes (`+2`/`+3`, class 0 = always) and items (`+4`/`+6`): the secret boss's
record 437 with rare item 20030, class 0 → "[boss] laisse tomber un coffre au trésor ! … Il renferme un éclair de
[boss] !". With `--butin-combat`, the overlay-23 graft (§90.2) replaces any non-zero item; register `r0` is dead after
both sites (`ldr r0, [sp, #0xc]` follows). Overlay 23 is full up to `0x02200160` (the page graft ends there).
