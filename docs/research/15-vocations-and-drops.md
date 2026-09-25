# 15. Vocations and per-battle drops (§89–§90)

Measured on September 25, 2026 (ZER-36, ZER-39), in BizHawk with memory
watches (`event.onmemoryread` / `onmemorywrite` / `onmemoryexecute` on full
System Bus addresses, three arguments) and step-by-step screenshots.

## §89 Vocations

### 89.1 Unlocked vocations are event flags

The six unlockable vocations (Gladiator, Paladin, Armamentalist, Ranger, Sage,
Luminary) are **story flags**, set by the script of their quest. The flag array
lives at `0x021088D0` (the save block, copied to RAM at load); the flag of
vocation `id` has index `0x113F + id`, i.e. indices `0x1146`–`0x114B`. Eight
flags per byte, so they fall in the u16 at `0x02108AF8` that §22 of the
September 22 notes had located (bits 6–11). **CONFIRMED**: the only reads of
those six flags when talking to the abbot come from the list builder below.

The game reads every flag through one function:

    0x0206DFC0   test_flag(ctx, flags, index) -> 0/1
    0x0206DF7C   set_flag(ctx, flags, index, value)

The script command that unlocks a vocation is at `0x02062FE8` (event-script
VM, ARM9): `set_flag(..., 0x113F + id, 1)`.

Vocation ids (save editor `DQIX/editor`, confirmed by the in-game list order):
0 Guardian (prologue only), 1 Warrior, 2 Priest, 3 Mage, 4 Martial Artist,
5 Thief, 6 Minstrel, 7 Gladiator, 8 Armamentalist, 9 Paladin, 10 Sage,
11 Luminary, 12 Ranger.

### 89.2 The abbey list (overlay 3)

When the player talks to Abbot Jack (« père Blaise », Alltrades Abbey, L1,
straight ahead from the entrance), `0x02156054` builds the vocation list:

    ids 1..6 are added unconditionally
    for each id in the 0-terminated table 0x0217F304:
        0x021560B0   bl test_flag(ctx, flags, 0x113F + id)
        0x021560B4   cmp r0, #0 ; addne -> added to the list

Replacing the `bl` at `0x021560B0` with `mov r0, #1` puts all twelve in the
list. The flags themselves do not change: the unlock quests stay playable.

**Measured in game** (work ROM `voc_p.nds`, player's save, cold boot, Zoom to
the abbey): the list shows 12 vocations, Ranger and Luminary (« Sommité »)
included; choosing Ranger gives « Papouz est devenu ranger ».

Overlay 23 has a second loop over the flags of ids 7–12 (`0x021DF2A8`), which
fills a 13-byte table on the stack; it did not run in any menu we opened
(status, spells, battle records). It is left alone.

### 89.3 Recruiting at Patty's (overlay 9)

Patty (« Tulipe ») stands behind the left counter of the Quester's Rest in
Stornway (« Ablithia »). « Recruter un ami » → the vocation menu offers **only
the six base vocations**, whatever is unlocked. Then the creation screens
(gender, build, hair, colour, face, skin, eyes, name) and « Ajouter ce
personnage à votre liste d'équipiers ? ».

