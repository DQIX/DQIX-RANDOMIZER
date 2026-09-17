# 3. First spawn patches, zone lists and the preload limit (§19–§31)

Part of the [research notes](README.md). Sections keep their original numbers.
This part is a chronological log: several conclusions here are corrected by
later sections, and the corrections are kept on purpose.

## 19. Code patch: fully random spawns

### The problem it solves

Randomizing the encounter tables only changes the **list** of species in an
area — 4 to 6 per map. In a given area you always meet the same 4 to 6 monsters,
just different from the original ones. For any monster to appear anywhere,
every time, the code has to change.

### What was replaced

`ChooseFieldMonsterId`, EUR address `0x02073FEC` (§17), 132 bytes available.
Its body was replaced with 68 bytes, 18 instructions:

```
push  {r3, lr}
mov   r0, #320          ; 320 + 10 = 330 usable species
add   r0, r0, #10
bl    #0x2032380        ; game RNG: r0 = bound in,
                        ; r0 = draw in [0, bound) out
add   r0, r0, #1
cmp   r0, #65           ; the four holes of the identifier range,
addge r0, r0, #10       ; skipped by conditional adds:
cmp   r0, #154          ;   65..74, 154..156, 209..211, 299
addge r0, r0, #3
cmp   r0, #209
addge r0, r0, #3
mov   r1, #256          ; 299 is not an encodable immediate, build it
add   r1, r1, #43
cmp   r0, r1
addge r0, r0, #1
pop   {r3, lr}
bx    lr
```

The RNG calling convention is deduced from the original code: before the `bl`,
`r0` holds the sum of weights; after it, `r0` is compared to the running sums.
So it is a `rand_below(n)`.

### Why 330 species

Identifiers 1 to 347 hold **330 valid species**, in five contiguous blocks
separated by four small holes. The conditional adds turn a draw in 0..329 into a
valid identifier, and the coverage is **exact**: 330 draws give the 330
identifiers, no duplicate and no invalid one (checked by enumeration).

Above 347 identifiers are sparse — 500-514 (legacy bosses), 600-660, 747-779,
800-801, 900 (grotto variants and test entries). Including them would need an
injected table, and the decompressed ARM9 has **no free 512-byte range**
(checked).

### Three traps

**1. `mov r0, #330` assembles to `MOVW`.** That is ARMv6T2, while the DS ARM9 is
ARMv5TE. Keystone accepts it silently and the result would crash on the console.
Hence `mov #320` then `add #10`. A guard in `scripts/patch_spawn.py`
disassembles the produced code every time and refuses `movw`, `movt`, `sdiv`,
`udiv` and the like.

**2. `cmp r0, #299` is refused.** ARM immediates are 8-bit values rotated by an
even number of bits; 299 is not one of them. Hence the scratch register.
**Rule: check every immediate above 255.**

**3. A savestate cancels a code patch.** The most expensive trap. A savestate
restores **all** RAM, code included. Loading a savestate taken on an unpatched
ROM overwrites the patched function with the original — and reading memory
showed the original code, which made the patch look broken. **A code patch can
only be tested from a cold boot, loading the game from SaveRAM.**

### What is verified

| | |
|---|---|
| the ARM9 recompresses and the ROM boots | yes (`ndspy.codeCompression`) |
| the assembled code has nothing beyond ARMv5 | yes (automatic guard) |
| the patch survives recompression | yes, read back and disassembled from the ROM |
| the patch is in RAM after a cold boot | yes, `0x02073FEC` = `E92D4008` |
| the patch is still in RAM after loading the game | yes |
| monster models load dynamically | yes, seen in game |
| **the effect on spawns in game** | **not seen** |

### Why the first patch alone was not enough — CORRECTION

Player test: the patched ROM behaved like the previous one, always the same few
species per area. The patch was in RAM.

Diagnosis by searching **callers**. An ARM `BL` is encoded `0xEB` followed by a
24-bit relative word offset; scanning the decompressed ARM9 and the 35 overlays,
`ChooseFieldMonsterId` has only **two callers**:

| Caller | Context |
|---|---|
| `0x02073CA0` (ARM9) | calls if the table pointer is not null |
| `0x021A24CC` (overlay 17) | **calls only as a fallback** |

The second is the field path, and it is conditional:

```
021a23e4  push {r4, ...}
021a23f8  mov  r4, r3        ; r4 = the function's FOURTH PARAMETER
...
021a24c4  cmp  r4, #0
021a24c8  bge  #0x21a24dc    ; if the caller gave an id, skip the draw
021a24cc  bl   #0x2073fec    ; only otherwise, draw
```

**The monster identifier is passed in by the caller**, and the drawer is only a
fallback when no identifier is available. That is why patching the drawer
changed nothing in the common case.

### The second patch: remove the short-circuit

Two instructions replaced by `NOP`s in overlay 17, at `0x021A24C4`:

```
before : cmp r4, #0 ; bge #0x21a24dc
after  : mov r0, r0 ; mov r0, r0
```

Every spawn then goes through the drawer. The NOP used is `mov r0, r0`
(`0xE1A00000`) and not the dedicated `NOP` (`0xE320F000`), which is ARMv6K and
does not exist on the DS ARM9.

**Writing an overlay with ndspy.** `Overlay.data` is decompressed;
`Overlay.save(compress=True)` returns the compressed bytes, to put in
`rom.files[overlay.fileID]`. The overlay table **must also** be updated: the last
word of the 32-byte entry holds the compressed size on 24 bits plus 8 flag bits.
Without that update, the overlay is loaded with a wrong size. Here recompression
happened to give the same size (200,184 bytes), but do not count on it.

## 20. Why "random at every spawn" looked impossible

Player feedback after three versions: each area keeps its set of species. The
code patches changed nothing. Here is why, established by measurement.

### The decisive experiment

From a savestate taken on an open plain, the patch is written **directly in RAM**
from Lua — which gets around the savestate cancelling a ROM patch — to force the
drawer to always return the same species. Then we walk and count calls to the
drawer with `event.onmemoryexecute`.

| Forced species | Monsters on screen | Calls to the drawer |
|---|---|---|
| **1** (declared by the area) | appear immediately, battle starts | **2** |
| **200** (not declared by the area) | **no monster** | **3,629** |

### What this establishes

**The engine can only spawn species whose 3D model it preloaded when the map
loaded**, and that preload list is the area's table. When the drawer returns a
species outside the list, the spawn fails and the game **retries in a loop** —
hence 3,629 calls against 2.

Variety per area is bounded by the **size of the table**, not by chance. No
drawer patch can get around it: models would have to load on demand, a whole
other project (memory budget, asset loading). *(Which is what versions 1.0 and
1.1 eventually did, §65–§78.)*

### The real ceiling, and the lever

| File | Situation |
|---|---|
| `encmons.bin` | **564 free slots** over 209 maps: most use only 5 of 8 |
| `encfld.bin` | 5 entries per area on average, but **some areas have 13** |

Filling `encmons.bin`'s free slots raises declared variety from **4.3 to 6.7
species per map** (`scripts/remplir_zones.py`). *(Later found to be wrong: field 1
of `encmons` is a position gate, not a free slot, §24.)*

### Two method limits

- **A frozen savestate hides table changes.** The RAM table is built when the map
  loads; a savestate restores it as it was. File changes only show after a zone
  reload.
- Checking that a patch is *present* says nothing about it being *useful*. Calls
  had to be counted and the screen watched.

### Status of `--spawn-libre`

Kept but **not recommended**: it produces empty plains and a retry loop. Its code
path is correct — model preloading is what defeats it.

## 21. Per-area structure of `encfld.bin`, and the cap of 6

### The hierarchy, from sequential reading

```
tag 0x69 (5 fields)   AREA HEADER, field 0 = map identifier
  tag 0x68 (1 field)  start of a GROUP
  tag 0x66 (1 field)  group parameters (bit field)
  tag 0x67 (2 fields) an ENTRY: 12-bit identifier, 3-bit weight
  tag 0x67 ...
  tag 0x68            next group
tag 0x69              next area
```

