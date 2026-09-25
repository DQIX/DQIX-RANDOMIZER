# 7. The universal gatekeeper and the on-demand loader (§65–§71)

Part of the [research notes](README.md). Sections keep their original numbers.

## 65. P3 delivered and validated in game: the universal gatekeeper

September 8. Goal reached for the targeted half: **any species of the bestiary
appears at every spawn**, the battle is right, only the symbol's look on the map is
borrowed. Player feedback: "it works as expected, on the map I mostly see the same
5-6 models but as soon as I enter a battle I get a random mob every time".

Build: `python randomizer.py "<rom>" --seed 35 --especes 12
--sans-rotation --portier -o work/dq9_p3.nds`. Source: `scripts/patch_portier.py`.

### The four pieces

| piece | where | size | role |
|---|---|---|---|
| drawer | `0x02073FEC` | **8 bytes** | `mov r1,#0x8000 ; b A2` — reuses graft A2's "return" mode, which already draws from the 256-species bitmap |
| gatekeeper 1 | area `+0xC0` | 80 bytes | original lookup, then SYNTHESIZES the missing record |
| gatekeeper 2 | `0x020F1E40` | 64 bytes | same for container 2's linked list node |
| borrow | `0x02073FF4` | 72 bytes | `FindLoadedModel`, then on failure a random loaded model |

Data: synthetic record at `0x020F1CB8` (0x1C bytes), node at `0x020E7C78` (0x1C
bytes).

Four `bl` redirected in overlay 17: `0x021A2164` (spawn gatekeeper 1),
`0x021A2178` and `0x021A22F0` (gatekeeper 2 and its reread), `0x021A21F8`
(`FindLoadedModel`).

### Three decisions, and why

**Patch the CALL SITES, not the functions.** `0x0206F500` has **twenty** callers in
the whole game (battle, overlays 21E/21F): replacing it would return a synthetic
record where the caller expects a zero. Exhaustive count of `bl` in the ARM9 and the
35 overlays: `chercher1` 20 callers, `chercher2` 4, `FindLoadedModel` 4.

**Not the preloader's sites** (`0x021A2988`, `0x021A299C`). If the gatekeeper always
said yes to it, it would load the template's model twelve times. It keeps its
behaviour — five to nine real models — and spawns borrow from those.

**A single shared static record, not a pool.** Four fields are really consumed, all
checked by disassembly:

| field | reader | destination |
|---|---|---|
| `+0x04` model code | graft A2 (`ldrb [r0,#5]`) | code validation |
| `+0x0C` short | `0x021A22C8` -> `0x020377D4` | actor`+0x64` |
| `+0x0E` short | `0x021A22D8` -> `0x020377C4` | actor`+0x68` |
| `+0x12` short | `0x021A1FEC` `ldrshne sl,[r0,#0x12]` | **scale**, 0x1000 by default |

The gatekeeper copies the `0x1C` bytes of **the area container's first record** —
real values, from a monster of that area — and only overwrites the species at
`+0x08`. The content is therefore identical for every substituted species, and two
live actors can point to it without trouble. A pool per actor slot would have cost
336 bytes, which we do not have.

The record IS read again after spawn (`0x021A1FE0 ldr r0,[sb,#0x180]`), so a stack
record or one recycled at each call was not enough.

### What the player sees, and it is as designed

- The same 5 to 6 models on the map: the preloader is untouched.
- A different monster at every battle: that is the goal.
- **The hitbox follows the real species, not the borrowed model.** A large symbol
  whose species is small is touched like a small one. Collision does not come from
  the model — P4 removes the gap by construction.

### Cold boot: validated

`scripts/lua/demarrage.lua` on `work/dq9_p3.nds`, player SaveRAM, no savestate:
game loaded, `ctx=022A6C28`, heap 8 at 11,344 bytes (vanilla size, so no trace of
graft C), 9,000 stable frames. The test `v33` had failed.

## 66. The session's measurements, and two corrections

### Leftover confiscation — instrumented at setup

`scripts/lua/montage.lua`, probes on the four points of `0x021A2FA0`:

```
[1] town  : model heap = 62,280   free after preload = 62,228  CONFISCATED 62,228
[2] field : model heap = 188,384  free = 93,892  models 5 : 123,84,174,147,129  CONFISCATED 93,892
[4] field : model heap = 188,384  free = 99,308  models 5                        CONFISCATED 99,308
[6] field : model heap = 188,384  free = 36,532  models 9                        CONFISCATED 36,532
```

Sequence `0x021A30B8`-`0x021A312C` creates the model heap with **all** the free
space of `ctx+0x1244`, runs the preloader, then **takes back the whole leftover** to
make heap `ctx+0x11C0`. Systematic, at every setup, and it is **36 to 99 KB** on the
field — two to five models thrown away.

The model heap therefore has **0 free bytes by construction**, which ruled out any
on-demand loading. P4's fix: bound `r5` at `0x021A310C`.

### `ctx+0x11C0` is never used in game

`scripts/lua/tas_confiscation.lua`, frame-by-frame sampling: usage **0 bytes** over
16 walking zigzags, on the field as in town. The heap is created then stays empty.

