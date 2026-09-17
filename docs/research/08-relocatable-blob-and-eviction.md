# 8. The relocatable code blob, eviction and field records (§72–§78)

Part of the [research notes](README.md). Sections keep their original numbers.
This is the architecture versions 1.0 and 1.1 ship with.

## 72. CODE SPACE: three failures, and the only method that does not gamble

This section replaces the promise of §69 ("the BSS bootstrap will unlock everything"):
the BSS was not used, and three other locations failed before the right method was
found. That is the real achievement of September 9.

### What the player saw, and what started the hunt

Over four builds in a row: "still texture bugs in town, like some textures are
stretched". Indoors as in town, never on the field. Monsters, for their part, worked:
"the first one that spawns, the model does match the monster".

### Failure 1: zero padding in the ARM9

**THE CANARY IS THE WRONG TEST, and §69 itself says so**: it proves a region is not
WRITTEN by the game; it says nothing about whether it is READ. A range of zeros can
perfectly well be a table the engine consults — default parameters, a matrix,
coordinates.

Bisection with the player as oracle, since only they see the textures:

| build | content | interiors |
|---|---|---|
| `A` | gatekeeper + source table | **clean** |
| `B` | `A` + confiscation bound | **clean** |
| `D` | `B` + ONE pass-through graft at `0x020E7100` | **broken** |

A single graft, which does nothing but call the original function, and textures
break. So it is not what it does: it is where it is. The eight regions "validated by
canary" that day are all suspect.

Read probe (`scripts/lua/lectures.lua`): **unusable**, `event.onmemoryread` does not
fire in this core — zero reads everywhere, including on controls that are certainly
read. Lesson: a zero without a positive control is worth nothing.

### Failure 2: the tail of the ITCM

Measured on the autoload list: block 0 to `0x01FF8000`, data 5,952, bss 23,360, so
the end is at `0x01FFF280` — and the ITCM is 32 KiB. **3,456 bytes that nothing
declares**, neither the block's data, nor its BSS, nor the linker.

To put code there without a bootstrap: enlarge the block (`size` 5,952 -> 29,532,
`bss` 23,360 -> 0, data = original + 23,360 zeros + our code). crt0 copies, the
game's BSS ends up zeroed as before, our code lands at a fixed address. Elegant — and
**crt0 refuses**: the ROM hangs at boot, PC stuck in the wait loop
(`work/dq9_E.nds`).

Isolated from the content: same enlargement filled with ZEROS, no site redirected —
**hangs too** (`work/dq9_F.nds`). So it is the restructuring, not the location. Module
kept: `scripts/patch_itcm.py`, with its measurements. *(§74 shows these "hangs" were
a broken probe; the ITCM path was not retried.)*

### Failure 3: dead code

The right test for CODE exists and works — execution watching, with a mandatory
positive control. Two very different sessions, savestate outside town then cold boot
with menus and interiors, `Allocate` control at 5,692 then 1,754:

```
0200341C (2080 b)    779 /    669   ALIVE (silent at load, revealed by MENUS)
0204C044 (1500 b) 136594 /  80576   ALIVE
02002CB8 (1888 b)      0 /      0   silent
0200702C (1732 b)      0 /      0   silent
0200884C (1368 b)      0 /      0   silent
```

Written over `0x02002CB8`: **the ROM hangs at boot** (`work/dq9_G.nds`), while the
same loader in padding booted (`work/dq9_p10.nds`). So it was called — during boot, or
through a table built at run time: exactly the caveat §33 had stated.

**Execution watching is not enough either.** And `0200341C`, silent at load then
revealed by a menu, shows why: no session covers everything.

### The method that does not gamble: ask the game for memory

`SafeAllocator::Allocate` returns a block the game GUARANTEES is free. No more canary,
no more watching, no more "probably".

Four primitives, all identified by disassembly that day:

| EU address | role | how found |
|---|---|---|
| `0x02032554` | `Allocate(heap, size)` | known |
| **`0x020750A8`** | **NitroFS file read** `(path, buffer, &size)` | through the caller of `data/prm/skilltable.bin` (`0x0209A410`) |
| **`0x020C8300`** | `DC_FlushRange(address, size)` | scan for `mcr p15, c7` |
| **`0x020C833C`** | `IC_InvalidateRange(address, size)` | same |

