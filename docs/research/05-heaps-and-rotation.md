# 5. Heaps, rotation grafts and the memory plan (§47–§57)

Part of the [research notes](README.md). Sections keep their original numbers.

## 47. MAJOR CORRECTIONS — the model heap is a FRAME HEAP

Established in `work/re/RAPPORT_SPAWN.md`, with measurements. Three earlier
sections are wrong.

### What is wrong

| section | what it says | what is measured |
|---|---|---|
| **43** | "the record holds the pointer to free, eviction unblocked" | `record+0x08` is a **0xAC**-byte render object (`0x020360E4`), `record+0x0C` a **0x2C**-byte object (`0x020368D0`). **Neither is the model.** The decompressed `.cchr` blob is referenced nowhere in the record |
| **32**, **42** | `0x02032500 = CreateExpHeap` | `0x02032500` writes the magic **`FRMH`** (literal `0x020AF88C`): it is **`CreateFrmHeap`**. `0x02032498` writes **`EXPH`** (`0x020AF338`): it is **`CreateExpHeap`** |
| **32** | "`0x02057F10` frees texture number i" | `0x02057F10(manager, tag)` scans **16 entries of stride 0xD4** and frees those carrying the tag. It is not a texture index |
| internal note | "at most 3 simultaneous actors" | **wrong, and it was my reading**: the 4-burst log gave 3, the 40-burst log gives **5, growing**. The coded cap is **12** (`0x021A21BC mov r2,#0xc`) |

### The fact that drives everything

`[ctx+0x113C]` is a heap with signature **`0x46524D48` = `FRMH`**, 187,440 bytes,
**0 free** after preloading. And `HeapFree` (`0x02032628`) dispatches on the
signature:

| signature | route | effect |
|---|---|---|
| `EXPH` | `0x020AF788(heap, ptr)` | frees **that block** |
| `FRMH` | `0x020AF9FC(heap, 3)` | **rewinds the whole heap**, `ptr` ignored |
| `UNTH` | nothing | no-op |

**So model-by-model eviction is structurally impossible as things stand**, and
there is nothing to take either: the rest of the heap is handed to `ctx+0x11C0` at
`0x021A3108`-`0x021A312C`.

187,440 / 18,345 = **10.2 models**. The memory cap and the 12-slot cap are in the
same place: **there is no hidden margin.**

## 48. Three new leads from these measurements

**(a) Convert the model heap to an `ExpHeap`.** Replace
`0x021A30E0 bl 0x02032500` with a call to `0x02032498`, which makes
`HeapFree(ptr)` actually work. It takes a 4th argument in `r3` (direction), but
`r3` holds `ctx+0x13C` there: a small stub is needed, not an in-place replacement.
Measured overhead: 0x4C header instead of 0x30 and 0x10 bytes per block, i.e.
**604 bytes out of 187,440**. Teardown (`0x021A316C`) and free-size computation
(`0x02032804`) already dispatch on all three magics, so they will follow.
**Unverified hypothesis**; the test is a single probe: put the stub in RAM, cross
a boundary, read the signature of `[ctx+0x113C]`.

**(b) `0x021A2B1C` reattaches models to actors already alive** — the preloader
calls it on exit (`0x021A2AF0`). A full regeneration **therefore does not need
every symbol to be off screen**, contrary to the fear in §42. It is enough that
the species of live actors are in the new list. A graft R building the list as
"live actors' species, then new species to fill" makes regeneration **safe at any
time**. And `ctx` is obtained through `0x0218B5B0 = GetFieldCtx()` =
`[[0x021D82E0]+4]`, measured at `0x022A6C28`.

**(c) The variety lever is not the number of models, it is their size.** 187,440
bytes hold 10 median models but **34** from the metal family (5,508 bytes). A
pool with a cumulative budget — rather than a fixed count of 12 — would fill the
heap as closely as possible on each map. Offline work in `randomizer.py`, **no
graft instruction and no risk**.

### A reusable control, to keep

Species **254** is in the transition state's preload list but not among loaded
models, and yet occupies two actor slots: a **reproducible invisible monster**,
useful for any future measurement.

And a method rule: **the bot's walk leaves the encounter map** after about twenty
30-frame bursts. Any duration measurement on the field must check that the model
set stays non-empty, otherwise it measures nothing.