But it is not useless: `0x021C20B4` passes it in `r2` to `0x0202FD0C`, the
enqueueing of an **asynchronous** file request. It is the field's asynchronous
request heap. Our loader will therefore allocate its compressed member there, as the
game does.

Measurement trap paid along the way: reading these headers **during** a transition
gives inconsistent values (`0x11C0` missing, a "usage" of 160,080 bytes that was
actually the free space of `0x113C`). Instrument setup, do not sample blindly.

### Texture VRAM: individual eviction IMPOSSIBLE

The game installs the **watermark** manager (`Frm`):

```
0218ba54  mov r0,#4 ; mov r1,#1 ; bl 0x20bb49c   ; InitFrmTexVramManager(4 slots)
0218ba60  mov r0,#0x4000 ; mov r1,#1 ; bl 0x20bb790 ; InitFrmPlttVramManager(16 KB)
```

- `NNS_GfdDefaultFuncFreeTexVram` (`0x020F1EEC`) points to `0x020BB708` =
  `mov r0,#0 ; bx lr`. **An empty stub.** Same for palettes (`0x020BB918`).
- The installed allocator (`0x020BB598`) is two cursors per region, with no block
  tracking structure: nothing to update even when writing a `free`.
- Neither `BitArray` nor `Lnk` is linked in the binary.
- Table of 5 descriptors of 0x18 bytes at `0x020F1F14`, total `0x80000` = 512 KB,
  exactly the DS texture image VRAM, with the rule for 4x4 compressed textures
  (`kind 0 -> R1`, `kind 3 -> R2`, half the size).
- Substituting a manager is a big job: the 10 hot sites call `0x020BB598` through a
  **direct** `BL`, and ~15 sites do checkpoint/rollback (`0x0207DFBC` marks,
  `0x0207DFA0` restores), an idiom incompatible with a free-block allocator.

The game's only "free" is the watermark rollback, and **the preloader starts with
it** (`0x021A2900 bl 0x207dfa0`): the 12 monster textures live in a single region
freed all or nothing. Same discipline as `FRMH` on the RAM side.

Hence the piece to add to P4: **monotonic allocation + bulk refresh**. Load by
advancing the cursor; when full, roll back then relink the textures of the N
residents from the blobs kept in RAM. With 256 KB reserved for the field and
textures of 8 to 30 KB, that is a stutter **every 10 to 20 spawns**, not one per
pop.

### Loading one species exists in the resident ARM9

Case `type == 5` of `0x0203D038`, always in RAM:

```
0203d47c  cmp r0, #5
0203d4c0  bl 0x2003ce8    ; sprintf(name, fmt, r5+4)   <- r5+4 = model code
0203d4f0  bl 0x20d91ec    ; opens enemy.gp2, buffer 0x30000
0203d53c  bl 0x20d9548    ; extracts the member (SYNCHRONOUS)
0203d584  bl 0x207551c    ; .cchr sub-chunk
0203d5b8  bl 0x2075664    ; LZ77 -> heap
0203d5f0  bl 0x2036814    ; registers the model
```

`0x02075664` is indeed the decompressor, contrary to what a report had concluded:
`ldr r1,[r5] ; lsr r1,#8 ; str r1,[r2]` (size), `bl 0x2032554` (allocation),
`blx 0x20006cc` (BIOS LZ77 thunk), and **it returns the blob pointer** — so our
eviction table fills itself for free.

`0x020D9548` is **synchronous**, not asynchronous. The real asynchronous path is
`0x0202FD3C` / `0x0202FDE0` / `0x0202FED8`, and any synchronous archive open
**purges the queue** (`0x021A2908`, `0x0203D4A0`).

### Spawn retries forever, so asynchronous is free

```
02073d3c  bl 0x21a2128     ; the spawn
02073d40  cmp r0, #0
02073d44  movne r0, #0
02073d48  strne r0, [r7,#8] ; the accumulator is only reset IF it worked
```

A failure keeps the accumulator and **retries on the next frame**. An asynchronous
loader therefore only needs one word to lock the pending species: zero frames
blocked, against one or two when synchronous.

### `0x0206F500` is a trampoline

```
0206f500  ldr ip, [pc, #4]   ; -> 0x0206F480  generic binary search
0206f504  ldr r2, [pc, #4]   ; -> 0x0206EF50  key extractor: ldrsh r0,[r0,#8]
0206f508  bx  ip
```

Gatekeeper 1 is therefore a binary search over the record array, key = the species
at `record+0x08`.

### CORRECTION: `EU = USA + 0x10` is wrong at the bottom of the ARM9

Checked over 22,246 `bl` sites: offset **0x00** from `0x02000814` to `0x0200F3B4`
(808 sites), **+0x10** from `0x0200FD24` to `0x020E6918` (21,427 sites). The EU's
extra 0x10 bytes are inserted **inside** the EU version of `func_0200F3A4`. The
first ~200 entries of `work/communaute/symboles_eu.txt` are therefore off by 0x10
(BIOS thunks, libc). Overlay 17 is indeed identical.

### CORRECTION: §43 is wrong, and the "textures 120-139" do not exist

- `record+0x08` is a 0xAC-byte render object, `record+0x0C` a 0x2C config object:
  freeing them returns 216 bytes out of 18,500. **The blob pointer is nowhere in the
  record** — our loader must remember it, since it is the one calling `0x02075664`.