The last two are essential: we write CODE through the data cache, and instruction
prefetch would not see it.

### The architecture

**The bootstrap**, 100 bytes, in OWNED space — regions played for hours by the player
(`v14`, `v29`, `v40`, `B`). It runs at every setup: allocates 1,024 bytes on the model
heap (where the bound left 50 to 92 KiB), reads `data/prm/dq9rand.bin` into it,
flushes the data cache, invalidates the instruction cache, then hands over to the
blob's installer. It pops before jumping, so the installer returns directly to its
caller — the four bytes gained that way are exactly what was missing to fit in 100.

On failure — allocation refused, file missing — it returns without installing
anything: sites keep their original calls and the game behaves as without the loader.
Clean and free degradation.

**The 48 missing bytes** come from graft A2, down from 140 to 92: its container
membership check and model code test no longer make sense since the gatekeeper queries
the source table (§68), which always finds the species and always with a real code.

**The blob**, 404 bytes out of the 1,024 allocated, fully RELOCATABLE:

```
+0x00   header: the installer's offset
+0x04   words    DEMANDE / DEPART / BORNE
+0x10   table    seven pairs {site, target offset}, then a zero
+0x50   installer
+0xB8   the five grafts
+0x12C  the trigger, IN ONE PIECE
end     the literal pool
```

Data precedes code so every access is a BACKWARD offset, the only direction
`sub rX, pc, #n` can express.

What "relocatable" imposes:

- call into the game: `ldr ip, [pc, #{Lx}] ; mov lr, pc ; bx ip`
- branch: `ldr pc, [pc, #{Lx}]`
- access to our data: `sub rX, pc, #{@@label}`

Checked on reading back: `greffe_a` starts with `sub r1, pc, #0xbc`, i.e.
`base+0xc0-0xbc = base+0x04` — the words, whatever the block's address.

This two-instruction overhead per call was unthinkable when counting every
twenty-four bytes; it is painless in a 1,024-byte block, and it removes SPLITTING —
the source of two of §71's defects and of the two failures of §58 and §61.

**SEVEN sites rewritten at run time**, not six: the preloader's six, plus the trigger
call in `emprunt`. The seventh is a `mov r0, r0` in the ROM, which gives the clean
degradation.

### Two tools added to the assembler, and why

- **`{@@label}`**: the pc-relative offset to a label, i.e. `(here + 8) - target`.
  Essential for a relocatable block to reach its own data. **The assembler computes it,
  never us**: a literal read four bytes too far (§58) and a shared exit off by one
  instruction (§61) are the two most expensive failures of the project.
- **`etiquettes_out`**: returns label positions, to write reserved data (site table,
  command words) after assembly.

### What remains

1. Add `data/prm/dq9rand.bin` to the ROM (ndspy), put the bootstrap in owned space —
   100 bytes that are not contiguous there, so **in two pieces** — and hook it to setup.
2. Put the `mov r0, r0` in place of `emprunt`'s `bl trigger`, at the address the table
   expects.
3. Remove site redirection at build time: the installer does it.
4. Cold boot, then in-game test.
5. **Finally eviction**, with 620 bytes of margin in the blob: free the replaced model,
   so that ALL spawns get the right model and not only the first.

## 73. The relocatable loader: complete chain, but the ROM hangs

Follows §72. Everything was built and checked piece by piece; the whole does not boot.
Exact state at the end of the September 9 session.

### What is established, checked

- **The four primitives**, identified by disassembly: `0x02032554` (Allocate),
  **`0x020750A8`** (NitroFS file read), **`0x020C8300`** (DC_FlushRange),
  **`0x020C833C`** (IC_InvalidateRange).
- **The blob**, 836 bytes, fully relocatable: twelve sites in its table, header holding
  the installer offset (`+0xB0`), pc-relative accesses checked correct
  (`sub r1, pc, #0xbc` lands on the words).
- **The bootstrap**, 140 bytes, fits exactly in owned space (area: 280 of 280, with the
  bitmap at 48 and A2 slimmed to 92).