## 49. Cumulative size budget: the whole bestiary, against three species per area

Lead (c) of §48, implemented and measured. Graft A2 replaces graft A: instead of a
one-bit-per-species bitmap, a **table of size classes, 2 bits per species** (128
bytes), and a **cumulative budget** reset to full at the first species of each
map.

| class | model size | cost charged |
|---|---|---|
| 0 | > 32 KiB, or no model | species excluded (only 4) |
| 1 | <= 12 KiB | 6 units of 2 KiB |
| 2 | <= 20 KiB | 10 |
| 3 | <= 32 KiB | 16 |

Budget: **90 units = 180 KiB**, out of the 183,452 bytes of measured footprint.
When the budget is not enough, the graft **adds nothing** — nine visible monsters
are better than twelve with three invisible.

### In-game measurement, four transitions

```
transition 1 : list 9 | models 9 | 180,149,114,96,163,3,236,3,148
transition 2 : list 8 | models 8 | 149,32,5,261,159,87,276,267
transition 3 : list 9 | models 9 | 28,84,42,99,242,26,191,109,116
transition 4 : list 8 | models 8 | 175,158,125,266,176,56,136,103
```

**Every model loads, every time.** And identifiers go up to 276: the draw does
cover the whole bestiary, not only small species.

### An ARM trap not to repeat

The first version kept the retry counter in **`ip`**. That is the call scratch
register: `rand_below` overwrites it, the counter becomes arbitrary and the loop
runs forever. Symptom: **black screen at the transition**, identical to an invalid
file layout — two very different causes for the same screen. The counter must
live in a register the call preserves.

### The real trade-off, in numbers

Three 2-bit classes each charge at their upper bound: mean overhead is **11.3
units charged against 8.9 real**, i.e. 25 %. Refining the bounds only gains half a
species (8.0 -> 8.5). Charging at the median would give 10 species but allow
overruns, hence invisible monsters.

**So the choice is plain:**

| | species per area | species reachable in the whole game |
|---|---|---|
| v18 (`--taille-max 16384`) | **12** | 102 |
| v29 (cumulative budget) | **9** | **256** |

Same memory budget seen two ways. Twelve monsters per area only exist if we give
up the 158 species whose model exceeds 16 KiB.

## 50. (b) Regeneration safe at any time: design, and the remaining wall

### Why it is the only way

On a frame heap, **full regeneration is the only possible release**: `HeapFree`
rewinds everything or does nothing. Not a style choice, it is the only operation
the allocator can do. `0x021A2FA0(ctx)` does exactly that — teardown
(`0x021A316C`) then rebuild.

### What makes it safe, measured

`0x021A2B1C`, called on preloader exit (`0x021A2AF0`), **reattaches models to
actors already alive**. A regeneration therefore does not require no monster on
screen: the species of live actors only need to be in the new list.

And we know how to enumerate them. Predicate **validated on a control**
(`sonde_acteurs.lua`: `[-1 x 12]` before the transition, `[254 96 57 -1 ...]`
after, the three species being in the preload list):

```
variant = [map+0x02] & 3                 (0x021A21AC)
base    = 0x70 + 12 * variant
for i in 0..11 : a = GetSlot(table, base+i)
                 if a != 0 and (short)[a+2] >= 0 -> species [a+2] ALIVE
```

It is the predicate the game itself uses to find a free slot (`0x021A20C0`).
Twelve reads. There is **no reference counter** (checked: `0x02072AEC` increments
nothing, `0x021A1364` decrements nothing): this scan is the only way.

### Graft R2

At the same hook point as graft R (`0x021A2FA4`):

1. clear the list;
2. put back **the species of live actors** — what makes the operation safe;
3. set the budget to `90 - 12 x (actors put back)`, since their models will also
   use heap;
4. fill by calling graft A2 twelve times, which draws within the remaining budget.
   `bl GRAFT_A2` works as "add a species": A2 ends with `b AddSpecies`, which
   returns with `bx lr` to A2's caller.

Then a **trigger**: setup runs neither while walking nor at the end of a battle
(measured in §46), so we must call it ourselves, with
`ctx = 0x0218B5B0()` = `[[0x021D82E0]+4]`, measured at `0x022A6C28`.

### The wall: space

R2 is about **30 instructions, 120 bytes**. Inventory of what remains:

| location | free |
|---|---|
| area `0x020E7268` | **8 bytes** (table 128 + graft A2 128 + costs + budget = 0x110 of 0x118) |
| tail of `ChooseFieldMonsterId` | **76 bytes** (graft B takes 56 of 132) |
| padding `0x020F1E40` | 72 bytes |
| padding `0x020F1D2C` | 54 bytes |

**210 bytes in total, in four non-contiguous pieces.** R2 fits, but must be split
into two halves linked by a branch — e.g. 19 instructions in the drawer's tail and
18 in the `0x020F1E40` padding.

The other, cleaner way is to free the ~600 bytes of the preloader `0x021A28A8`: it
becomes useless once R2 fills the list at every setup. But that requires storing
overlay 17 uncompressed, hence changing the file layout, hence asking the player
for a new savestate.

## 51. The trigger is in the ARM9, and it already holds `ctx`

A finding that changes the cost of (b): **everything can live in the ARM9**,
without touching overlay 17 — so without changing the file layout, so without
invalidating the player's savestates. Overlay functions are only called by address,
and it is resident during field play.

The spawn tick is `0x020733E8` (ARM9):

```
02073430  bl 0x200f398          ; slot table     -> [sp+0x24]
02073438  bl 0x218b5b0          ; GetFieldCtx()  -> [sp+0x20]   <<< ctx
0207344c  bl 0x2010220          ; cadence increment
02073450  ldr r1, [r7, #8] ; add r0, r1, r0 ; str r0, [r7, #8]
0207345c  cmp r0, #0x3e8        ; not yet -> exit
02073460  blt 0x2073d4c
02073464  ldrh r1, [r7, #2]     ; <<< HOOK POINT: about to spawn
02073478  bl 0x21a20c0          ; FindFreeActorSlot
```

Two lucky facts: hook point `0x02073464` is only reached when the game **is really
about to spawn a monster**, which gives a natural cadence; and `ctx` is already on
the caller's stack at `[sp+0x20]`, reachable without looking it up.

The trigger replaces `ldrh r1, [r7, #2]` with a call that counts spawns, and once
every K calls graft R2 then `0x021A2FA0([sp+0x20])`, before running the removed
instruction.

### Space inventory, all in the ARM9

| location | free | planned use |
|---|---|---|
| tail of `ChooseFieldMonsterId` `0x02074024` | 72 bytes | graft R2, first half |
| padding `0x020F1E40` | 72 bytes | graft R2, second half |
| padding `0x020F1D2C` | 54 bytes | trigger |
| area `0x020E7268` | 8 bytes | counter and seed |

**The actor scan is not optional.** Regenerating without putting back the species
of live actors leaves those actors pointing at rewound memory, which the 3D engine
reads every frame: corruption or data abort. It is the one part of R2 that cannot
be simplified for a first version.

## 52. (b) The rotation graft is written; the trigger is still missing

`scripts/patch_rotation2.py`. Three pieces in the ARM9, linked by branches, all
checked by disassembly:

| piece | address | size | role |
|---|---|---|---|
| C1 | `0x02074024` (drawer tail, dead code) | 72/72 bytes | counts, clears the list, gets the slot table |
| C2 | `0x020F1E40` | 72/72 bytes | puts back **the species of live actors** into the list |
| C3 | `0x020F1D2C` | 52/54 bytes | fills to budget through graft A2, then calls setup |

The actor scan (C2) is the safety condition: without it, symbols already on screen
point at rewound memory.

### Two hook points tried, neither fires

| hook | result |
|---|---|
| `0x02073464`, after the cadence threshold | **never reached**. An early exit (`0x0207342C bls`) short-circuits the tick as soon as the map holds its quota of symbols. Counter at zero after 50 s of walking, period forced to 1 |
| `0x020733F0` (`movs r7, r0`), function entry | **never reached either**. Checked with a minimal control — a graft that only increments a counter: it stays at zero |

So `0x020733E8` is not the per-frame tick I thought: it is called conditionally,
and in the transition state — three live symbols, quota full — it does not run at
all.

**The harness cannot settle what comes next**: it cannot fight, so the quota stays
full and the whole encounter subsystem stays idle. What is missing is no longer
disassembly, it is a game state where the system is working.

### What would be needed, by cost