- `0x02057F10` is not a texture manager: it scans 16 entries of stride 0xD4,
  compares `[entry+0xD0]` to a tag and does `ClearSlot(0xD0 + i)`. Those are **16
  3D object instances** (effects), in slots 208-223 of the global table. Allocator
  `0x02057FE8`, free by index `0x02057DC8`, access by index `0x02058668`. Nothing to
  do with monster models.

### The `dq9_banc.nds` bench is dead for monsters — do not trust it

`scripts/lua/diag.lua` on `rand.State`: the tick runs (`tic=1200`), the drawer is
called 877 times in 40 blocks, but **spawn `0x021A2128` is never reached**, zero
models loaded, twelve actor slots at -1. And `c1=150`: an old build **with graft
C**, the one that corrupts records. Any zero measured on this bench is an artefact.
Valid bench: `work/dq9_p3.nds` + `banc/states/terrain_p3.State`.

Method lesson: put a probe on a function **known to be called** before believing a
zero. Here `getCurrentFieldStructure` (`0x02027CC0`) also stayed at zero — it is
simply not called on that path — while the tick and the drawer counted normally.

## 67. P4 step 1: the space finally exists, and the §57 riddle falls

September 9. `scripts/patch_place.py`, option `--place`. Three stubs of four to
eight bytes, all in the old rotation's piece C (`0x020F1D2C`, 52 bytes validated by
canary). Everything measured with the setup probe (`scripts/lua/montage.lua`, six
setups per run).

| stub | where | what |
|---|---|---|
| ExpHeap | `0x021A30E0` -> `mov r3,#4 ; b 0x02032498` | the model heap becomes an ExpHeap |
| bound | `0x021A310C` -> `min(r0, 0x4000)` | confiscation only takes 16 KB |
| cap | `0x021A2ACC` -> `min([list+0x18], N)` | the preloader only does N loops |

### The ExpHeap does not only allow eviction: it UNBLOCKS the preloader

Comparative measurement, same bench, same savestate, three town exits:

| | models loaded | free after preload |
|---|---|---|
| frame heap (vanilla) | **5, 5, 9** | 93,892 / 99,308 / 36,532 |
| ExpHeap, no cap | **11, 10, 8** | 7,608 / 2,072 / 8 |

The bound acts AFTER preloading: it cannot be the cause. So it is the ExpHeap
conversion that doubles the number of loaded models — on the frame heap, preloader
allocations failed and it gave up species.

**That is the §57 riddle falling**: "only four models, with 124 KiB of heap still
free — the cap is not memory". Indeed it was not memory: it was the allocator type.

Immediate practical consequence: `--place` without a cap already improves P3, twice
as many models on the map, so much more varied borrowed looks. That is
`work/dq9_p3b.nds`.

### But with no cap nothing is left: the space comes from the cap

The preloader then fills the heap to within eight bytes, and the confiscation bound
becomes useless — it only REDUCES, it guarantees no floor. Hence the third stub. With
`--plafond 5`:

```
[2] field : models 5 : 120,237,142,17,107   free 104,284  CONFISCATION 16,384
[4] field : models 5 : 16,27,115,149,2      free 108,416  CONFISCATION 16,384
[6] field : models 5 : 328,140,247,214,265  free  66,124  CONFISCATION 16,384
```

and the model heap kept, free block list walked:

```
field : free 87,884 / 92,016 / 49,724   in 1 SINGLE block, largest = all
town  : free 45,788                     in 1 single block
```

104,284 - 16,384 = 87,900, within a 16-byte block header. **Three to five streaming
models on top of the five residents, in one piece.** No fragmentation at start, and
the largest model of the bestiary (61,368 bytes) fits in two cases out of three.

### The cap is NOT the §60 freeze

The §60 freeze came from CHANGING the list count in memory while the preloader
iterated, although it had sized its record array once and for all on entry
(`count * 0xB0` at `0x021A28EC`). Here the list is untouched: we only bound the
value returned to the loop test `0x021A2AD0 cmp sb, r0`. The array stays sized to
the real count, we use less of it. Six setups, no freeze, clean cold boot.

### Reading a heap's free space: the formula depends on the type

Trap paid here. On a frame heap free space is `[h+0x28] - [h+0x24]` (tail minus
head). On an ExpHeap, `+0x24` is the **head of a free block list**, and the same
formula gives a misleading zero. NNS ExpHeap block header: size at `+0x04`, next at
`+0x0C`. `scripts/lua/montage.lua` now walks the list and returns the total, the
block count and the largest — i.e. the fragmentation measurement, for free.

### What is left for P4

1. **The loader**, transcribed from case `type == 5` of `0x0203D038`, hooked at
   `0x021A2154` (return 0 before actor creation) rather than `0x021A21F8`, so the
   retry loop at `0x02073D40` goes around cleanly. Asynchronous: `0x0202FD3C`
   enqueues, `0x0202FDE0` polls, `0x0202FED8` fetches. One word to lock the pending
   species.
2. **Eviction**: 12-word table of blob pointers (returned by `0x02075664`),
   live-actor predicate from §50, `HeapFree` on the three blocks. Allocate from the
   tail (`SafeAllocator::AllocateReversed`, `0x02032594`) to isolate the churn from
   the residents.
