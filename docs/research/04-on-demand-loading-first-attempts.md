# 4. On-demand model loading, first attempts (§32–§46)

Part of the [research notes](README.md). Sections keep their original numbers.
Section §47 (next file) corrects several conclusions made here.

## 32. The full toolbox for on-demand loading

Every building block is identified. Only the glue code is missing.

### Loading

| Function | Signature | Evidence |
|---|---|---|
| `0x0202FD3C` | `(mgr, archive, member, heap) -> id u16` | asynchronous enqueue, type 2 |
| `0x0202FDE0` | `(mgr, id) -> 1 / 0 / -1` | ready / waiting / error |
| `0x0202FED8` | `(mgr, id, void** p, u32* n)` | fetch |
| `0x0203D038` | synchronous actor loader, case `type == 5` | single caller: `ovl17 @0x021A2EA4` |
| `0x0207551C` | `(blob, name, ...)` | opens the `.mon` as NARC, filters with `strstr` |
| `0x02075664` | `(heap, src, u32* size) -> void*` | BIOS LZ77 (`svc #0x11`) to the heap |
| `0x02036814` | model registration | 46 callers |

### Freeing — the missing piece

| Function | Signature | Evidence |
|---|---|---|
| **`0x02032628`** | **`HeapFree(heap, ptr)`** | in the queue purge `0x02030120`: `ldr r0,[r4,#0x34]` (heap), `ldr r1,[r4,#0x38]` (data), `bl 0x2032628`, then the field is zeroed |
| `0x02032554` | `HeapAlloc(heap, n)` | 1,081 callers |
| `0x02032500` | `CreateExpHeap(handle, block, n)` | *(actually a frame heap, §47)* |
| `0x02032804` | `GetTotalFreeSize(handle)` | compares the magic to `0x45585048` |

### Model slot table

| Function | Signature |
|---|---|
| `0x0200F398` | returns the table (base `0x020F33D8`, entries at `+8`, **233** slots) |
| `0x0200FD48` | `SetSlot(table, i, obj)` — writes `table[i]` and `obj->4 = i` |
| **`0x0200FD58`** | **`ClearSlot(table, i)`** |
| `0x0200FD68` | `ResetTable(table)` — `memset(table+8, 0, 0x3A4)` |
| `0x0200FD80` | `GetSlot(table, i)`, bounded at 233 |
| `0x021A27E8` | **`ClearAllMonsterModelSlots()`**: clears slots **7 to 18** then calls `0x02057F10` for indices **120 to 139** (20 slots, probably textures). Called at the start of the preloader. |

Field monster models occupy slots **7 to 18**; `FindLoadedModelSlot`
(`0x021A277C cmp r5,#0xc`) only scans those 12.

### Containers checked by the spawn

| Container | Kind | Capacity | Source |
|---|---|---|---|
| `map+0x2F8` | array of **0x1C**-byte records, allocated as one block | **512** (`0x0206F324 cmp r7,#0x200`) | `mon_data_<LG>.nat` |
| `map+0x304` | linked list (u16 key at `+0`, next at `+0x10`) | none | `data/prm/fld_mondata.bin` |

Useful fields of the `+0x2F8` record: `+0x04` = **model code** (string, used for
`sprintf("%s_f.mon")`), `+0x08` = search key, `+0x0C` and `+0x0E` = two shorts
read back at spawn (`0x021A22C8`, `0x021A22D8`). The transit buffer feeding them
is **0x18 bytes**, i.e. 12 u16 (`0x021B52B8`), and **that** is the real
bottleneck — not the container.

### Where to put the code

| Option | Verdict |
|---|---|
| ARM9 padding outside BSS | **406 bytes in total**, 280 already used by v14. The 3 ranges: `0x020E7268` (280), `0x020F1E40` (72), `0x020F1D2C` (54) |
| append to the end of the ARM9 | **impossible**: crt0 zeroes `0x020F2E60` to `0x021536E0`, which would erase the code |
| overlay 17 padding | **zero bytes**; binaries are packed |
| enlarge overlay 17 | **impossible**: the 1,888 bytes behind it are exactly its BSS, and overlays 22 to 31 start right after, at `0x021D8A40` |
| **ARM9 dead code** | **13.5 KB** over the 10 largest functions never called nor referenced |