An area holds **several groups**, each with its own species list. Map 20001 has
three, with 4, 4 and 3 entries.

**This explains the `count=4` read in RAM** (§18): the loaded table is **one
group**, not the whole area. The game picks a group — by sub-sector or by a
criterion in the tag `0x66` bit field — and that group becomes the spawn table.

### The cap is 6, established twice

**By code.** Function `0x02073ED4`, which prepares the selection, reserves `0x30`
bytes of stack and builds **two candidate arrays** at `sp+0` and `sp+0x18`: 24
bytes each, so **6 entries of 4 bytes**.

**By data.** Entries per group in vanilla, over the 287 groups of `encfld.bin`:

| entries | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| groups | 21 | 39 | 66 | 66 | 88 | 7 |

Max 6, mean 3.6. *(The code reading was wrong, see §23: those arrays hold group
keys. The cap of 6 entries per group is real, but comes from `AddGroup`, §24.)*

### The enlargement

`scripts/agrandir_zones.py` brings each group to **exactly 6 entries**, adding
`0x67` records. The file goes from 23,072 to 31,220 bytes and from 1,827 to 2,506
records; the header is updated (`count` and data size), and the 52 unparsed
trailing bytes are kept as is.

### The species pool, and excluding bosses

Draws only use species the game **already** uses as field symbols (260), minus
those appearing in a scripted battle (5 overlap): **255 species**.

Two guarantees: no boss, and every species has already proven it can be placed
as a symbol. The 77 species that only appear in battle groups (`Pandora's box`,
`stone golem`, `cyclops`…) are left out, not knowing whether they have a field
model.

"Appears in a scripted battle" is not an exact definition of "boss": the
prologue battle uses `slime` and `bodkin archer`. Excluding them costs 5 species
out of 260.

### `encbtl.bin` left alone, and why

A first count gave a maximum of 12 entries per group for this file. **That count
was wrong**: it added group headers to entries. Enlarging on that basis pushed
groups to 16 entries, beyond anything the game does. With no established cap, we
do not touch it — and it is battle composition anyway, not visible symbols.

### Checks on the produced ROM

| | |
|---|---|
| groups after processing | **287 groups, all at exactly 6** |
| header consistent | `body + data_size == file_size` |
| invalid identifiers written | **0** |
| `encbtl`, `encmons`, `mon_btldata` | bit-identical |
| boot and game load | checked |

## 22. Lifting the cap of 6, and the field / boss split

### The cap is not in the format, it is in a stack frame

Function `0x02073ED4` builds two candidate arrays on its stack frame and has **no
bound check**:

```
02073f68  str r1, [fp, r7, lsl #2]
02073f6c  add r7, r7, #1            ; no check on r7
```

The frame is `0x30` = 48 bytes, two 24-byte arrays = 6 entries of 4 bytes. The
frame is used in only six places, all checked by disassembly. Four are enough to
resize it:

| Address | Role | 6 entries | 12 entries |
|---|---|---|---|
| `0x02073ED8` | allocation | `#0x30` | `#0x60` |
| `0x02073EF8` | array 1 base | `#0` | unchanged |
| `0x02073F7C` | array 2 base, write | `#0x18` | `#0x30` |
| `0x02073FB8` | array 1 base, read | `#0` | unchanged |
| `0x02073FD4` | array 2 base, read | `#0x18` | `#0x30` |
| `0x02073FE4` | release | `#0x30` | `#0x60` |

`scripts/patch_capacite.py` does it for any capacity, with a guard: it refuses to
patch if the instruction read is not the expected one. *(Useless, see §23.)*

**Not guaranteed**: that the game can preload twelve monster models instead of
six. The emulator faithfully reproduces the DS's 656 KiB of VRAM, so that limit
does not go away in emulation. Failure modes would be visible: invisible
monsters, corrupted textures, or a crash when loading an area.

### The field / boss split — corrected twice