3. **The species -> model code table**, injected: the `mon_data` context was not
   found (`0x02108D18` is always empty, it is not it), and we have the mapping
   offline in `work/tailles_modeles.txt`.
4. **Bulk VRAM refresh**: texture VRAM is a watermark whose `free` is an empty stub
   (§66). Allocate by advancing the cursor, then when full `0x0207DFA0` (rollback)
   followed by relinking the residents' textures from the kept blobs. A stutter every
   10 to 20 spawns.

### The reference savestate, and its limit

`banc/states/terrain_p3.State` (paired with `work/dq9_p3.nds`) is **in the middle
of zone 20002**: no zone boundary reachable in 15 s of walking in the four
directions (`scripts/lua/reperage.lua`). It is for observing spawns, not setups. For
setups, only `rand.State` + `dq9_banc.nds` crosses — and that is legitimate, setup
does not depend on the monster subsystem, dead on that bench.

## 68. THE SOURCE TABLE: the game can build it, on the heap we choose

This is the piece that tips P4, and it was in the game from the start.

### The problem it solves

The preloader takes the model code from container 1's record:

```
021a29b4  ldr r2, [r0, #4]     ; r0 = the record, +0x04 = the code (string)
021a29c0  bl  0x2003ce8        ; sprintf("%s_f.mon", that code)
```

So to load an arbitrary species' model, the record just needs to hold the RIGHT
code. The previous gatekeeper copied the area's first record and only overwrote the
species: wrong code, wrong scale. Hence the hitbox not matching the symbol — a
defect the player reported on `dq9_p3.nds`.

We therefore needed the species -> code mapping for the 438 monsters. Three leads
were tried before the right one:

- **`0x02108D18`** (returned by getter `0x0206F514`): always empty, it is not the
  `mon_data` context. Measured.
- **Keeping the blob** by neutralizing both releases (`0x021B5314`, `0x021B540C` ->
  `mov r0, r0`): breaks nothing, checked in game — but we still did not know where
  the table lived.
- **The 0x30000 buffer** (`0x0211E33C`): capturing the arguments of constructor
  `0x0206F240` showed `{count = 438, block}` right after setup... then garbage. It
  is the archive's SHARED SCRATCH, overwritten at the next read. Not a persistent
  table.

### The function, and its signature

```
0206efe8  push {r3, r4, r5, lr}
0206efec  mov r5, r0            ; the context to fill
0206eff0  mov r4, r1            ; THE HEAP
0206eff4  bl 0x202f7d8          ; suspends async
0206eff8  ldr r0, [pc, #0x24]   ; "data/prm/mon_data.gp2"
0206effc  ldr r1, [pc, #0x24]   ; the member
0206f000  add r2, sp, #0
0206f004  bl 0x207569c          ; reads the file -> blob, size in [sp]
0206f008  mov r2, r0
0206f00c  ldr r3, [sp]
0206f018  bl 0x206f02c          ; builds {count, block} ON HEAP r4
0206f01c  bl 0x202f7f8          ; resumes async
```

**`0x0206EFE8(context, heap)`** — two arguments, and the produced context is in the
format the game's generic search already understands. `0x0206F108` confirms it:

```
0206f108  ldr r1, [r0]
0206f10c  mov r0, #0x1c
0206f110  lsl r1, r1, #0x14
0206f114  lsr r1, r1, #0x14     ; the count fits in TWELVE bits
0206f118  mul r0, r1, r0        ; size = 0x1C * count
```

So: **stride 0x1C, count on 12 bits of word 0, block at +0x04** — exactly the map's
container. `0x0206F480(ctx, species, 0x0206EF50)` works on it as is.

Reading trap paid here: `lsl #20 ; lsr #20` keeps the twelve LOW bits, not twenty.
With a 20-bit mask you read 328,118 instead of 438.

### In-game measurement

`scripts/lua/p4.lua`, two town / field round trips, patch injected in RAM:

```
before any setup  SRC=[00000000 00000000] count=0
field 1           SRC=[822501B6 0237E9C4] count=438
      [  0] species=1    code=z000a  scale=4096
      [  1] species=2    code=z000b  scale=4096
      [ 50] species=51   code=z058a  scale=5406
      [200] species=217  code=z034a  scale=13926
      [437] species=900  code=z060c  scale=4915
      models loaded=5 : 120,237,142,17,107
```

Increasing species, real codes, real scales — 4096 = 0x1000 = 1.0, and 13926 = 3.4x
for species 217, the giant, whose code `z034a` is indeed in §37's list of heavy
models. The table is rebuilt at every setup (different address in town and on the
field), the game runs, and all five models load despite the ~12 KB it costs
(438 x 0x1C).

### The stub

`talon_source`, 44 bytes, replaces `0x021A30FC bl 0x021A28A8` in setup:

```
push {r0, lr}
ldr r0, [pc, #L0]      ; SRC
mov r2, #0
str r2, [r0]           ; invalidate: the heap was just recreated
ldr r1, [sp]           ; the field context
add r1, r1, #0x1100
add r1, r1, #0x3c      ; r1 = ctx + 0x113C  (0x113C is not encodable)
bl 0x0206efe8
pop {r0, lr}
b  0x021a28a8          ; then the preloader, as planned
```