The largest: `0x0200341C` (2,080 bytes), `0x02002CB8` (1,888), `0x0200702C`
(1,732), `0x0204C044` (1,500), `0x0200884C` (1,368).

*Caveat: the criterion is "no branch target, and no word of the binary equals an
internal address". It does not cover references built with `add rX, pc, #imm`
nor tables built at run time. To validate in game before putting useful code
there.*

### The plan

1. **Fill the containers with the 260 species** at map load. They accept 512; the
   construction just needs the full list instead of the 12-entry buffer. Cost:
   260 x 0x1C = 7.3 KiB on the map heap.
2. **At spawn**, if the species' model is not loaded, load it on the spot —
   `0x0207551C` + `0x02075664` + `0x02036814` — into one of the 12 slots.
3. **Evict** the least recently used: `ClearSlot` + `0x02057F10` for the texture
   + `HeapFree(map+0x113C, ptr)`.

Trap already identified: bypassing the two spawn rejection tests without
providing the records causes a read at address `0x0C`. Same family as the v14
freeze.

## 33. Hunting dead code does not work — and what to do instead

The static criterion "no branch target, no word of the binary equals an internal
address" gave 23 ARM9 functions and 13.5 KiB. **It is wrong.**

In-game check (`scripts/lua/valide_code_mort.lua`): each region is filled with
`b .` — a branch to itself — from the field savestate, then we play while
watching the program counter. A live region freezes the game immediately and
the PC ends up inside it, which gives it away.

| Region | Verdict | When |
|---|---|---|
| `0x0204C044` | **live** | from the first frame |
| `0x02017DA4` | **live** | from the first frame |
| `0x02005AC8` | **live** | after ~50 s of walking |
| `0x0200341C`, `0x02002CB8`, `0x0200702C`, `0x0200884C`, `0x020026B8`, `0x020076F4` | not hit yet | idle + 30 walking loops |

**The lesson is in the third row.** A region can look dead for fifteen seconds
and be called the next minute. During my tests the game never had the chance to
open a menu, enter a battle, save or play a cutscene. No test duration will prove
a region is dead; it only proves it is not.

These addresses all fall in `0x02002000`-`0x02009000`, which looks very much
like the C runtime — `printf`, conversions, floats. Code called through pointers,
exactly what the static criterion cannot see.

### The right source of space: the preloader itself

On-demand loading **makes the preloader useless**. Its function, `0x021A28A8`, is
about 600 bytes in overlay 17 — exactly where the code must live, and exactly the
code being replaced. The space freed is the space needed.

Also available, safely:

| Location | Size |
|---|---|
| body of `0x021A28A8` (the preloader) | ~600 bytes |
| rest of `ChooseFieldMonsterId`'s body, already replaced by graft B | 72 bytes |
| ARM9 padding `0x020F1E40` and `0x020F1D2C` | 126 bytes |

None of these is code of unknown use: they are functions whose role is known and
which we deliberately remove. That is the difference between reclaiming space and
hoping nobody uses it.

## 34. How to fill the containers with the 260 species

The construction is fully decoded, in `ovl17 @0x021B5250` (called when the
asynchronous request for `mon_data_<LG>.nat` completes, state 2):

```
021b52ac  ldr r6, [r5, #8]        ; r6 = map
021b52b0  add r0, sp, #0x18       ; local buffer...
021b52b4  mov r1, #0x18           ; ...of 24 bytes = 12 u16
021b52b8  bl  0x200f374           ; zeroing
021b52bc  add r1, sp, #0x18
021b52c0  add r0, r6, #0x44       ; the preload list
021b52c4  bl  0x209c0d0           ; CopyList(list, buffer) -> count
021b52d0  asr r7, r0, #0x10       ; r7 = count
021b52d4  add r0, r6, #0x2f8 ; bl 0x206efd4    ; clears the container
021b52e0  add r1, sp, #0x18 ; stm sp, {r1, r7} ; arguments: buffer, count
021b5308  bl  0x206f240           ; builds the container
```

`0x0209C0D0` is `CopyList(src, dst) -> count`: a `ldrh`/`strh` loop bounded by
the count at `src+0x18`.