1. **Try v32 in game.** If the hook never fires, the ROM behaves exactly like v30
   — no risk. If it fires, the set changes while walking. The cheapest test, and
   the only one that answers.
2. A savestate taken **right after a battle**, quota not full: the encounter
   subsystem would work, and the harness could measure.
3. Look for a field function called unconditionally every frame. `0x0200F398` is
   one, but it is called from everywhere: grafting a setup call there would be
   dangerous.

## 53. Why v32 only showed one monster, and the architecture that fixes it

In-game feedback on v32: regeneration does fire (~30 s, two periods), no crash,
but **a single monster species appears afterwards, everywhere, until the zone
changes**.

The cause: **setup called mid-game does not rebuild the containers.** They are
built by an asynchronous state machine, only at map load. The new list therefore
only passes the gatekeeper for species already in the old containers — i.e. those
of live actors, which the graft puts back for safety. The three actors were the
same species: hence a single monster. And a zone change rebuilds the containers,
hence the return to normal.

**The resulting rule: the list must always be drawn FROM the container.** The
container is the gatekeeper; nothing else gets through. That was already §45's
lesson, badly applied.

### The architecture of `scripts/patch_b.py`

| piece | where | role |
|---|---|---|
| 64-byte bitmap | area +0x00 | allowed species: roaming, no boss, model <= 20 KiB -> **186 species** |
| graft C, 96 bytes | area +0x40, on both constructors | fills the containers with **20 random species**, once per map |
| graft R, 212 bytes | area +0xD0, then `0x02074024`, then `0x020F1E40` | at every setup: clears the list, puts back the species of **live actors**, then **8 consecutive species** from the container starting at a random index |
| trigger, 52 bytes | `0x020F1D2C`, hook `0x020733EC` | calls setup every 1,024 frames |

Graft C's draw is **random**, fixing v27's defect of taking the 16 smallest
identifiers — the same for every area.

The hook moved to `sub sp, sp, #0x1c0`: unlike the following `movs r7, r0`, it
leaves no flags to reproduce.

### What the harness cannot exercise

`0x020733E8` **does not run** when the map holds its quota of symbols: checked
with a control that only increments a counter, on both hooks tried. The bot never
fights, so the quota stays full. In real play the function runs — the player saw
it on v32.

And from the v30 savestate, walking no longer crosses the zone boundary: neither
the trigger nor the transition can be exercised in the lab. **Only the player can
settle v33.**

### v33: crash at load, and a design flaw

**v33 does not start**: data abort at `0xFFFF0108` when the game loads. Caught by
the boot test, the ROM was not delivered.

Looking for the cause, a **second flaw** appears, independent of the crash: graft
C is called by **both** container constructors, and draws again each time. The two
containers therefore get **two different sets** of 20 species. But spawn requires
the species in both: the intersection is about 20 x 20 / 186 = **2 species**. Even
without the crash, v33 would have shown two monsters.

The fix needs the second call to **reuse** the first one's buffer, hence a second
distinct stub and a word to remember the count — some twenty bytes no longer
available in the area. The lead stays open but requires reworking the memory
plan, not tweaking a constant.

**Reference state: `work/dq9_v29.nds`** — 9 species per area drawn from 256,
renewed at every map load, no invisible monster, validated in game.

## 54. THE MODEL HEAP IS CONVERTED TO AN ExpHeap — verified to the byte

This is the door everything else was waiting for. On a frame heap, `HeapFree`
rewinds the whole heap and ignores the pointer: no eviction is possible. On an
`ExpHeap`, it **really frees the block**.

### The stub, two instructions

```
0x021A30E0   bl 0x02032500        ; CreateFrmHeap  -> becomes  bl STUB
STUB         mov r3, #4
             b  0x02032498        ; CreateExpHeap, tail call
```

`0x02032498` takes a **fourth argument** `0x02032500` does not: it ends up in
`0x020AFEA4`, the allocator initialization. The frame heap passes **4** there
(`0x02032530 mov r2, #4`). **With r3 = 0, no model loads anymore; with r3 = 4,
everything works.** That was the whole problem — and it also proves the stub
applies.

The two argument conventions are otherwise identical: `0x020AF984` and
`0x020AF714` both do `add r1, r1, r0`, so (start, **size**). Only the minimal
header, 0x30 against 0x4C, and the written signature differ.