- **The file** correctly added: `dwc/dq9rand.bin`, id 7516, 836 bytes, correct header.
- **No abort**: `scripts/lua/abort.lua` no longer fires.

### What does not work

`work/dq9_J.nds` hangs at boot: constant PC at `0x020C9C0C` over the five readings of
`demarrage.lua` — the sick signature, that of `E`, `F` and `G`. Healthy builds (`p9`,
`p10`) show varied PCs. And overlay 17 is never loaded: the twelve sites read
`0x00000000`. *(§74: this "hang" was the probe's artefact.)*

### Two defects found along the way, both of the same kind

**`r1` is not the file's destination.** `0x020750A8(path, buffer, &size)` uses `r1` as
the file system's scratch, and it is the RETURN VALUE that points to the content. The
game's caller says so three lines later: `bl 0x20750A8` then `movs r4, r0`
(`0x0209A410`). Symptom: abort at `0xFFFF0108`, `lr = 34793DFE`.

**In NitroFS, a file's identifier is IMPLICIT** — it follows from the order of names in
the tree, no field holds it. Adding a name in `data/prm` gives it the next identifier OF
THAT FOLDER, that of an existing file, and shifts everything else: the game was reading
a 52,320-byte GPC2 archive. And the ROM holds UNNAMED files at the end of the table, so
"the last identifier" is not "the end of `rom.files`": you must **insert** at the
identifier the name just received. Fixed in `patch_amorce.ajouter_fichier`.

### The bisection still to do

The bootstrap does four things; each can be tested alone with `demarrage.lua`, whose
healthy (varied PCs) and sick (constant PC) signatures are known:

1. **allocate only**, then chain to the preloader;
2. **+ read the file**;
3. **+ sync the caches**;
4. **+ install**.

The first that hangs names the culprit. Suspects, in order:

- **The 16 KiB allocation at every setup**, never freed: on an indoor map the model heap
  is smaller, and a later game allocation failing would hang. Check first — reduce to the
  blob's real size (836 bytes) and see.
- **`0x020750A8` called from setup**: it purges the async queue (`0x0202F7B8`) like all
  synchronous reads, in the middle of building the map. The same mechanism suspected in
  §71.
- **Writing into overlay 17's code** while the game runs, even with caches synced.

### What the player has

`work/dq9_B.nds`: every species appears, battle, scale and hitbox are right, interiors
are clean. Only the symbol's look is borrowed — the loader is not in it. Not the goal,
but the last healthy state.

## 74. The relocatable loader installs — and the four mistakes that hid it

§73 concluded "complete chain, but the ROM hangs". **It did not hang.** None of the
suspected ROMs hung. What hung was the reading.

### 74.1 The instrument that declared the freeze

The boot probe read `ARM9 r15` once per frame and concluded a freeze if it only saw one
PC:

    PCs seen = pc=020C9C0C          -> "FREEZE"

`emu.frameadvance()` always returns **at the same point of the loop**. The PC there is
therefore always the same, whatever the game state: the probe measured its own
periodicity. The "healthy" control that had validated it (`p10`, six distinct PCs) had
been taken with a probe that sampled differently — a comparison between two instruments,
presented as a comparison between two ROMs.

**Proof**: `dq9_B3.nds`, declared hung, is **byte-for-byte identical** to `dq9_B.nds`,
which the player had validated in game (same MD5,
`f4ea3c169e68102e7c35b129f06c75df`). And the screenshot taken by the probe itself, in the
same folder, shows the game in the church, saving.

It is the **fourth** time in the project a measurement was taken with an unvalidated
instrument: the read probe without a control (`event.onmemoryread` not firing), the
bisection contaminated by the drawer, the canary "validation", and this one. The
resulting rule, valid for everything after:

> **No probe gives a verdict until it has given the expected verdict on a known case.**
> A screenshot beats a deduction: it cannot be wrong about "the game is running".

Immediate corollary: graft A2 had broken nothing, slimming it from 144 to 92 bytes was
innocent, and the five-stage bootstrap bisection was measuring a freeze that did not
exist.

### 74.2 The three real defects, found by rereading

Once the instrument was disqualified, the defects can be read in the code.

**a) The file was added twice.** `patcher()` called `ajouter_fichier(rom, blob)` at the
start — to know the path before writing the string — and a second time at the end, a
leftover from the previous version. The second `dq9rand.bin` entry in the same folder
shifted every following identifier again: the game read a neighbouring file.