The player saw bosses on the field. Two successive causes.

**Cause 1.** Boss exclusion only applied to entries **added** by the enlargement.
Existing entries were rewritten by a permutation over the whole bestiary, so a
field slot could receive anything. Fix: permute within separate sets.

**Cause 2.** The first split defined the field pool as "species that roam,
**minus** those in a scripted battle". The 5 overlapping species therefore moved
into the boss pool, and the boss permutation turned them into `Dragonlord`,
`Malroth`, `Barbarus`… in field slots.

The right criterion is the reverse:

```
field_pool = species used as a field symbol in vanilla      (260)
boss_pool  = scripted battle species that NEVER roam        (101)
```

**A species that roams in vanilla is a field species**, even if it also appears
in a scripted battle — the game itself places it as a symbol, so it has the model
and the right. The two sets are disjoint, and permuting within each guarantees a
field slot never gets a boss.

Checked on the produced ROM: **0 boss** in `encfld.bin` and `encmons.bin`, as in
the original.

### Two settings that change perceived variety

**Weights.** Each entry has a 3-bit probability. In vanilla, the most likely
species of a group takes **36 %** of spawns, and 3 species out of 4 cover 80 %.
Adding entries without touching weights leaves the original species dominant.

Equalizing all weights of a group (`POIDS_UNIFORME = 4`) makes every species
equally likely:

| | Most likely species | Species covering 80 % of spawns |
|---|---|---|
| original (4 entries) | 36 % | 3 of 4 |
| capacity 12, original weights | 14 % | 8 of 12 |
| capacity 24, equal weights | **4.2 %** | **20 of 24** |

**Duplicates.** The first draw ignored the group's content: `froicoucass` ended
up twice in the same area, wasting a slot. The draw now excludes species already
present.

### The weight IS the rarity — never equalize it

Raised by the player and confirmed by measurement. Weights are not a variety
setting, they are **encounter rates**, and they encode the game's experience
economy.

| Median vanilla weight | Species | Median XP |
|---|---|---|
| 1 | 4 | **23,100** |
| 2 | 16 | 1,035 |
| 3 | 36 | 364 |
| 4 | 46 | 423 |
| 5 | 69 | 580 |
| 7 | 28 | 795 |

The whole metal family is at 1 or 2: `liquid metal slime` (40,200 XP),
`platinum king jewel` (43,392 XP), `metal king slime` (54,504 XP). Their rarity is
their whole point.

An intermediate version equalized weights at 4 to maximize perceived variety.
**That was a mistake**: it turned every experience jackpot into a common monster,
i.e. an XP farm.

### The fix: a rarity per species

`construire_rarete()` computes, for each species, the median of its vanilla
weights. That rarity is applied **after the permutation**, based on the species
actually in the slot — a metal slime stays rare wherever it goes.

Checked on the produced ROM, capacity 24: **0 entries** whose weight does not
match its species' rarity.

| Species | Weight | Chance per encounter | XP |
|---|---|---|---|
| `liquid metal slime` | 1 | 0.88 % | 40,200 |
| `platinum king jewel` | 1 | 0.89 % | 43,392 |
| `metal king slime` | 2 | 1.85 % | 54,504 |
| common species | 7 | 6.36 % | — |

**Side effect.** These rare species now appear in 22 to 29 areas each, against 1
to 5 in vanilla. Per-encounter rarity is kept, but they can be met in many more
places.

## 23. CORRECTION of §21 and §22 — what I had misunderstood

Established by targeted disassembly.

**`0x02073ED4` does not build the monster table.** It picks **one group** among
the area's groups, and its two stack arrays hold **group keys**, not monster
entries. Vanilla never goes above 4 groups per area, against a code cap of 6:
those arrays are never full.

**Consequence: `scripts/patch_capacite.py` never unlocked nor broke anything.**
It enlarged a buffer unrelated to the number of species. The two "6"s — six
entries per group and six keys per array — were a coincidence, and I took it for
a confirmation. The script is kept for the record but removed from the
randomizer.

## 24. The real chain, and the three caps