**The bottleneck is the 24-byte local buffer, nothing else.** The container
accepts 512 species (`0x0206F324 cmp r7,#0x200`), and `0x0206F240` fetches each
species' model code from `mon_data_<LG>.nat`, which holds all 438.

### The graft

No need to enlarge the stack frame: just provide another buffer.

1. replace `bl 0x209c0d0` (`0x021B52C4`) with a call to a graft that **allocates
   520 bytes** on the map heap (`HeapAlloc`, `0x02032554`; the heap is already
   loaded at `0x021B52FC` by `ldr r1,[r2,#0x10]`), writes the **260** identifiers
   by expanding the 64-byte bitmap already present, keeps the pointer in a static
   word and returns 260;
2. point both `add r1, sp, #0x18` (`0x021B52BC` and `0x021B52E0`) at that word —
   a `ldr r1, [pc, #x]` is enough, the word living in overlay 17 itself, within
   the 4,095 bytes of a pc-relative offset;
3. free after `0x021B5308` with `HeapFree` (`0x02032628`).

Same operation for `map+0x304` in the neighbouring function, `0x021B5348`, which
reads `data/prm/fld_mondata.bin`.

Cost on the map heap: 260 x 0x1C = 7.3 KiB of records, plus the duplicated
strings, about 10 KiB.

**What this graft gives alone**: spawn accepts any species, and graft B can draw
from the 260. But the model is still not loaded, so many monsters would be
invisible. It is a verifiable intermediate step, not a playable version — the
next step (on-demand loading) is required.

## 35. Step 1 built: `scripts/patch_conteneurs.py`

Three patches, checked by disassembling the produced ROM:

```
ovl17 0x021B52C4   bl 0x209C0D0        -> bl 0x020E7308   (graft C)
ovl17 0x021B52E0   add r1, sp, #0x18   -> ldr r1, [sp, #0x18]
ARM9  0x020E7308   graft C, exactly 96 bytes, no literal
```

The graft allocates 1,024 bytes on the map heap (`[map+0x10]`, the same one
already passed to the constructor), expands the 260-species bitmap into it, puts
the pointer in the first word of the local buffer and returns the count. The
post-indexed `strhne` avoids a branch in the loop — that is what makes it fit in
the 96 free bytes behind graft A.

Two traps paid along the way:

- **1,032 is not an encodable ARM immediate** and keystone answered with a
  `MOVW`, absent from ARMv5TE. The guard stopped it. The buffer is therefore
  1,024 bytes (`0x400`), which covers the worst case of 512 u16.
- **ndspy's `Overlay.save()` returns the overlay's DATA, not its table entry.**
  Joining them to rebuild `arm9OverlayTable` makes an 11 MB "table" and
  `saveToFile` fails with an `IndexError`. The table is rebuilt with
  `ndspy.code.saveOverlayTable(overlays)`. Overlay 17 is now stored uncompressed,
  314,688 bytes instead of 200,184 compressed.

### What the harness cannot measure

Global `0x02108D14` holds the container's address (`0x0206F24C ldr r3,[pc]`;
`str sl,[r3]`). It does give `0x020FE03C`, i.e. `map+0x2F8` with
`map = 0x020FDD44` — the same map as in the field savestate.

But its three words are **zero**, and **they are on v14 too**. The container is
simply not populated where the harness is: the savestate starts in a Stornway
building, and a map without encounters has no monster container. The reading is
worthless there, for v17 as for the control.

**Method conclusion**: step 1 is not observable alone. Nor is it playable alone
— spawn would accept every species without their model being loaded. Steps 1 and
2 therefore form **a single testable batch**, and must be delivered that way.

## 36. Step 2: the invisible monster mechanism, instruction by instruction

Confirmed in spawn `0x021A2128`:

```
021a21f0  mov r0, fp
021a21f4  mov r1, sb              ; sb = the species
021a21f8  bl  0x21a2738           ; FindLoadedModel(species) -> object or 0
021a21fc  ldrh r1, [r6]
021a2200  cmp sl, r1 ; bne  ->    skip
021a2208  cmp r0, #0 ; beq  ->    skip
021a2210  mov r1, r8 ; bl 0x2072aec   ; attaches the model to the actor
```