**b) The bootstrap overlapped graft A2.** It was placed at `ZONE_LIBRE + 0x30 + 92`,
i.e. behind a graft A2 assumed slimmed to 92 bytes. Once A2 went back to its 140 bytes,
the bootstrap ran 48 bytes into it.

**c) `patch_place` placed a cap stub the blob does not need.** With `--chargeur` it was
already neutralized; with `--blob` it was not, and it landed on the 36 bytes the bound
already occupies (`0x020f1d50 is not free`). The blob's `BORNE` word plays that role.

### 74.3 The bootstrap moves into the drawer function

`ZONE_LIBRE` (280 bytes) holds the bitmap (48) and graft A2 (144): only 88 remain, and the
bootstrap needed 140. Rather than trimming a graft validated in game — §73's mistake — we
put it where space really exists:

    0x02073FEC   the drawer, two instructions           8 bytes
    0x02073FF4   THE BOOTSTRAP                         116 bytes  -> 124 of 132

`0x02073FEC` is **the field drawer's original function**, 132 bytes the project has
owned since P3 (graft B filled it entirely, and P3 is validated in game). The blob's
drawer only keeps eight: `mov r1, #0x8000 ; b GREFFE_A2`. The write order is imposed —
erase the 132, put the drawer at the entry, put the bootstrap behind — because the entry
is the address the game calls.

The bootstrap goes from 140 to 116 bytes through three savings, losing nothing:

| saving | gain |
|---|---|
| `push {r0, r4, r5, lr}` instead of `push {r4,r5,lr}` + `mov r4, r0`: the `pop` restores `r0` directly, the two exit `mov r0, r4` go away | 12 bytes |
| the installer returns the stub in `r1` not `r0`: no more `mov r1, r0` | 4 bytes |
| the failure exit branches to `PRECHARGEUR` relatively (`b`, 32 MiB range) instead of through a literal | 8 bytes |

### 74.4 The count mirror

`talon_borne` lives in the ARM9 and needs to know whether the map has monsters; its
criterion is "was the source table built". But the table now lives in the blob, whose
address changes at every setup. The source stub therefore copies its count into the
first word of `GREFFE_C` (`SRC_MIROIR = 0x020F1CB8`), the old `SRC` location, fixed and
free. The path string moves sixteen bytes, to `0x020F1CC8`.

### 74.5 Measurement: twelve sites out of twelve

Probe `scripts/lua/k.lua`, cold boot on the player's save, with three positive controls
(`T1` the overlay 17 hook is indeed a `bl` to the bootstrap, `T2` the bootstrap is indeed
in RAM, `T3` a screenshot).

    loop  6  frame   2041  map=  118  hook=EBFB43BC
    T1 hook      021A30FC -> 02073FF4   OK
    T2 bootstrap 02073FF4 = E92D4031   OK (push {r0,r4,r5,lr})
    12 / 12 sites installed

Two harness traps worth noting, both able to give a false negative:

- **SaveRAM is named after the ROM.** A new ROM boots without a save and stops at
  "Create a new adventure log". Copy `banc/states/dq9.sav` to
  `tools/bizhawk/NDS/SaveRAM/dq9 <label>.SaveRAM` before launching.
- **Overlay 17 arrives before the game**, from the load menu. Stopping at "the overlay is
  loaded" leaves the probe in the dialog box, where arrows move a cursor. The right
  criterion is `map != 0` (`0x020FDD44`).

## 75. The black screen: a dead pointer, not a lack of space

Reported symptom: one battle entry in two or three freezes on a black screen. Three
successive hypotheses, two of them wrong — and a savestate taken by the player **during**
the black screen settled it.

### 75.1 The two wrong hypotheses