### Verification

Walking back from a pointer inside the heap (`record+0x08` of a loaded model) to
the header:

| | header | signature | models loaded over 3 transitions |
|---|---|---|---|
| v29 as is | `0x0235AF2C` | **FRMH** | 9, 8, 9 |
| v29 + stub | `0x0235AF2C` | **EXPH** | 9, 8, 9 |

Same address, same behaviour, signature changed. The record shifts by 0x18, which
matches the larger header.

### What it unlocks

`HeapFree(heap, ptr)` = `0x02032628` now frees a specific block. Combined with:

- the scan of live actors, which tells which species are **still displayed** and
  therefore untouchable;
- `ClearSlot` (`0x0200FD58`) to empty the slot;
- the fact that **we will call the loader ourselves**, so we will know the pointer
  to return — which gets around obstacle B of §43, where the blob pointer could
  not be found in the record.

... model-by-model eviction becomes possible. We still need to preload **fewer**
models to make room: the player rarely sees more than five monsters on screen, so
six resident models are enough, freeing about 110 KiB of the 187.

**Status: the conversion is done and measured.** On-demand loading is still to
write.

## 55. Reduced preloading: 5 resident models, 112 KiB free

Graft A2's budget is a single immediate (`mov r0, #90`, 6th word). Measured over
three transitions, with the heap converted to ExpHeap:

| budget | species | models | occupied extent | estimated free |
|---|---|---|---|---|
| 90 | 9 | 9 | 161,452 bytes | ~26 KiB |
| **60** | **5** | **5** | **75,240 bytes** | **~112 KiB** |
| 45 | 4 | 4 | 53,096 bytes | ~139 KiB |

The extent is measured as the gap between the lowest and highest block pointer of
loaded records (`record+0x08`).

The player rarely sees more than five monsters on screen, so five residents are
enough — and the remaining 112 KiB hold six more models loaded on demand, in a
heap that can now return them one by one.

### What is left to write, and the cheapest way

On-demand loading reuses the preloader's sequence: `0x020D91EC` (archive open, 8
arguments, 4 on the stack), `0x020D9548` (member extraction), `0x0207551C`
(`.cchr`), `0x02075664` (decompression to the heap), `0x02036814`
(registration), `0x0200FD48` (`SetSlot`), `0x020D962C` (close). Written from
scratch, that is about fifty instructions, plus the member name `sprintf` — about
200 bytes, with 198 left in three pieces.

**The economical way is therefore to reuse the preloader itself**: patch it to
load ONE species, read from a global word, into a chosen slot, without clearing
slots or reallocating the record array. The graft then drops to about fifteen
instructions instead of fifty, since all the archive machinery is already there.
That requires patching overlay 17, hence keeping v30's layout.

Eviction, for its part, is now complete: scan of live actors to know which species
are untouchable, `ClearSlot` to empty the slot, `HeapFree` to return the blocks —
whose pointers we will know since our code will call `0x02075664`.

## 56. The community repositories, and the container cap falls

Two repositories provided by the player: `DQIX/dqix-functions` (function names in
resymgen format) and `DQIX/dqix-decomp` (decompilation configuration, JPN and USA
targets).

### What they validate

Crossing two entries carrying both addresses — `ChooseFieldMonsterId` (eur
`0x2073FEC`, usa `0x2073FDC`) and `GenerateCompanionByBT` (eur `0x209AFE4`, usa
`0x209AFD4`) — gives **EU = USA + 0x10** for the ARM9. Overlay 17 addresses are
**identical**.

Translated that way, `config/usa/arm9/symbols.txt` and its overlay 17 counterpart
give **7,402 functions with their sizes** (`work/communaute/symboles_eu.txt`). And
the ten addresses I had established by hand each fall **exactly on a function
boundary**.

The allocator is named:

| EU | real name | what I called it |
|---|---|---|
| `0x02032498` | `SafeAllocator::CreateTypeB(void*, u32, int)` | CreateExpHeap |
| `0x02032500` | `SafeAllocator::CreateTypeA(void*, u32)` | CreateFrmHeap |
| `0x02032554` | `SafeAllocator::Allocate(u32)` | HeapAlloc |
| `0x02032628` | `SafeAllocator::Free(void*)` | HeapFree |
| `0x02032698` | `SafeAllocator::Reset()` | — |
| `0x02032740` | `SafeAllocator::Destroy()` | "empty" |