**If `FindLoadedModel` returns 0, the actor is created and no model is attached
to it.** The monster exists, it is not displayed. Exactly what the player
describes at 10 and 12 species.

`FindLoadedModel` (`0x021A2738`) scans slots 7 to 18 with `GetSlot(table, 7+i)`
and compares the species to `object+2` (`ldrsh`). It returns the **object**, not
the index. Objects are the **0xB0-byte** records allocated as one block by the
preloader (`0x021A28EC`, `count * 0xB0`), and the species is written there by
`0x021A2A60 strh fp, [r0, #2]`.

Four callers, all of the same shape: `bl`, `cmp r0,#0`, `beq`, otherwise attach.
The only one on the spawn path is `0x021A21F8`.

### Why `0x0203D038` does not fit

Its `type == 5` case allocates a 0xD8-byte actor record and stores it in
`[r7+0x18]`: it is an **actor** loader, not a "load species X's model into slot
i". Reusing it from the spawn would need rebuilding its context (`r0`, `r5`,
`r7`), which we do not know how to produce.

### The shape step 2 must take

The preloader `0x021A28A8` already holds the whole sequence: clear the slots,
allocate the record array, open the archive, loop over the list, close. Turning it
into a **loader of one species into one slot** needs seven graft points:

| # | Address | Change |
|---|---|---|
| 1 | three words in free space | `TABLEAU` (records), `TOUR` (rotation), `DEMANDE` (requested species) |
| 2 | `0x021A28CC` | do not clear slots if `DEMANDE` |
| 3 | `0x021A28E4`-`0x021A28F0` | reuse `TABLEAU` instead of allocating |
| 4 | `0x021A295C` | start from the rotation slot |
| 5 | `0x021A2974` | return `DEMANDE` instead of `GetSpecies(list, i)` |
| 6 | `0x021A2AC8` | exit after one iteration |
| 7 | `0x021A21F8` | if `FindLoadedModel` fails: set `DEMANDE`, call the preloader, retry |

Plus eviction: free the recycled slot's model with `HeapFree(map+0x113C, ptr)`,
which requires knowing the offset of the model pointer in the 0xB0-byte record —
**not identified yet**.

**Remaining unknowns**: that offset, and whether the spawn has the `r0` (`sl`)
the preloader expects. Without both, the assembly does not hold.

This is a multi-session job, and the test loop does not close locally: it needs
loading a map with encounters, which the harness cannot produce.

## 37. The real cost of each model, and the size filter

`scripts/tailles_modeles.py` measures, for each species, the size of its field
model once in RAM. The chain, checked:

`data/pack_lv5/enemy.gp2` -> member `<code>_f.mon`, **not compressed at the GPC2
level** -> Nitro **NARC** archive -> `.cchr` file, LZ77-compressed ->
decompressed size read from the header (`word >> 8`), without decompressing
anything.

**Corrections to `scripts/gp2.py`, all checked:**

- the index size field carries tree flags in its high byte: mask with
  `0xFFFFFF`. Without it the archive announces 419 MB members. After the fix,
  **600 consecutive pairs out of 600** satisfy
  `pos[i+1] - pos[i] == size[i] + 4`;
- the name table follows the order of entries **sorted by masked offset**, not
  the raw index order. Pairing without sorting gives no `_f.mon`;
- and there is **no** control u32 before a member: the NARC starts directly at
  `pos`. The 4-byte gap is trailing padding.

### Results over the 289 field models

| min | median | mean | max |
|---|---|---|---|
| 5,508 | **18,320** | 20,831 | **61,368** |

| threshold | models kept |
|---|---|
| <= 8 KiB | 6 |
| <= 16 KiB | **102** |
| <= 24 KiB | 230 |
| <= 32 KiB | 264 |

The largest are the `b`-prefixed monsters: `b100a` (Dragonlord) 61,368 bytes,
`b109a` (Zoma) 58,996. The smallest are the metal family: `z050a`/`b`/`c` at
5,508 bytes.

**A factor of 11 between the smallest and the largest.** Twelve median models
cost 220 KiB, twelve small ones 168: the filter is the cheapest lever to fit more
species per area. Hence `--taille-max N` in the randomizer.

## 38. A SAVESTATE IS TIED TO THE ROM'S FILE LAYOUT