**The async request heap starved.** The bound capped at 16 KiB what the model heap gives
it, where vanilla gives ~77 on the field. The bound's direction was reversed (keep a fixed
reserve, give the rest) and `dq9_L.nds` built. **No change.** The explanation is
instructive: `talon_borne` exits immediately when the mirror is zero, and the mirror was
precisely zero — so the bound had never been active on the field, and K and L were
identical there.

**The retry storm.** A gatekeeper rejecting everything makes the call count explode at
spawn (3,629 against 2, see §20). Measured on the frozen state:
`gatekeeper1=0 borrow=0 preloader=0 setup=0 alloc=0` over 900 frames. Nothing runs. Not a
storm.

### 75.2 The real defect, read in the frozen state

    PC at frame boundary over 900 : FFFF0108

`0xFFFF0108` is the ARM9 exception vector. The game is not looping, it crashed. In abort
mode `lr` holds the return address:

    lr = 0235ACDC     and the blob had been installed at 0235A9CC

The faulting address therefore falls INSIDE the blob — but the words read there
(`023501FF`, `7CCC809B`) are not instructions. The memory was reclaimed.

Direct confirmation, in the same state, reading the field context `r11` still designates:

    models  handle 00000000 : outside RAM
    parent  handle 00000000 : outside RAM

**On battle entry, the field context is entirely torn down.** The model heap, which held
the blob, no longer exists. The twelve sites keep their `bl`: the first one called jumps
into data.

So the defect was not a lack of space but a **dead pointer**, and none of the three memory
leads could do anything about it.

### 75.3 What closes the other doors

- **The BSS bootstrap is closed**, and §69 already said so: anything added to the image
  falls in the range crt0 zeroes at boot. There is no permanent static RAM to take.
- **No field context heap fits**, parent included: both die together.
- A RAM scan of the frozen state finds 85 `FRMH` heaps, two of them large and low
  (`02200190`, 69 KB free; `02257190`, 94 KB free). They might survive, but their handle
  has no known fixed address, and a frame heap rewinds everything at the first free: the
  gamble would be on the same order as the canary.

### 75.4 The uninstaller

Teardown reads plainly in overlay 17:

    021A31A4  add r0, r6, #0x13c ; add r0, r0, #0x1000 ; bl 0x20328c4
    021A31B8  ... bl 0x2032740      (empty)
    021A31C4  ... bl 0x203248c      (destroy)

We hook **the first call**: the blob is still alive there, the last moment it can
withdraw. The stub (44 bytes, `0x020E7328`) only knows one fixed word of the blob in the
ARM9 (`BLOB_BASE = GREFFE_C + 0x20`), written by the installer; it needs to know nothing
about the allocation. If that word is zero — bootstrap failed, or already uninstalled — it
does nothing.

The uninstaller lives in the blob, where space is free. The site table goes from two words
per entry to three: `{site, target offset, original word}`. The blob header goes from one
word to two: `{installer, uninstaller}`.

**Validated in game by the player: no more black screens.**

### 75.5 Two more defects fixed along the way

**`r0` overwritten before `CHARGE_SOURCE`.** `0x0206EFE8(context, heap)` writes
`{count, block, strings}` at the address `r0` designates. The mirror writes, added between
loading `r0` and the call, overwrote it: the 438-entry table was built INTO the mirror and
the blob's real table stayed empty. The gatekeeper therefore knew no species. Symptoms
explained at once: the mirror at zero, and "the first monster is right four times out of
five" — the only accepted species were the map's own, whose model was already loaded.

**The file system buffer, 16 KiB taken from the model heap.** Measured on the field, table
finally built: `heap 188180/188832`, i.e. 652 bytes free. The 32 KiB reserve was cut in
half by that buffer alone, never returned before teardown. Brought down to 4 KiB (the blob
is 1 KB), reserve raised to 48 KiB.

### 75.6 Measured state

Three on-demand models fit: the player sees the first two monsters always right, the third
never. Next is **eviction** — freeing a model to load another — which requires switching
this heap to ExpHeap on monster maps only, which the mirror finally makes it possible to
condition.

## 76. The on-demand loading budget, and what eviction will cost

### 76.1 The budget, finally computable