On « Oui », overlay 9 applies the choice:

    0x021876C8   ldrb r1, [sl, #0xda2]     the chosen vocation
    0x021876D0   bl 0x02083CB0             set_vocation(obj, id)
    0x021876D4.. ldrb r0, [sl, #0xda2]     re-read for level 1, exp 0,
                                           level%d.bin, equipment...

`set_vocation` (`0x02083CB0`) stores `obj+0x950 = id` and sets bit `id` in
`obj+0x954`. The runtime character object is then written back into the
roster (`0x020830DC` → `0x02086878`, 572-byte save records at `0x020F6D5C`,
vocation at +0x50).

Graft: the `ldrb` becomes `b 0x0218AD44`, where 20 bytes (the alignment
padding after the overlay's last string) draw `rand_below(12) + 1` with the
game's RNG (`0x02032380`, LCG state at `0x020EEF30`), store it at
`[sl, #0xda2]` and branch back. Everything downstream reads the drawn value.

**Measured in game**: « Guerrier » chosen → the recruit is created as **Sage**
(draw 9, id 10); the record has vocation 10, bit 10 in +0x54, and a caster's
equipment. From the same savestate the draw is always the same (the LCG only
moves when called), but it advances with every call, so two recruits in a row
differ.

### 89.4 The hero's starting vocation

> **CORRECTED the same day.** The first reading below (« Guardian until the
> fall ») watched the wrong object. It is kept struck through in the journal.

**The hero is a Minstrel from the character creation on.** The status screen
shows « Gardien Niv. 1 » during the prologue, but that is a display tied to
the story: the hero's runtime object (party member 0 = `[0x020F33D8+8]`,
object at `[member+0x150]` = `0x020F384C`, vocation at `+0x950` =
`0x020F419C`) holds 6 at the first visit of the Observatory and in front of
Yggdrasil, and **nothing writes it during the fall** (write watch through the
whole cutscene, player's save of September 25).

It is set once, at the creation: overlay 17 calls `0x020897C4(member 0,
level 1, vocation, …)` with a hard-coded **`mov r2, #6` at `0x0218BF14`**;
`0x020897C4` stores `+0x950`, sets the vocation bit in `+0x954`, level and
experience, and loads `level%d.bin`. (`0x02167204` in the battle overlay
temporarily turns the hero into a Guardian, id 0, for the prologue battle.)

`--vocation-depart` replaces the immediate with a vocation drawn from the seed
(`patch_vocations.tirer_depart`, its own generator so the other draws do not
move). **Measured**: new game on a test ROM with 9 → the object holds 9 right
after the creation; and with 9 written in RAM on the player's save before the
second offering, the fall keeps it and the status screen after waking shows
« Paladin Niv. 1 » with the paladin's skill trees.

**The Guardian's coup de grâce.** The battle overlay has three
vocation → coup de grâce tables (overlay 0, `0x02183444`, `0x02183510`,
`0x02183658`, one u16 action id per vocation 0–12). Vocation 0 gets `0x1F9`,
the same as the warrior: « Critique systématique » (Critical Claim, a
guaranteed critical hit). Names are in `data/prm/actname.nat` (English) and
`actdt_*.gp2`.

### 89.5 Locking vocations: the abbot's menu and the Voice of Vocation

The abbot's dialogue is a state machine in overlay 3 (context `sl`, state
byte `[sl+0x1f8]`, message ids written as halfwords to `[r5]` / `[sl+0x1ec]`,
ids of `data/bin/menu/str_dam.gp2`). The menu « Changer de vocation /
Renouvocation » returns 8 or 9 in `[sl+0x1e0]`, tested at `0x02156B9C`.
The game already has a refusal pattern (a cursed character, `0x02156BE4`):
message id, state 7, end of the turn at `0x02156CFC`.

Lock (`--vocations-bloquees`): at `0x02156BB0` the first five instructions of
choice 8 are replaced by `mov r1, #0x43 ; strh r1, [r5] ; mov r1, #7 ;
strb r1, [sl, #0x1f8] ; b 0x02156CFC`. Message 0x43 is appended to
`str_dam_<lang>.nat` in the five languages. **Revocation stays open**
(player's decision: it does not change the vocation, it brings a level 99
character back to level 1 in it); a first version also refused it through
the `beq` of choice 9 at `0x02156BA8`.

**The Voice of Vocation.** Flag bit 0 of `[sl+0x1fc]`, set at opening
(`0x02154988`) from a parameter of the field event (`[r7+0x1e]`,
`0x021C14F0`), switches the speaker (messages 6–0xD are shown as 0x1B–0x22,
`0x021552E0`) and **skips the menu**: « Papouz se laisse inspirer par
l'esprit des vocations », then straight to the character list. Three
« character chosen » handlers test for a curse (`bl 0x02155F88` at
`0x021569CC`, `0x02156DD0`, `0x02156FB4`, followed 16 bytes later by
`mov r2, #8`): the lock makes the test always true and the message 0x44,
the same refusal spoken by the Voice. The in-game trigger of the Voice was
not identified; it was reached by forcing the flag in RAM
(`scripts/lua/guet.lua`, `DQ9_REG=02154738:r4:1`).

**Measured in game** (work ROM, player's save): « Changer de vocation »
answers « Dans ce monde, les vocations sont scellées, mon enfant. Nul ne peut
en changer ici. Seul le rite de renouvocation reste permis. », then the
dialogue ends and the party walks away; « Renouvocation » runs as in the
original game; with the Voice forced, the Voice gives its refusal after the
character is chosen.

Message tables: `str_dam_*.nat` is `u32 count | pool_size << 12`, then
(id, offset) pairs, then the pool; `bm_*.bin` and `str_gskl_*.bin` are
record tables (header of four u32, strings are 0x67 records). Both are
handled by `scripts/textes_dq9.py`.

### 89.6 Patty's vocation menu reduced to « Random »

Patty's bar is also in overlay 3 (`bm_lui.gp2` = the bar's menus; Luida is
Patty's Japanese name). The recruit vocation menu is window 8 of
`bm_lui_wnd.bin` (x 11, y 3, w 10, h 14, 7 elements): element 37 is the
title (string 0x11 « Vocation »), elements 38–43 the six vocations
(strings 0x12–0x17). In `bm_lui_txt.bin` each element is a 0x65 record, then
a record whose **tag** is the string id, then a 0x66 navigation record (up,
down, left, right). The chosen element becomes the vocation as
`element - 0x25` (`0x02163018`), then `[ctx+0xb4]` (`0x0217E658`) and the
recruit context `[sl+0xda2]` (overlay 9, `0x02184768`).

With `--vocations-embauche`, the window keeps two elements (height 4), element
38 shows a new string 0x21 (« Aléatoire », « Random », « Zufällig »,
« Aleatoria », « Casuale ») and cannot move down. Strings 0x12–0x1D are left
alone: the bar's friend list shows each companion's vocation with them.
**Measured in game**: « Vocation / Aléatoire » in a small window, the cursor
does not move, the recruit is created as a Sage.

## §90 Monster drops drawn at every battle

### 90.1 The battle keeps only a few records, and rewrites their rates

At battle start, `0x02070CF4` copies into a small heap table (`0x02361FEC` in
our run, count 5) **only the records of the species present**, from the whole
`mon_btldata.nat` loaded in the static buffer `0x0211E33C` (header) /
`0x0211E340` (records). That buffer is reused right after; at roll time the
full file is gone.

Then overlay 0 (`0x02165A54`..`0x02165BAC`) **overwrites** fields of each
copied record from the field monster entry (`r6`, from `0x020A93AC`):
`+0x08` (exp), `+0x0C` (gold), **`+0x02` and `+0x03` (drop rate classes)**.
The item ids `+0x04`/`+0x06` are not overwritten.

**Correction to §81**: forcing the rate classes in `mon_btldata.nat`
(`scripts/rom_drops_garantis.py`) has **no effect** on field monsters — the
battle rewrites them. Measured: ROM with every class forced (common 0 =
always, rare 7 = never), the roll still uses denominators 64 and 32. The item
randomization of 1.2 is unaffected (it writes the item ids).

### 90.2 The graft

The two item reads of the roll function (overlay 23, §81) become `bl` to a
graft:

    0x021F4A10   ldrh r1, [fp, #6]   -> bl 0x021FFF40   (rare item)
    0x021F4AD8   ldrh r1, [fp, #4]   -> bl 0x021FFF48   (common item)

The graft replays the `ldrh`; if the item is not 0, it draws
`k = rand_below(1088)` and walks a compact table of the pool to the k-th item.
Mode `rares`: an item from a 4–5★ run is kept only if `rand_below(8) == 0`,
otherwise it draws again (at most 8 times). Mode `libre`: no flag, uniform.
Drop chances are untouched; an empty slot stays empty.

Table: `u16 count, u16 first id`, then one byte per run of consecutive ids —
bit 7 = 4–5★ run, bits 6–4 = gap since the previous run (7: gap in the next
byte, 255 there: u16 gap), bits 3–0 = length (0: length in the next byte).
The 1088 pool items fit in 225 (`libre`) or 278 (`rares`) bytes.

Where: **after overlay 23's BSS**. Overlays 22–30 share the slot starting at
`0x021D8A40`; overlay 24 ends at `0x02200160`, overlay 23's BSS at
`0x021FFF40`: 544 bytes. Measured: overlays 23 and 24 take turns during a
battle; what lies past overlay 23 while it is loaded is only overlay 24's
leftover, never written. To have the loader copy the graft there, the BSS
becomes data (0x560 zero bytes, which the loader would have written anyway)
followed by the graft, and `bssSize` becomes 0 — BSS addresses do not move.
Used: 172 bytes of code + 282 of table.

**Emulated** exhaustively (unicorn, `work/emu_butin.py`): for every k the graft
returns the k-th pool item in both modes; callee-saved registers and `sp`
are preserved; rejection, the retry cap, the empty slot and the rare entry
behave.

**Measured in game** (test ROM with the common roll forced to always succeed,
`mov r1, #1` at `0x021F4A74`, test only): a funghoul whose item is a
medicinal herb (22000) drops « un haut de bikini torride »; replaying the same
kill with six RNG states gives six items (velvet cape 13205, futhark staff
20400, « trident de Gracos » 20510, trident 20509, stratotoga 13022 — a 4★ that
passed the 1-in-8 filter —, traveller's gloves 15010), and the battle message
names them (« Il renferme une cape de velours ! », « … une stratotoge ! »).