v18 (`--especes 12 --taille-max 16384`) **boots and loads a game normally**,
program counter spread identical to the reference. But loading the transition
savestate taken on **v14** then crossing the boundary freezes the game on the
black screen.

The reason: `--especes 12` enlarges `encmons.bin` and `encfld.bin`, so **every
file offset in the ROM shifts**. The savestate restores the file system state as
it was on v14; the first cartridge read of the map load then lands in the wrong
place, and loading never finishes.

**Method consequence:** a savestate is only valid for ROMs with the **same data
layout**. Every **code** variant (grafts, bitmap) can be tested that way on v14's
layout, but no variant that changes a file size. For those, a savestate taken on
the ROM itself is needed.

## 39. The model budget, measured

Five size thresholds, six zone transitions each, on v18 (`--especes 12`). Model
slots actually filled out of the 12 requested:

| threshold | species in pool | models loaded |
|---|---|---|
| **16 KiB** | 102 | **12, 12, 12, 12, 12, 12** |
| 20 KiB | 186 | 11, 10, 11, 11, 12, 12 |
| 24 KiB | 224 | 10, 10, 11, 9, 11, 11 |
| 32 KiB | 256 | 10, 10, 9, 10, 10, 10 |
| none | 260 | 10, 10, 9, 10, 10, 10 |

With no filter, **2 to 3 models out of 12 never load**: that is the measure of the
invisible monsters reported on v15 and v16. At 16 KiB, all 12 load every time —
which the player confirmed in game on v18.

The model heap budget is therefore about **170 to 190 KiB**: twelve 14 KiB models
fit, twelve 18 KiB ones do not.

**Draw defect spotted along the way**: `180,114,3,3,83,245,28,83,83,76,15,11`.
Species 83 three times, 3 twice — graft A does not look at what is already in the
list. This area only shows 9 distinct monsters over 12 slots.

## 40. ANY FILE SIZE CHANGE INVALIDATES SAVESTATES

Already seen in §38 with `--especes 12`. Clearly confirmed: **v20**, i.e. v18 with
overlay 17 simply stored uncompressed and **no code change**, freezes exactly like
v19 after a transition.

The overlay goes from 200,184 to 314,688 bytes, every file offset in the ROM
shifts, and the file system state restored by the savestate points to the wrong
place. The map load never finishes.

**So it was not graft C.** It remains untested.

### The practical consequence, and the way out

The data layout must be **frozen once and for all** before asking for a
savestate. It is as soon as three things are settled:

| | |
|---|---|
| `encmons.bin` / `encfld.bin` | `--especes 12` |
| ARM9 | stored uncompressed, 1,000,984 bytes |
| overlay 17 | stored uncompressed, 314,688 bytes |

Once those three sizes are fixed, **any later code change keeps the same layout**
— grafts live in padding or replace existing code, without changing a single file
size. One savestate then covers the whole of step 2's development.

## 41. Graft C validated: 64 species accepted per area

Measured on v19 with the transition savestate taken on v19 (same file layout, so
valid), injecting bitmaps of increasing density:

| species in the bitmap | species accepted by the container |
|---|---|
| 24 | 24, 25, 24 |
| 48 | 48, 48, 48 |
| **64** | **64, 64, 64** |
| 80 | 80, **0**, 80 |
| 102 | 0, 0, 0 |

**Graft C works**: the container goes from 12 accepted species to 64, five times
more. First validation of step 1.

The cap is not in the container — it accepts 512 — but in the **`[map+0x10]`
heap**, from which `0x0206F240` allocates its 0x1C-byte records plus two
duplicated strings each. At 80 species it fails one time in three, at 102 always.
**64 is the safe value.**

Note: readings sometimes give 25 for 24 requested. Overlay 17 adds 1 to 4
hard-coded species after reading the file; one of them ends up in the container.

### What it changes for goal B

An area can now **accept** 64 species, while only 12 models fit in memory. Exactly
the configuration rotation needs: the container is wide, and only the 12 resident
models have to rotate within those 64.

## 42. A shorter path to rotation

Model heap setup, `ovl17 @0x021A30B0`:

```
021a30b8  bl 0x2032804   ; GetTotalFreeSize(map+0x1244)     -> r5
021a30cc  bl 0x2032554   ; HeapAlloc(map+0x1244, r5)         -> block
021a30e0  bl 0x2032500   ; CreateExpHeap(map+0x113C, block, r5)
021a30fc  bl 0x21a28a8   ; preload the 12 models
021a3108  bl 0x2032804   ; what is left of the model heap
021a312c  bl 0x2032500   ; CreateExpHeap(map+0x11C0, rest)
```

Rather than writing a per-model loader with its own eviction, we can **replay this
sequence** after handing both blocks back to the parent heap:
`HeapFree(map+0x1244, [map+0x113C])` and likewise for `map+0x11C0`. The preloader
then restarts on a fresh list, and the 12 models are replaced at once — reusing
the game's code instead of rewriting it.

About twenty glue instructions instead of several hundred.

**The risk, and it is real**: destroying the model heap while a visible symbol
uses it. Rotation must therefore trigger when no monster is displayed — the end
of a battle is the natural candidate, the game already resets field symbols
there.

No `DestroyExpHeap` function was found: `0x02032498`, the only candidate, is
actually a creation variant (`0x20AF714` then `0x20AFEA4`). So blocks are freed
directly, which assumes `[map+0x113C]` does hold the address of the block
returned by `CreateExpHeap` — **to check before touching it**.

## 43. The model record holds the pointer to free — eviction unblocked

Reading of the records returned by `GetSlot(table, 7..18)`, after a zone
transition:

```
2 records, gap between them: 176 = 0xB0        <- confirms the record size
record +0x08 = 0235E06C   <- pointer into the model heap
record +0x0C = 0235E118   <- pointer into the model heap
```

**That was the last unknown of eviction.** The block to return to the heap is read
at `record+0x08` (and a second at `+0x0C`). With `ClearSlot` (`0x0200FD58`),
texture freeing (`0x02057F10`, indices 120 to 139) and `HeapFree`
(`0x02032628`), the eviction sequence is complete.

## 44. Graft C starves the small heap — dead end, and what to do

Graft C does build the `+0x2F8` container (up to 64 species, §41), but **it breaks
model preloading**. Measured, after transition:

| bitmap | container `+0x2F8` | models loaded |
|---|---|---|
| 24 | 24 | **2** of 12 |
| 48 | 48 | **0** |
| 102 | 0 | 0 |

The cause: everything comes from the same small heap `[map+0x10]`. My 1,024-byte
reserve, plus the 0x1C records and their two duplicated strings, exhaust it — and
the **second** container, `map+0x304`, built by the neighbouring function
`0x021B5348` from `fld_mondata.bin`, has no room left.

Yet the preload loop requires the species in **both** containers:

```
021a2980  add r0, r6, #0x2f8 ; bl 0x206f500   -> [sp+0x18]
021a2994  add r0, r6, #0x304 ; bl 0x206ef28   -> r0
021a29a4  cmp r1, #0 ; cmpne r0, #0 ; beq     -> species skipped
```

An empty `+0x304` container therefore rejects every species, and no model loads.
That is also why v19 would show **no** monster in game.

### The conclusion, and it reverses the plan

**The large container is useless.** For rotation, the container only needs the
current generation's species — 12. If **the containers rotate together with the
models**, small heap usage stays exactly the original game's.

The right shape for step 2 is therefore: replay **the whole monster setup of a
map** (both containers plus preloading) with a fresh list of 12 species, at a
moment when no symbol is displayed. No large container, no per-model loader, no
fine eviction — a full regeneration, with the game's code.

Still to find: the `ctx` context the preloader needs (heaps live at
`ctx+0x113C`, **not** in the map structure — two distinct objects, which explains
why `[map+0x113C]` was not a pointer), and the battle exit point to graft the
regeneration onto.

## 45. Graft R alone is not enough: the containers are in charge

`0x021A2FA0(ctx)` is indeed the full setup, and `0x021A316C` is its **teardown**:
it tests each heap (`0x020328C4`), empties it (`0x02032740`) then destroys it
(`0x0203248C`), for `ctx+0x11C0` and `ctx+0x113C`. The function is therefore
reentrant and leak-free — the game calls it from seven places.