The model heap is 188,832 bytes on the field. What happens in it at setup, in order:

    file system buffer (bootstrap)                     4,096
    preloader, `BORNE` models                    ~21,500 each
    confiscation: everything except `GARDE`, to the async heap
    left for on-demand loading                     GARDE - 4,096

Measured on the player's savestate (`dq9_Q`, `GARDE = 98,304`, `BORNE = 2`):
`heap 152,020 / 188,832` at load, `173,796` after one more spawn — i.e. **21,776 bytes per
model loaded on demand**. 94,208 usable divided by 21,776 gives 4.3 models, and the player
sees "4 for sure, sometimes 5".

Progress is entirely explained by a single number:

| version | GARDE | buffer | on-demand models | observed |
|---|---|---|---|---|
| N, O | 32 then 48 KB | 16 then 4 KB | 0.6 then 2.0 | "the first two" |
| P | 48 KB | 4 KB | 2.0 | "the first two" |
| Q | 96 KB | 4 KB | 4.3 | "4 for sure, sometimes 5" |

**And the ceiling is reached.** With `BORNE = 2` only ~141 KB are free before confiscation:
raising `GARDE` to 120 KB would only gain one model and leave 21 KB to the async heap,
against 77 in vanilla. The player reported no texture defect at 58 KB, but there is no
margin left to take.

### 76.2 What a load allocates, exactly

Probe `scripts/lua/couts.lua`, hooked on the allocator during a spawn:

    alloc 1 :    704 to 1,056 b   called from 021A28F4   (the record table)
    alloc 2 : 16,136 to 20,100 b  called from 0207567C   (the model itself)

Two blocks, both on `ctx+0x113C`. The record table is `176 x (DEPART + 1)`: it grows with
rotation, and **it cannot be returned** since already filled slots point into it. A
structural leak, but of a kilobyte: the price to pay is the second block.

### 76.3 The record, and the missing pointer

Probe `scripts/lua/fiche.lua`. A record is 176 bytes:

    +0x00  halfword : a flag (1)
    +0x02  halfword : the species       (`ldrsh r1, [r0, #2]`, see TROUVE_MODELE)
    +0x04  halfword : the slot          (0x0A for slot 3: 7 + 3)
    +0x08  pointer  : THE END of the model block
    +0x0C  pointer  : that end + 0xAC

Check: slot 4, record `0237FE50`, returned block `0237FF00` of 20,100 bytes;
`0237FF00 + 0x4E84 = 02384D84`, exactly the word at `+0x08`.

**So the record does not hold the block's base.** On the current frame heap it can be
deduced (`record + 0xB0`, allocations being contiguous) but that equality disappears as
soon as we switch to ExpHeap — exactly when we would need it. We must capture the base
ourselves.

### 76.4 The eviction plan

1. **ExpHeap on monster maps only.** `talon_expheap` compares `r2` — the block size,
   already at hand in `CreateTypeA` — to the field threshold. Towns and the church keep the
   frame heap, which is precisely what fixed their textures; the field gains a `Free` per
   block.
2. **Capture the model's base.** A graft on `0x0207567C` which, when `DEMANDE` is armed,
   records the returned address in `MODELES[DEPART]`, an eight-word array in the blob. A
   thirteenth site, in the ARM9 this time.
3. **Return before loading.** In the trigger, if `MODELES[DEPART]` is armed: free that
   block, clear slot `7 + DEPART` with `0x0200FD58`, and only then call the preloader.
4. **Still to identify**: the `SafeAllocator` method that frees ONE block on an ExpHeap. The
   one we know (`0x02032628`) passes the constant 3 on the EXPH path — a global release,
   not a pointer release. *(§77.2 corrects this.)*

## 77. Eviction, the species pool, and monster behaviour

### 77.1 What limited to four models

Three successive causes, each found by measurement and not by reasoning.

**The file system buffer.** 16 KiB taken from the model heap at every setup, never
returned, out of a 32 reserve. Brought down to 4 KiB.

**Eviction applied to the wrong slot.** It looked for a free slot among the eight and always
found one — the heap only holds six models for eight slots — so it freed nothing and loading
failed anyway. It now works in **two passes**: first an OCCUPIED slot whose species no live
actor carries, the only choice that returns memory; only failing that, an empty slot.