```
encmons.bin --parse--> u16 ids[12] + u16 count          (mapstruct+0x44)
                              |
                              +--> model collections (mapstruct+0x2F8, +0x304)
                              |
encfld.bin  --parse--> EncGroupSet : 6 slots of 32 bytes (mapstruct+0x60)
                              |
    0x02073ED4 (picks ONE group) --> 0x02073FEC (weighted lottery)
                              |
                              v  monster identifier
              0x021A2128 (overlay 17) : SPAWN
                |- model missing from mapstruct+0x2F8 ? -> return 0
                +- model missing from mapstruct+0x304 ? -> return 0
```

| Cap | Where | Value |
|---|---|---|
| entries per group | 32-byte slot allocated by `AddGroup` (`0x0209BD50`, `lsl r4, r0, #5` then `memset 0x20`) | **6** |
| species preloaded per map | `cmp r3, #0xc` at `0x0209C0A0` | **12** (the file only gave 6) |
| groups per area | `cmp r0, #6` at `0x0209BD60` | 6 (vanilla: 4 at most) |

**`AddEntry` (`0x0209BE54`) has no bound check**: it writes `count = n+1`
without checking. Entries 7 and above overflow into the next group's slot, which
the next `AddGroup` immediately zeroes. Declaring 24 entries only keeps the first
6 — and corrupts the neighbour along the way. That was the flaw of the 24-entry
version.

### The invariant the game keeps

**A species can only spawn if it is in the map's `encmons.bin` list.** The check
is a plain `return 0` in the spawn code. And vanilla respects
`union(species of an area's groups) ⊆ encmons list` on **208 maps out of 208**.

Randomizing the two files **independently** breaks this invariant: that alone
explains why all previous work had no effect. In the 24-entry version, the
intersection dropped to 2 to 4 species actually spawnable — exactly the "4 to 6"
the player observed.

### Two `encmons.bin` traps

**Field 1 is not a free slot, it is a position gate.** A non-zero value **disables
the whole record**, without adding any species. That is what my filling attempt
overwrote, and it finally explains why no monster appeared anywhere anymore.

**A zero in fields 2 to N is skipped, not a terminator.** A partly filled list is
perfectly legitimate.

## 25. The chosen fix: resynchronization, with no code patch

`scripts/resync_zones.py` rebuilds both files together:

1. per area, pick a set of **8 species** (≤ 10; the code cap is 12 but overlay 17
   adds 1 to 4 hard-coded ones, silently lost if the list is full);
2. split it into **groups of at most 6 entries**, never more;
3. make **every group unconditionally eligible** — bits 0-2 of the group
   parameter to 2 ("always" predicate), bits 13-20 to 0 ("always" mask), cadence
   kept — so the selector can draw any of them at any time instead of freezing
   one;
4. write **exactly the same set** into `encmons.bin`, restoring the invariant by
   construction.

Measured result, starting area:

| | Species | Groups |
|---|---|---|
| original | 6 | 3 |
| after | **8** | 2 |

Checks, all in line with vanilla: entries per group **6 at most**, `encmons`
**8 at most**, non-zero position gates **1** (the same as vanilla), invariant
violations **2** (the same as vanilla), bosses on the field **0**.

### Why we stop there

Going from 6 to 14 entries per group would need the container stride to change
from 32 to 64 bytes. But `FindGroupByKey` (`0x0209BDA4`) is called from 9 sites,
four of them in the `encbtl.bin` parser: changing the stride would break
`encbtl`. And going above 12 preloaded species would need map structure members
to be relocated, the list having only **2 bytes of margin** before the
`EncGroupSet`.

Not checked: whether the 192 KiB model budget (`mov r0, #0x30000` at
`0x021A2928`) holds 8 to 10 models.

## 26. Drawing at zone load (v14)

The cap of 12 preloaded models cannot be bypassed. What can change is **what goes
into those 12 slots, and when**. Two grafts, applied by `scripts/patch_hasard.py`:

| | Where | What |
|---|---|---|
| A | the 2 `bl AddSpecies` of the `encmons` parser (`0x0209BFD8`, `0x0209BFF0`) | replaces the file's identifier with a draw from a 260-species bitmap |
| B | the body of `ChooseFieldMonsterId` (`0x02073FEC`) | returns a species taken **from the preloaded list**, instead of the weighted table |

B makes the parsing order of the two files irrelevant: when the draw happens,
both structures were built long ago.

Findings that simplified everything:

- **`0x02032380` = `rand_below(max)`**, the game's generator, called by the
  original drawer. No need to embed one.
- **`0x02109BC8`**: `[[0x02109BC8]]` is the preload list, u16 ids at `+0x00`,
  count at `+0x18`. The first pointer lives in **DTCM** (`0x027E3200`), which
  BizHawk's "System Bus" domain does not cover — it returns 0 there without an
  error, and three times I thought the graft did not work.
- Graft B fits in **56 bytes** out of the original function's 132.

Bosses are absent from the bitmap: excluding them costs no instruction.

## 27. THE TRAP THAT COSTS A DAY: `CompressedStaticEnd`

**Recompressing the ARM9 after changing it makes the ROM unbootable**, and the
symptom has nothing to do with the patch: PC stuck at **`0xFFFF0108`** — the ARM9
BIOS exception vector — within the first second, white screen, before the title.

The cause is in `ModuleParams`, at `nitrocode - 0x1C` (magic `0xDEC00621` at
offset `0xBBC`):

```
+0x00 AutoloadListStart     0x020F4600
+0x04 AutoloadListEnd       0x020F4618
+0x08 AutoloadStart         0x020F2E60
+0x0C StaticBssStart        0x020F2E60
+0x10 StaticBssEnd          0x021536E0
+0x14 CompressedStaticEnd   0x0209BD08   <-- = 0x02000000 + 638,216
+0x18 SDKVersion            0x04027539
```

`CompressedStaticEnd` holds the end of the BLZ stream, i.e. **exactly the length
of the original stream**. ndspy does not update it. As soon as the content
changes, the recompressed stream changes size and the game's decompression stub
works on a wrong end.

What misled me: a decompress/recompress round trip **with no change** gave
638,216 bytes, the same size, and booted fine. I concluded the chain was sound.
It took writing **64 bytes of bitmap into padding** — no instruction, no code
called — to see the same ROM refuse to boot, and understand it was not the graft.

**The fix**: set `CompressedStaticEnd` to zero and store the ARM9 uncompressed.
The stub then skips decompression. The ARM9 grows from 638 KiB to 1,001 KiB,
absorbed by the 10 MiB of cartridge padding: the produced ROM is still
268,435,456 bytes. Only visible effect, the `.xdelta` patch grows from 19 KiB to
571 KiB.

## 28. The freeze on the first step out of town

Reported by the player on the first v14. Reproduced, PC read: **`0xFFFF0108`**,
the ARM9 BIOS exception vector — a **data abort**, not a loop.

Graft B followed the parser's chain of globals, `[[0x02109BC8]]`. The first link
lives in DTCM (`0x027E3200`), and the second is **0** as soon as no map with
encounters is loaded. `ldrh r0, [r4, #0x18]` then read address `0x18`. I tested
the species count but **never the pointers**.

**Fix**: no chain at all. Graft A gets the list as an argument — always valid —
and stores it in a word at `0x020E7368`, in the same free area. Graft B reads
that single word and tests it for null; at zero it returns -1, exactly what the
original returns when no entry fits. Callers handle it (`cmp r5, #-1 ; beq`).

### The harness that made it visible

The savestate remains the fastest tool, if you know what it does: it restores all
RAM, **code included**, so it cancels the patch. So we reload it, then **rewrite
the patch's 58 words in RAM** (`memory.write_u32_le`) right after. We are on the
plain with the patched version, without having to leave town.
`scripts/lua/gel_v14.lua`.

Result: freeze reproduced at step 2 with the faulty version, 30 steps without
incident with the fixed one.

### Not checked in the lab