Graft R refreshes the preload list at the start of this function. It runs
correctly, measured: after a transition, the list does hold twelve new species.

**But zero models load.**

| | |
|---|---|
| species requested | 12 |
| models loaded | **0** |

Same reason as §44: the preload loop requires the species in both containers
`map+0x2F8` and `map+0x304`. Those containers are built by the asynchronous
handlers `0x021B5250` and `0x021B5348`, driven by a state machine **at map load
only** — not by `0x021A2FA0`. Changing the list after them only desynchronizes it.

Another measurement: 24 walking loops without crossing a boundary trigger **no**
call to `0x021A2FA0`. None of the seven callers runs during plain walking.

### The correct shape, at last

The containers are the gatekeeper. They must therefore be **wider than the list**,
and rotation happens inside:

| graft | when | role |
|---|---|---|
| C | map load | fill the container with **36 species** drawn at random |
| R | every setup | fill the list with **12** species **taken from the container** |

Graft R then reads species directly from the container's record block
(`[container+4]`, stride 0x1C, key at `+0x08`), which guarantees it never requests
a species the gatekeeper will refuse.

And graft C must **allocate nothing**: its 1,024-byte reserve on the small heap
`[map+0x10]` starved the second container (§44). A static 72-byte buffer in the
ARM9 padding `0x020F1E40` holds 36 identifiers, which sets the cap at 36 —
comfortably below the 64 measured in §41.

The space comes from removing graft A: if graft R fills the list at every setup,
drawing a species when parsing `encmons` is no longer useful.

## 46. The full chain, validated: grafts B, C and R

Three grafts, no more graft A. All measured on the transition savestate.

| graft | where | role |
|---|---|---|
| **C** | BOTH `bl CopyList` of the container constructors (`0x021B52C4` and `0x021B53C8`), plus the two following `add r1, sp, #off` | makes the containers hold 16 species instead of the list's 12, from a **static** buffer at `0x020F1E40` — it allocates nothing |
| **R** | `mov r7, r0` at the start of setup `0x021A2FA0` | fills the preload list with 12 **consecutive** species taken from the container, starting from a random index |
| **B** | body of `ChooseFieldMonsterId` (`0x02073FEC`) | the field drawer returns a species from the list, uniformly |

Graft A — drawing when parsing `encmons` — is **removed**: graft R fills the list
at every setup, making it useless.

### What the measurements imposed, step by step

| what was tried | result |
|---|---|
| graft C allocating 1 KiB on `[map+0x10]` | container 1 filled, **container 2 empty**, 0 models |
| graft C on container 1 only | 12 species requested, **0 models** |
| graft R drawing from the bitmap | 12 species, **0 models** (they are not in the containers) |
| graft R keeping the index in **r2** | near-identical lists: `AddSpecies` overwrites r2 (leaves `count * 2` there) |
| 12 independent draws | up to **three times** the same species, 10 models of 12 |
| container at 36 | container 2 empty |
| container at 24 | 10 to 12 models |
| container at 20 | 11 models most of the time |
| **container at 16, 12 consecutive** | **12 models at every transition** |

### Measured state of v27

```
container 16 | list 12 | models 12
transition 1 : 10,11,15,16,17,18,19,20,21,1,2,3
transition 2 : 11,15,16,17,18,19,20,21,1,2,3,4
transition 3 : 19,20,21,1,2,3,4,5,6,9,10,11
transition 4 : 2,3,4,5,6,9,10,11,15,16,17,18
```

Twelve **distinct** species, twelve models loaded, at every regeneration.

### The remaining limit, and it is structural

The container only holds **16** species: beyond that, it takes its share from the
same parent as the model heap and models stop loading. We take 12: two consecutive
windows therefore share at least 8 species. **Rotation can only move four species
at a time.**

Widening the rotation window would require reducing the visible count — for
example 8 species out of 16, which allows two disjoint windows. A trade-off to
make in game: twelve monsters with little rotation, or eight with real rotation.

And one unknown no lab measurement settles: **does setup `0x021A2FA0` run at the
end of a battle?** Twenty-four walking loops trigger no call to it. If yes,
rotation is visible at every battle; if not, it is only visible on zone loads, and
v18 (twelve species drawn from 102 at every load) remains preferable.