It is the only point of the life cycle where we hold both a fresh heap and the
context. And since the heap is recreated at every setup, the table must be too.

### What the gatekeeper becomes

It SHRINKS: 52 bytes instead of 80, and it tells the truth instead of approximating.

```
push {r4, lr}
mov r4, r1
ldr r2, [pc, #L0]      ; the key extractor
bl 0x0206f480          ; the map's container
cmp r0, #0
popne {r4, pc}
ldr r0, [pc, #L1]      ; SRC
mov r1, r4
ldr r2, [pc, #L0]
bl 0x0206f480          ; the source table of 438
pop {r4, pc}
```

No more synthesis, no shared static record, no pool. If the table could not be
built, `SRC` is {0, 0} and the search returns 0 without overflowing
(`ldr r5,[r0,#4]` then `cmp r5,#0`).

### What is left, and it is little

The preloader now has everything: ask it for a species, it finds its record through
the gatekeeper, reads the real code, builds `<code>_f.mon` and loads. Only the "one
species into one slot" mode is missing — §36's seven graft points, two of which
must be revisited in light of §66: do not clear slots, and above all DO NOT roll back
the VRAM watermark (`0x021A2900 bl 0x207dfa0`), which would throw away the other
models' textures.

## 69. CODE SPACE: inventory, and the reserve for later

Read before any new work that needs code in the ARM9. This topic cost more time than
any other constraint of the project.

### The rule that avoids the problem: data or code?

| what we want | where it is done | code space |
|---|---|---|
| which species in which area | files `encfld`/`encmons`/`encbtl` | **zero** |
| monster stats | `mon_btldata.nat` | **zero** |
| items, equipment, spells, skills | `itemdt.gp2`, `spelltable.bin`, `skilltable.bin` | **zero** |
| scripted battles | `eventbattle.bin` | **zero** |
| **a different species at EVERY spawn** | code | ~600 bytes |
| **different loot at every kill** | code | same |
| **a shop that restocks randomly** | code | same |

In other words: anything decided **once, when the ROM is generated** is data work and
costs nothing. Anything that must be decided **in game, every time** needs a graft. A
classic item randomizer is therefore entirely on the data side; only PER-EVENT
randomness hits the space wall.

### Measured inventory, as of September 9

Scan of zero ranges in the decompressed ARM9 (1,000,984 bytes): **1,119 bytes in 27
regions**, including the 280-byte area. Overlay 17 offers **none** — its two 48-byte
"holes" at `0x021D622C` and `0x021D6298` are nearly empty 0x34 records in a table the
game reads.

Usage as of September 9 (P3 + P4 step 1):

| region | size | content |
|---|---|---|
| `0x020E7268` area, `+0x00` | 48 | bitmap of allowed species |
| area `+0x30` | 140 | graft A2 (draw from the bitmap) |
| area `+0xC0` | 52 / 88 | gatekeeper 1 — **36 free** |
| `0x02073FEC` | 8 / 132 | drawer (2 instructions) |
| `0x02073FF4` | 72 | model borrow |
| `0x0207403C` | 44 / 52 | source table stub — **8 free** |
| `0x020F1E40` | 64 / 72 | gatekeeper 2 — **8 free** |
| `0x020F1D2C` | 48 / 52 | ExpHeap, bound, cap stubs — **4 free** |
| `0x020F1CB8` | 8 / 40 | `SRC` (source table context) — **32 free** |
| `0x020E7C78` | 28 / 40 | container 2 synthetic node — **12 free** |
| `0x020E8888` | 0 / 40 | **free** |

Left, all fragments together: about **600 bytes in some twenty pieces of 24 to 40
bytes**. Other ranges, not used yet and **not validated by canary**: `0x020E70FE`
(34), `0x020E7129` (27), `0x020E7182` (30),
`0x020E71A8`/`C7`/`E8`/`0x020E7208`/`28`/`48` (24-25 each), `0x020E7C0A` (26),
`0x020E7C2E` (34), `0x020E7DA4` (25), `0x020E9449` (26), `0x020F0320` (32),
`0x020F03A1`/`C1`/`E1` (31 each), `0x020F0405` (29), `0x020F1DA6` (26),
`0x020F1DEE` (26), `0x020F2E3C` (37).

**Any region not listed in §57 must be validated by canary before putting code
there** (`scripts/lua/canari.lua`: pattern written in RAM, read back after playing and
crossing two zones).

### Practical consequence: splitting

`assembler()` produces a contiguous block. A function over 40 bytes must therefore be
split into pieces linked by branches, as the old rotation did (pieces A, B, C).
Doable, and the label mechanism supports it, but **each split is a chance to be off
by one instruction** — the two most expensive failures of the project came from that
(§58, §61). Rule: never a hand-written branch address, always `{@label}`.

### THE RESERVE: the BSS bootstrap, never done

`static_bss_start = 0x020F2E60`, `static_bss_end = 0x021536E0` — **395 KiB**. Read in
ModuleParams (`0x02000BA0`), checked:

```
autoload_list_start   +0x00 = 020F4600
autoload_list_end     +0x04 = 020F4618
autoload_start        +0x08 = 020F2E60
static_bss_start      +0x0C = 020F2E60
static_bss_end        +0x10 = 021536E0
compressed_static_end +0x14 = 0209BD08
```

Autoload list, two entries: `{dest=0x01FF8000, size=5952, bss=23360}` (ITCM) and
`{dest=0x027E0000, size=96, bss=32}` (DTCM). The ARM9 image spans `0x02000000` to
`0x020F4618`; its tail, from `0x020F2E60` to `0x020F4618`, holds the autoload data
then the list. crt0 copies those blocks to ITCM/DTCM, **then zeroes
`0x020F2E60`-`0x021536E0`**.

So three closed paths, one open:

- **Enlarge the image and put code in it**: added bytes fall in the zeroed range.
  Closed.
- **Move `static_bss_start`** to protect our code: the game's BSS variables placed
  there by the linker would no longer be initialized. Closed.
- **Enlarge an autoload block** (ITCM): moves the start of its BSS, so our data
  overlaps the game's ITCM variables, addressed absolutely. Closed.
- **COPY AT RUN TIME.** Zeroing only happens **once, at boot**. A blob stored in a
  NitroFS file, read at map load into a heap allocation, then executed, survives
  without trouble. Open.

Bootstrap recipe, for the day more than 600 bytes are needed:

1. Add a file to the ROM with `ndspy` (the code blob, assembled
   position-independent: relative branches, data through a base register).
2. Read it with **`0x0207569C(path, member, &size)`** — already used by the game, see
   §68 — or with the generic NitroFS loader whose EU address lies in
   `]0x020750A0 ; 0x02075258[` (`candidate_loadNitroFsFileToBuffer` in
   dqix-functions).
3. Allocate it on a heap that lives long enough. The model heap (`ctx+0x113C`) is
   recreated at every setup: it would suit code used only on the field, and it has 50
   to 92 KB free since patch_place.
4. **Invalidate the instruction cache** before branching into it: the ARM9 has
   separate caches. `ClearDataCacheByAddr` and `ClearInstructionCacheByAddr` are in
   block `0x020C82B8`+ (names from dqix-functions, EU addresses derived by alignment —
   **to check before use**).
5. Keep the blob pointer in a static word, and branch to it from a three-instruction
   stub placed in existing padding.

Estimated cost: one to two sessions, mostly verification. Gain: code space stops being
a constraint for the rest of the project.

**When to do it**: if a task needs PER-EVENT randomness (different loot at every kill,
restocking shop, look drawn at every encounter). Not for a classic item, equipment or
spell randomizer — that one is entirely on the data side. *(Superseded by §72: the
code blob ended up in a file loaded by the game.)*

### Dead code, and why it remains a bad lead

§32 found 13.5 KB of functions "never called nor referenced". §33 showed the criterion
does not hold: it covers neither references built by `add rX, pc, #imm` nor tables
built at run time. Use only after validation by watched execution
(`event.onmemoryexecute` on the candidate function during a long session), not by a
mere canary — a canary proves the region is not WRITTEN, not that it is not EXECUTED.

## 70. P4 step 2: on-demand loading, through the preloader itself

`scripts/patch_chargeur.py`, option `--chargeur` (implies `--portier --place`). 204
bytes in eight pieces, five sites redirected in the preloader.

### The idea: do not write a loader

The preloader `0x021A28A8` already does the whole sequence — open `enemy.gp2`, extract
the member, find the `.cchr` sub-chunk, decompress to the heap, register the model,
set the record. We turn it into "load ONE species into ONE slot".

What makes it possible, and was not before §68: it takes the model code from container
1's record (`0x021A29B4 ldr r2, [r0, #4]`), and the gatekeeper now returns the REAL
record of any of the 438 species. Asking it for species X is therefore enough.

### Three words rather than a test everywhere

`DEMANDE` (0 = normal, species+1 = single load), `DEPART` and `BORNE` (start index and
loop bound). The preloader reads them blindly; graft A, which runs at the start in both
modes, resets `DEPART` to 0 and `BORNE` to the cap in normal mode.

This indirection brings two twelve-instruction grafts down to four, and removes
`patch_place`'s cap stub — its role becomes `BORNE`'s initial value.

| # | site | in DEMANDE mode |
|---|---|---|
| A | `0x021A28CC` `bl 0x021A27E8` | do not clear slots; otherwise init DEPART/BORNE |
| B | `0x021A28E0` `bl 0x0209C0FC` | return 1: a single record to size |
| C | `0x021A2900` `bl 0x0207DFA0` | **do not roll back the VRAM watermark** |
| D | `0x021A295C` `mov sb, #0`    | `sb = DEPART` |
| F | `0x021A2ACC` `bl 0x0209C0FC` | return `BORNE` |

Graft C is the most important: without it, each single load would throw away every
other model's textures (§66). Graft B bounds a leak: 0xB0 bytes per load instead of
twelve times more, and it dies with the heap on a zone change.

### THE TRIGGER GOES IN `emprunt`, NOT IN THE GATEKEEPER — two regressions paid

First try: the trigger in gatekeeper 1, with an "am I already loading" guard. Measured
result: **zero models loaded over six setups**.