**The competing heap was overestimated.** We thought we left 58 KiB to the async request
heap; measured on the field (`scripts/lua/asynchrone.lua`):

    async HMRF  0 / 16736   models HPXE 188328

It only received 16,736 and used **none** of it, over sixteen measurement loops. The model
reserve therefore went from 96 to 135 KiB and the preloader from two species to one.

### 77.2 What a model costs, and how it is returned

    alloc 1 :    704 to 1,056 b  from 021A28F4   the record table
    alloc 2 : 16,136 to 20,100 b from 0207567C   the model

The record (176 bytes) holds the species at `+0x02`, the slot at `+0x04` and the **end** of
the block at `+0x08` — never its base. On a frame heap the base was deduced by contiguity; on
an ExpHeap it is not. A graft on `0x02075678` therefore records the returned address, only for
large blocks in demand mode.

`SafeAllocator::Free` is `0x02032628(heap, pointer)`: on `EXPH` it calls
`0x020AF788(heap, pointer)`, a per-block release; on `FRMH` it passes the constant 3, a global
release. Hence the ExpHeap **conditioned on the field threshold** in `talon_expheap` — towns
and the church keep the frame heap.

### 77.3 The pool: a whitelist of 256

Two blacklists failed before. The mechanical criterion "never appears roaming" excluded 69
ordinary monsters and left **seventeen real bosses** in the field pool that roam as lair
symbols — Zoma, Psaro, Malroth, Dragonlord, Atlas, Equinox, King Godwyn, the three
generals and others (French names in the original notes). The player saw Equinox and one of
the generals on a plain.

The bestiary, however, numbers them: **monsters go from 1 to 256, the 256th is the
Pelagosaur, and everything after is a boss.** A criterion from the game itself.
`scripts/monstres_nommes.py` holds the 288 matching internal identifiers (a monster has
several entries, one per rank). Filtering must happen in BOTH places: the bitmap governs the
draw at spawn, the encounter tables decide what the map preloads and what its container
accepts.

The size cap goes from 32 to 48 KiB: it dated from when the preloader held five to eleven
models; the largest model in the game is 42,408 bytes, so no one is excluded for weight
anymore.

### 77.4 Behaviour: container 2's node

Spawn keeps two records in the actor: `+0x180` the container 1 record (`map+0x2F8`, scale and
box, from `mon_data`) and `+0x184` the container 2 record (`map+0x304`). Gatekeeper 2 built
the second one from scratch. Reading on live monsters:

    native     050B0093 003C0309 00371333 00000037 <next> 632600AA ...
    synthetic  00000075 00000000 00000000 00000000 00000000  00000000 ...

Eight words of behaviour parameters against a single field. Hence motionless, unresponsive
monsters, then an abort: the script machine (`0x020B4B00`, `ldrh lr, [r2]`) reads its
resource at `[r4+0xD8]`, finds it null, takes a branch that sets `r2` to zero and dereferences
anyway.

**And there was only one node for all monsters**: two live actors pointed to the same address
and the species field flipped from one to the other. There are eight now, in rotation, each
**a copy of a native node** of the map with only the species corrected: borrowed but valid
behaviour.

WHAT REMAINS FOR THE REAL PARAMETERS. Container 2 is built at setup by `0x021B5348`, one by
one, from the entries of the map's preload list (`map+0x44`): `0x0209C0D0` extracts the
species, `0x0202FED8` fetches the resource, `0x0206EE90` turns it into a node. The parameters
are therefore **attached to the species** and not the map — they are reachable. The resource
name remains to be identified and its load triggered at spawn. *(Done in §78.)*

### 77.5 Pc-relative addressing, in two steps

Three builds failed because a `sub rX, pc, #{@@label}` stopped being encodable as the blob
grew (1,048 then 1,044 bytes). The blob's fifteen data accesses now use two instructions,
`d & 0xFF00` then `d & 0xFF`, encodable by construction whatever the size. The pair must stay
on two consecutive lines: the second recovers the first's `d` by SUBTRACTING four from its
own — adding it shifted the target by eight bytes. The assembler now names the faulty line
when keystone refuses.