Graft A only runs **when a map loads**, and the harness never crossed a zone
boundary. Graft A did run at boot and when loading the game — several maps —
without incident, but the combination "random list **then** drawing from it on
the field" was only exercised by the player.

## 29. WRONG — what I believed about the model buffer

**This section used to say that the 192 KiB at `0x0211E33C` bounded a map's 12
models, so the cap was a memory one. That is wrong**, established by disassembly.

This buffer is a **work buffer**. It receives the table of contents of the
`data/pack_lv5/enemy.gp2` archive, then **the current member, at the same place
on every loop iteration**:

```
021a2958  ldr r5, [sp, #0x30]     ; bytes taken by the TOC, once
021a29e8  add r2, r2, r5          ; SAME destination every iteration
021a2a30  bl  #0x2075664          ; decompress to the HEAP, that is what survives
021a2ad8  bl  #0x20d962c          ; the archive is closed
```

`r5` is never rewritten in the loop. And `0x0203D038` **reopens the same archive
into the same buffer mid-game**, which would be impossible if it held persistent
models.

The `cmp sb, r1 ; bhi` at `0x020D92BC` I quoted compares the size of the
**archive's table of contents** to the buffer, not the total size of the models.
The largest field member is 44,220 bytes, 23 % of the buffer.

**And there is no memory cap constant.** The model heap is created at map load
taking *all remaining free space*, and the remainder goes to the next heap:

```
021a30b8  bl 0x2032804    ; GetTotalFreeSize(map+0x1244) -> all free space
021a30e0  bl 0x2032500    ; CreateExpHeap(map+0x113C, block, r5)
021a30fc  bl 0x21a28a8    ; preload
021a3108  bl 0x2032804    ; what is left
021a312c  bl 0x2032500    ; CreateExpHeap(map+0x11C0, rest)
```

*(`0x02032500` is later found to create a **frame** heap, not an ExpHeap, §47.)*

My measurement of "552 KiB free, largest range 132 KiB" is still right, but it did
not measure what I thought: RAM is taken by heaps, not by a model pool to enlarge.

## 29 bis. ARCHIVE of the wrong version (kept for the record)

At 12 species per area, some monsters no longer appear, and some show up after a
battle. Not a patch bug: the model buffer overflows, and VRAM is freed then
reloaded after the battle.

The buffer is **fixed and passed as an argument** by overlay 17:

```
021a2928  mov r0, #0x30000       ; size   -> [sp, #4]
021a2940  ldr r3, [pc, #0x1c8]   ; base = 0x0211E33C
021a294c  bl  0x020d91ec         ; PrepareModelSet(..., base, size, &used)
021a2960  rsb r0, r5, #0x30000   ; space left
```

And in `0x020D91EC`:

```
020d92bc  cmp sb, r1             ; required size vs max size
020d92c0  bhi failure            ; does not fit -> give up
020d92d0  addne r0, r5, r1       ; otherwise place at the END of the buffer
020d92d8  subne r5, r0, sb
```

Three values to change, one of them a base: technically a three-word patch.

**Except there is nowhere to put it.** Main RAM map in game
(`scripts/lua/arpente_ram.lua`), pages never touched from boot to a walk:

| | |
|---|---|
| total free | 552 KiB, **fragmented** |
| largest contiguous range | `0235F000-0237FFFF`, **132 KiB** |
| second | `023A9000-023C8FFF`, 128 KiB |
| current buffer | **192 KiB** |

The largest free range is **smaller than the existing buffer**: it cannot even be
moved at the same size. Behind it, 21 KiB of BSS remain before `StaticBssEnd`
(`0x021536E0`), +11 % — pointless.

And a second wall follows: model registration (`bl 0x2036814`, failure -> code 3)
works in **VRAM**, 656 KiB wired, shared with everything on screen.

**Measured conclusion (at the time)**: the cap is not a constant to flip. Crossing
it would need freeing hundreds of kilobytes of main RAM *and* VRAM. The useful
setting remains `--especes`, working point between 8 (valid) and 12 (overflows).