### The heap size table, and why my first attempt failed

`func_ov017_021A02F0` sets up the field context heaps. Its loop reads a
`{identifier, size}` table with stride 8 at `0x021D6984` (terminated by `{0,0}` at
`0x021D6A2C`) and stores each handle at **`ctx + 0x38 + id * 0x14`**.

The container heap handle was measured at `ctx+0xD8`: `(0xD8-0x38)/0x14` =
**identifier 8**. The second one at `ctx+0x27C` = **identifier 29**, whose table
entry gives 1,024 — both agree.

**These sizes are read only once, when the field context is created.** Patching
them in RAM after loading a savestate always comes too late: they must be in the
ROM. That is what made my first attempt fail.

### The 16-species cap falls

v34 = v19 with identifiers 8-11 raised to 40,960 and 29-32 to 8,192. Measured on
the player's savestate, taken after a cold boot:

| | before | after |
|---|---|---|
| container 1 heap | 11,392 bytes | **40,912 bytes, 20,748 free** |
| species accepted by container 1 | 16 to 24 | **102** |

In game: 9 to 10 visible species, an occasional invisible one. The visible count
remains bounded by the **model heap**, not by the container — but the gatekeeper
no longer holds things back.

### And container 2 can be rebuilt, contrary to what I thought

`0x0206EE90` is not a constructor: it is a **parser driver**. It stores its
arguments in a global context (`count` as u16, heap, buffer, container) then runs
the tagged table parser (`0x02030744`) on the `fld_mondata.bin` blob, the
identifier list acting as a **filter**.

So rebuilding it mid-game only needs one thing: **still having the blob**. But it is
released right away (`0x021B540C bl 0x020301D8`), and likewise for `mon_data`
(`0x021B5314`).

| | size |
|---|---|
| `fld_mondata.bin` | 15,840 bytes |
| free in container 1's heap after enlargement | 20,748 bytes |

**The blob fits in the freed space.** Goal B's recipe becomes: keep a copy of both
blobs instead of releasing them, then rebuild both containers at will by calling
their drivers again with those copies.

*Unresolved: container 2 refuses 102 species — it allocates nothing, so it is not
memory. To settle before going further.*

## 57. The complete memory plan, and what today's measurements settled

### Available code space, exhausted

Scan of zero ranges in the decompressed ARM9 image: **529 bytes in total**, six
regions, including the 280-byte area already used. Overlay 17 offers none — its
two 48-byte "holes" at `0x021D622C` and `0x021D6298` are actually nearly empty
0x34 records in a table the game reads (non-zero words at `0x021D6228`,
`0x021D625C`, `0x021D628C`).

The three remaining candidates were validated with a canary — a pattern written in
RAM, read back intact after eight walks and two full map loads
(`scripts/lua/canari.lua`):