## 78. The field record: where it is, who returns it, and what it holds

Section written on September 15, after 1.1. It **corrects** §77's reading, which attributed
to the record an actor field that does not depend on it.

### 78.1 Size is NOT in the actor structure

Actor fields `+0x5C`, `+0x5E` and `+0x60` are **266 for everyone**, including a species whose
record the game builds itself at setup. Decisive measurement: species 12 had a record at 4915
(the game's value, not ours) and an actor at 266. Concluding from those 266 that "the record
is missing" was therefore wrong; it is simply a field that is 266 everywhere.

The size governing the collision box is the **field record**'s, at `+0x08`, in 12-bit fixed
point.

### 78.2 The record, 0x14 bytes

```
+0x00 u16  species
+0x02 u16  field 1 | field 2 << 8     (settings)
+0x04 u32  field 3                    (behaviour, copied as is)
+0x08 u32  size (12-bit fixed point) | attack << 16
+0x0C u16  defense
+0x10 u32  next record
```

A map's records form a linked list from `[map+0x304]`. Setup only builds them for species the
map preloaded.

### 78.3 Who answers when the record is missing

Looking up a species in that list goes through five overlay 17 sites: `0x021A2164`,
`0x021A2178`, `0x021A22F0`, `0x021A2988`, `0x021A299C`. The blob grafts them onto a
"gatekeeper": if the species is in the list, it returns its node; otherwise it makes one in a
circular pool it owns.

**Two measured consequences:**

1. The pool must cover simultaneous actors. Twelve actors can coexist; with eight nodes, a
   spawn rewrote the record of a monster still alive.
2. Writing the record **when the model loads** is too late: the game has already asked the
   gatekeeper for its record and uses what it got. Measured: record present and correct in
   the map's list, monster at 266 anyway.

### 78.4 Values come from `fld_mondata.bin`, embedded

`data/prm/fld_mondata.bin`: 15,840 bytes, 438 records, the first at offset 40, fixed stride of
36 bytes, u32 identifier at `+8` (1 to 900). Size is an **IEEE float** there (field 4)
converted to 12-bit fixed point:

```
mantissa = (bits & 0x7FFFFF) | 0x800000
fixed    = mantissa >> (138 - raw_exponent)
```

Check: recomputed for the eight species whose record the game builds itself at setup, and
compared to what it writes in memory — **eight out of eight identical**, fixed point included.

**This file cannot be read from memory on the fly.** The pointer the record constructor
(`0x0206EE90`) receives — the one a stub at its entry captures — starts with `GPC2`: it is the
compressed archive, which the function decompresses itself. The first six words read in game:
`32435047 0005A259 08C00000 ...`. The table must therefore travel with the code, computed at
build time.

### 78.5 The embedded table

384 then 336 bytes of index (identifier -> entry number) followed by a **twelve**-byte entry
per drawable species:

```
+0x00 u16  field 1 | field 2 << 8
+0x02 u16  defense
+0x04 u32  field 3
+0x08 u32  size (12-bit fixed point) | attack << 16
```

Two traps, both hit:

- **The stride is twelve bytes.** `r2 + r2*2 + r2*8` makes eleven: each entry was read
  straddling the previous one. Jellyfish-type species got 15,362 instead of 2,867 — five times
  too big — and the behaviour field got bytes from the neighbour, which **crashed the game when
  fleeing a battle**. The right expression is `r2*4 + r2*8`.
- **`0xFF` cannot be used as a "species absent" marker** with 256 species: entry number 255 is
  exactly `0xFF`, and the 256th species (identifier 334) was taken as absent. The test uses the
  **drawable species bitmap**, the one the draw graft already uses — same information, no
  ambiguity, zero extra bytes.

### 78.6 The blob's ceiling, and its formula

The file reader places the content inside the buffer the bootstrap allocates and returns a
pointer offset by about 1,532 bytes: usable space is `BUFFER_SIZE - 1532`. Beyond it, the blob
**is not loaded at all** — no install, no spawns, not found in memory — rather than "loaded
truncated". Measurements: with an 8 KiB buffer, 5,932 bytes pass, 6,044 do not. 1.1 is 5,920
bytes.