Cause: the preloader queries the same gatekeeper (`0x021A2988`), and as soon as a
species of its list was missing from the map's container — which §57 had already
measured — the gatekeeper triggered a load **from inside the preloader's loop**. The
preloader called itself, overwrote `DEPART`/`BORNE`, and restarted on an inconsistent
state. The guard prevented infinite recursion, not the first reentry.

The trigger therefore lives in `emprunt` (borrow), at site `0x021A21F8`: that function
only runs on the spawn path, never in the preloader, and its role is already exactly
"the model is missing". The gatekeeper goes back to its simple 52-byte version, safely
shared by both sites.

`emprunt` has three tiers: the original function, then on-demand loading, then borrowing
as a fallback. It is 104 bytes in three pieces (`0x02073FF4` 32, `0x020E735C` 32,
`0x02074014` 40).

A saving that made it all fit: **`0x021A2738` IGNORES its first argument**
(`movs r6, r1` then `bl 0x200f398` to fetch the table itself), so no need to preserve
r0 — two instructions fewer.

### THE TRAP BEHIND BOTH REGRESSIONS: the size of the source context

Second try: field setup no longer finished. Dumping the command words said it all:

```
WORDS = [37357140  2  3]      <- DEMANDE = 0x02392FD4, a POINTER
```

`0x0206F02C` allocates a **second block** — the strings — and stores it at `+0x08`
(`0206f098 str r0, [r8, #8]`). The source table context is therefore at least twelve
bytes, not eight. With the command words at `SRC+8`, the game overwrote `DEMANDE` with
that pointer at every setup: the preloader thought it was always in demand mode,
skipped its initialization and slot clearing, and looped on random `DEPART`/`BORNE`.

**One cause for both symptoms** — zero models, then an apparently endless setup. `SRC`
now reserves SIXTEEN bytes and the words follow at `GREFFE_C + 16`.

Rule to remember: before putting data behind a game structure, read the function that
fills it up to its last `str`.

### State after the fix, measured

```
[1] town  : free after preload 41,108  models 0  CONFISCATION 16,384
[2] field : free 83,204  models 5 : 120,237,142,17,107  CONFISCATION 16,384
```

188,384 - 83,204 = 105,180 used, i.e. the source table (~21 KB) and five models (~84
KB). **~66 KB** remain in the model heap after confiscation: three to four on-demand
loads at once.

### What is left, and can only be measured by playing

The trigger only fires on a spawn, and the harness cannot cause one: the map keeps its
symbol quota and the bot never fights (REPRISE.md 6, trap 3). Emptying actor slots
from Lua is not enough — the game counts its symbols elsewhere, measured.

What to watch in game:

1. **Is the look right?** That is the goal. It must be for any species whose load
   succeeds.
2. **Stutter.** A synchronous load costs one to two frames (§66). Watch when a symbol
   appears.
3. **Texture VRAM saturation.** The known weak point: the watermark allocates without
   ever freeing, so after ten to twenty loads the cursor saturates, allocation fails and
   models load without texture. Expected symptom: black or white symbols. The fix is
   **bulk refresh** — call the preloader in NORMAL mode, which rolls back and reloads the
   residents. Not written yet, because we first need to know whether the problem really
   shows up.

## 71. On-demand loading works — and the four defects that followed

First measured proof, `scripts/lua/chargeur.lua` on `banc/states/sortie_p5.State` (the
player's savestate, just outside town — **the first bench where spawns really run**, the
map being freshly populated):

```
start    : models 172,260,208,224,241
zigzag 1 : models 172,182,85,224,241     <- 260 -> 182 and 208 -> 85
```

Two slots changed species **while walking, with no setup at all**. The mechanism is
right. Four defects remain, all found by measurement and three of them through player
feedback.

### Defect 1: graft E lost — the loader loaded nothing useful

`spawn=4 decl1=4 prech=4` but slots never changed. The graft on `0x021A2974`
(`bl GetSpecies`) existed in the module's first version and disappeared in the rewrite
around the three words. The preloader therefore loaded `GetSpecies(list, DEPART)` — an
area species already loaded — instead of the one just drawn.

**Lesson**: when rewriting a module, compare the list of redirected sites before and
after. A missing graft shows neither at assembly nor at boot.

### Defect 2: an array sized by one value, indexed by another

The preloader calls `0x0209C0FC` in TWO places: `0x021A28E0` to size its record array
(`count * 0xB0`) and `0x021A2ACC` to bound its loop. If the two values diverge, the loop
writes outside the array.

- One version bounded the loop at 5 without looking at the real count: **in town the
  list is empty**, so `Allocate(heap, 0)` then five 0xB0 records written into it — 880
  bytes overflowed. Symptom: broken textures and moving scenery.
- Another announced a count of 1 in demand mode while the index is `DEPART`, up to 7:
  1,232 bytes overflowed, hence a crash at the first spawn outside town.

**Fix**: both sites go to the SAME function, which returns `min(real count, BORNE)`.
Divergence becomes impossible by construction.

### Defect 3: I was starving the asynchronous request heap