| region | bytes | final content |
|---|---|---|
| `0x02073FEC` | 68 | graft B |
| `0x02074030` | 64 | rotation, piece A (drawer's dead tail) |
| `0x020F1E40` | 72 | rotation, piece B |
| `0x020F1D2C` | 52 | rotation, piece C |
| `0x020F1CB8` | 40 | graft C, piece 1 |
| `0x020E7C78` | 40 | graft C, piece 2 |
| `0x020E8888` | 40 | graft C, piece 3 |
| area `+0x60` | 32 | graft C, piece 4 |

The class table went from 512 to **384 identifiers** (96 bytes instead of 128) to
free those 32 bytes: the largest field identifier is 334, and 384 is still an
encodable ARM immediate.

### The parent heap is full: no further enlargement possible

The field context heaps are carved from the ExpHeap **`0x022A3200`** (1,297,864
bytes, 25 children from `0x022A3278` to `0x02321BF8`). Its free block list
(`+0x24`, each block carrying its size at `+0x00`) holds a single block: **18,002
bytes**. v34's enlargement (+146,944 bytes) only just fit; there is no room for a
second one.

NNS header, **measured** offsets (the first reading, at `+0x14`/`+0x18` and
`+0x20`/`+0x24`, gave 36 MB extents):

| offset | field |
|---|---|
| `+0x00` | signature `FRMH` / `EXPH` |
| `+0x0C`, `+0x10` | children list |
| `+0x18`, `+0x1C` | start, end |
| `+0x24`, `+0x28` | head, tail (frame heap) or free list (exp heap) |

### The real cost of a species in the container

| | measured |
|---|---|
| container 1 heap (id 8) | 40,912 bytes, 17,884 free after 102 species |
| cost per species | **226 bytes** (0x1C record + three duplicated strings) |
| real capacity | **181 species** |
| container 2 heap (id 29) | 8,144 bytes, 5,300 free after 102 nodes -> **28 bytes per node**, 290 species |

Hence graft C's cap of **150** species: `0x0206F348` allocates the record block in
one go and gives up cleanly if it fails, but the rest duplicates three strings per
species (`0x020DA160`) and stores the result **without a null check**. Running out
at that point gives a null string pointer the preloader passes to its formatter.

### The window must be by rank, not by identifier

Picking 150 species out of 256 by taking an identifier range does not work: the
256 species span 0-334 with large holes, and a 160-identifier window holds **26 to
179** species depending on its start. Graft C therefore skips a number of species
(a rank), not an identifier interval.

The start comes from `[map+0x00] & 0x7F`: it must be **identical for both
constructors**, called one after the other (0x021B52C4 then 0x021B53C8). A random
draw would require remembering the rank between the two calls, seven instructions
there is no room for. Measured result: **c1 = 150, c2 = 150**, the same.

### The drawer now reads LOADED models

`FindLoadedModel` (`0x021A2738`) walks slots **7 to 18** of table `0x020F33D8` and
compares the species at `record+0x02` — confirmed by `strh fp, [r0, #2]` at
`0x021A2A60`, which writes it. Graft B therefore draws directly from those slots:
**a species that comes out necessarily has its model in memory**, and the
invisible monster disappears by construction.

### The preloader only handled six entries of twelve — and the budget is dead

Instrumentation of the preloader's six exits (`scripts/lua/pourquoi4.lua`,
`event.onmemoryexecute` without a fourth argument), control on v34:

```
loops=6 | container=6 name=5 narc=4 decompression=0 SetSlot=4 registration=0
```

And the order of events (`scripts/lua/ordre.lua`) is the expected one: twelve
`AddSpecies`, then the container constructor, then **a single** setup call, with
the list already complete at twelve.

So the preloader was not interrupted by memory nor by a loading failure: it only
ran **six loops of the twelve** announced by `0x0209C0FC` (= `[map+0x44+0x18]`,
the list count), spread over five frames. One species was refused by the
container, one when building the name, and the remaining four succeeded.

Practical conclusion: **graft A2's cumulative budget protected nothing** — neither
the heap nor the model count was saturated — and it only deprived the preloader of
candidates. It is now set to 200 units, out of reach. What really limits to four
models is still to establish, but two things are certain: graft B makes unloaded
species harmless, and the setup called by rotation gives the preloader a full new
chance.

### WHAT REMAINS OPEN

Control measurement on v34, the version the player validated:

```
list 12 (0 outside container) | models 4 | heap 187,392 bytes, 126,984 FREE
```

Only four models, with 124 KiB of heap still free: **the cap is not memory**, so
graft A2's cumulative budget is useless. The preloader can give up a species at
five points (container, file name, NARC member, decompression, model
registration); which one dominates is still to measure. The harness cannot settle
it alone: its symbol quota is full, so the spawn tick does not run and nothing new
is requested.

### v35: cold boot validated

`scripts/lua/demarrage.lua` on `work/dq9_v35.nds`, player SaveRAM, no savestate at
all — the only test that exercises the heap enlargement:

```
frame  3009  ctx=022A6C28  heap8 : extent 40912, free 21564 | c1=147 list=0
frame  4509  ctx=022A6C28  heap8 : extent 40912, free 21564 | c1=147 list=12
```

The field context is created, the enlarged heap is there, the container holds
**147 species** (the 150 window truncated by a high start rank) and the list its
twelve. The game loads and runs — final capture: the player in the Stornway church.
Exactly the test v33 had failed.

**Rotation, however, cannot be exercised in the lab**: the counter stays frozen (55
then nothing) because the spawn tick does not run when the map holds its quota of
symbols, and the bot never fights. The player had seen it fire on v32, after about
thirty seconds.