## 30. The on-demand loader already exists in the game

Established by disassembly. Two paths, both active during play.

### Asynchronous — the resource request manager

| Item | Address | Evidence |
|---|---|---|
| manager pointer | `[0x02104304 + 4]` | `0202F7BC` |
| request queue | `mgr+0x128`, 0x44-byte entries | `0202FAB4` |
| queue cap | **24** | `0202FA9C cmp r0,#0x18` |
| enqueue (archive member) | `0x0202FD3C(mgr, archive, member, heap) -> id u16` | type 2 |
| poll | `0x0202FDE0(mgr, id) -> 1 / 0 / -1` | ready / waiting / error |
| fetch | `0x0202FED8(mgr, id, void** p, u32* n)` | |
| full purge | `0x0202F7B8` -> `0x02030120` | |

**Reference client: overlay 14**, the monster list. It requests `"%s.mon"` in
`data/pack_lv5/enemy.gp2` (`0x0218521C`), polls, fetches, then `0x0207551C` to
extract `.cchr` / `.cmot` / `.bact`, `0x02075664` to decompress and `0x02036814`
to register — **one monster at a time, outside map loading**.

### Synchronous — `0x0203D038`, the field actor loader

A single caller: `ovl17 @0x021A2EA4`. The `cmp r0, #5` case is the monster model.
It **reopens `enemy.gp2` mid-game** (`0x0203D4F0`).

**Trap**: `0x0203D4A0` purges the async queue before the synchronous open. The two
paths do not coexist.

### The building blocks

- `0x02075664` = `LZ77DecompressToHeap(heap, src, u32* size)`. The decompressed
  size is `word >> 8`; decompression is the BIOS `svc #0x11` (`0x020006CC`),
  synchronous, RAM to RAM.
- `0x0207551C` opens the `.mon` as a NARC archive and filters the name with
  `strstr`.
- `0x02036814` registers the model.

### Where models live

`data/pack_lv5/enemy.gp2`, 15,843,860 bytes, **601 members**: `<code>.mon` (312,
full version) and `<code>_f.mon` (289, **field version**). Members are not
compressed at the GPC2 level — they are NARC archives whose `.cchr` and `.cmot`
files are LZ77-compressed.

**Latent bug in `scripts/gp2.py`**: the index size field carries flags in its high
byte, it must be masked with `0x00FFFFFF`. Without it the reader computes sizes of
419 MiB.

Cost of a field model, measured over the 289 `_f`:

| | min | med | p90 | max |
|---|---|---|---|---|
| member in the archive | 3,392 | 12,076 | 22,544 | 44,220 |
| decompressed `.cchr` (RAM) | 5,508 | **18,320** | 29,820 | **61,368** |

## 31. Field measurement: what v14 really does

Savestate taken by the player **on an open plain, on the v14 ROM itself**. The
tool missing from the start: the automatic harness cannot leave town, and a
savestate taken on another ROM cancels the code patch.

```
map = 020FDD44
preload list = 8 species : 119, 217, 251, 120, 111, 150, 113, 116
model slots used : 7, 8, 9, 10, 11, 12, 13, 14   -> 8 of 8
free slots behind: 15, 16, 17, 18
```

Two conclusions:

- **graft A works**: the list's 8 species are a draw, and the 8 matching models
  are loaded;
- **4 slots remain free** out of the 12 scanned by `FindLoadedModelSlot`
  (`0x021A277C cmp r5,#0xc`). The refusal at 10 species does not come from the
  number of slots.

*Not measured: free space in the model heap. Searching RAM for the ExpHeap
signature returned nothing in either endianness, and `[map+0x113C]` is not a RAM
pointer — either the offset differs, or the parser's map structure is not overlay
17's.*

### Why a monster is invisible

A species can be in the `map+0x2F8` and `map+0x304` containers — so pass both
spawn rejection tests (`0x021A2180`, `0x021A218C`) — **without its model being
loaded**. Record present, model absent: the symbol exists, nothing is displayed.
Raising `--especes` creates ghosts.