`talon_source` builds the 438-species table (~21 KB) and `talon_borne` only leaves 16 KB
to `ctx+0x11C0` — **the asynchronous file request heap** (`0x021C20B4` passes it in r2 to
`0x0202FD0C`). On a map that loads a lot through that path, NPCs, shops and scenery no
longer arrive: **stretched textures**.

First fix attempt: take nothing when the model heap is small, threshold 0x18000, on the
idea "an indoor map has a small heap". **Wrong, and measured**:

| map | model heap |
|---|---|
| town (100) | 62,280 |
| **church (109)** | **171,424** |
| field (20002) | 188,384 |

The church therefore passed for field. Threshold raised to **0x2C000** (180,224), between
the church and the field.

### Defect 4: two decisions, two criteria — and the second was free

With a single threshold compared to the REMAINING free space, the bound no longer fired
at all: on the field, free space after preloading drops to ~77 KB, below any threshold
that excludes the church.

Two criteria were needed, and the second existed without writing anything:
**`SRC[0] != 0` is exactly the "this map has monsters" flag**, since `talon_source`
decides whether to build the table. `talon_source` therefore decides BEFORE preloading on
heap size; `talon_borne` acts AFTER and only checks whether a table was built.

### What is left, and why it does not fit

**Eviction.** The replaced model is never freed: rotation reuses the SLOT, not the
memory. Each load therefore permanently uses ~18 KB. Measured: `greffeA=9` but
`greffeC=6` — in three calls the preloader gives up in between, and there is only an
`Allocate(heap, count * 0xB0)` followed by `beq` there. The heap is full. Hence **two to
three right looks per area, then back to borrowing**.

Two costed remedies, neither fits:

| remedy | cost |
|---|---|
| remember the blob per slot (graft on `0x021A2A30`, which returns the pointer) + 8-word table | 56 + 32 = **88 bytes** |
| empty and reload in bulk on failure (heap `Reset`, rebuild the table, normal preload) | **~48 bytes** |

Space left after P4: **~70 bytes in four fragments of 4 to 28**. The largest hole is 28
bytes, and three splits already produced two of the four defects above.

**THE THRESHOLD IS ALSO A DEBT.** The right criterion for `talon_source` is "is the
preload list empty", not "is the heap large". It costs about fifteen instructions. Only
three maps were measured: another indoor map with a heap above 180 KB would fall back
into defect 3.

Both debts point to the same place: **the BSS bootstrap** (§69), which gives 395 KiB and
would allow both eviction and the right test. It is now the project's critical path.

## 85. Borrowed models, and a palette theory that did not survive (23-24 September)

Two things the player reported on the same build. One is measured and fixed;
the other is still open, and the tempting explanation turned out to be wrong.

### Measured: monsters wearing another monster's model

`hud.lua` compares an actor's `+0x08` pointer to the loaded model records — it
deduces nothing. On the player's own field savestate, **2 of the 5 monsters
present** wear someone else's appearance: `hippotigrulk` shows as
`chef troll`, `cavalier de braise` as `AU-1000`. Against **1.3 %** measured on
15 September, when the remedy was deferred as not worth the risk. At this rate
the arbitration is different, and the remedy is now built (see below).

### Not established: the palette VRAM as the cause of the wrong colours

In his battle savestate the command box is pale blue with dark text where it is
dark blue with white text everywhere else. The frame texture manager keeps two
bump allocators, rolled back together by `SetFrmTexVramState` (`0x0207DFA0`):

| global | what |
|---|---|
| `0x0210CF88` | palettes: `[0]` base, `[1]` **cursor**, `[2]` limit = `0x4000` |
| `0x020F1F14` | textures: `[1]` cursor |

Graft C deliberately skips that rollback in on-demand mode (§66), so the
cursor only ever rises inside a scene — `vram_fuite.lua` over 5 400 frames:
`0x1990` to `0x39B0`, **zero decreases**. And `0x39B0` is exactly what the
broken-colour savestate reads: 90 % of the limit, against `0x1090` (26 %) in a
healthy one.

**That looked conclusive and it is not.** A town loaded from scratch, where no
on-demand load has happened and where every colour is correct, reads `0x39B0`
too. A high cursor is therefore normal and proves nothing. A guard was written
on top of this theory and removed the same day: it would have killed variety
for no reason. The wrong colours stay unexplained.

### Built: never show a model we do not have

The remedy written down on 15 September and left unbuilt — "ask for the drawn
species' model, but this time spawn a species already loaded". Its home is one
instruction:

```
021a21f8  bl   emprunt          ; returns the model record for species sb
021a21fc  ldrh r1, [r6]         ; <- the graft goes here, sb still unused
021a2220  mov  r1, sb           ; the palette lookup uses sb
021a2268  strh sb, [r8, #2]     ; the actor's species is written from sb
```

`emprunt` now writes the species of the record it actually served into a blob
word (`SERVI`, zero when it served the right one), and the graft at
`0x021A21FC` substitutes it into `sb` before anything reads it. One site, and
the palette, the actor's species, its hitbox and its shadow all follow
together. `lr` is free there — the `bl` on the previous instruction has already
clobbered it — and `r0` carries the record, so the graft leaves it alone.

Checked in the built ROM: `0x021A21FC` holds `E1D610B0` (`ldrh r1, [r6]`) on
disc and reads back as a `bl` into the blob once the game is running.
