# 6. Rotation in play: freezes, fixes and the allocator wall (§58–§64)

Part of the [research notes](README.md). Sections keep their original numbers.

## 58. The two offset mistakes, and what the player's savestate made possible

The player provided a savestate **on an encounter map, standing still**
(`banc/states/transition_v36.State`). That was the state the test bench was
missing: the spawn tick really runs there — 30 calls per 60 frames — so graft B
and rotation are exercised. Both mistakes below were invisible without it.

### Mistake 1: a literal read four bytes too far

```
0x02073ff0  ldr r4, [pc, #0x38]   ->  0x02074030   (first word of the rotation)
            the literal is at         0x0207402C
```

`r4` therefore held `0xE92D41F0`, the `push` opcode read as a table address: data
abort at the first spawn. Exact symptom reported by the player — *"I leave town,
as long as I don't move it's fine, as soon as I take a step the game freezes"*. No
monster spawns in town, hence a flawless cold boot. Cause: a literal offset
computed by hand with the number of WORDS (17) instead of the number of
INSTRUCTIONS (16).

### Mistake 2: a shared exit moved by one instruction

Removing the budget write at the start of piece C moved the exit `pop` back one
instruction; the two branches of piece A still targeted the old place, i.e. the
`movs` after the `pop`. **Seven words leaked onto the stack at every tick call**,
and its caller then popped a corrupted return address.

```
control v36 : calls=30 per 60 frames, regular counter
broken v37  : calls=1, then never again — no visible crash
```

### The two safeguards adopted

1. **Labels in the assembler.** `"name:"` names an address, `{@name}` returns it.
   No more instruction index counted by hand. And the address of the rotation's
   shared exit, shared between two pieces, is **computed** by looking for the
   `pop` in the line list.
2. **Literal pool check.** Every `ldr rX, [pc, #N]` produced must target a word of
   its own graft's pool, otherwise the build fails. Mistake 1 would have been
   caught at build time.

### The gatekeeper replaces the budget in graft A2

Measured on the player's savestate: `list 12 (6 outside container)`. Graft A2 drew
from the 256 allowed species, the container only holds 150: half the list could
not get a model. The graft now queries `0x0206F500(map+0x2F8, species)` — the
lookup the preloader itself uses — and redraws while the gatekeeper refuses, with a
fallback after 24 tries so it never returns an empty list.

### Measured result, end to end

| | before rotation | after |
|---|---|---|
| list outside container | 6 of 12 | **0 of 12** |
| models loaded | **1** | **9 then 10** |

Over four consecutive rotations: 10, 3, 10, 10 models, i.e. **8.2 on average**,
one rotation every 256 tick calls — from 8 s in the lab to 25 s in real play,
depending on how fast the map asks for symbols.

And the cadence is indeed counted **in tick calls, not frames**: the tick is only
called when the map lacks symbols. At 1,024, rotation only fired once per map —
which the player had seen as *"only one monster spawning"*.

## 59. The v37 freeze, and the real cause: bad container records

Reported symptom: *"it doesn't crash anymore but I only get one monster"* on v36,
then on v37 *"the game freezes after 2-3 seconds when I start walking around"*.
The player's savestate, taken standing in front of the town, reproduces the freeze
in the lab — and that is what made everything possible.

### The freeze happens AFTER the rotation

```
block  8  setups=1  models= 3
block  9  pc=FFFF0108   r0=r4=r5=006E6F6D   lr=020D903C
```

`0xFFFF0108` is the ARM9 BIOS exception vector: a data abort. The faulting
instruction is at `lr - 8`, i.e. `0x020D9034 ldrh r2, [r5, #6]`, with
`r5 = 0x006E6F6D` — the bytes "mon ", the tail of "_f.mon".

### The false lead: the formatter's buffer

`0x021A29C0` formats the name with `sprintf("%s_f.mon")` into a buffer at
`sp+0x54`, which only has 16 bytes before `sp+0x64` and `sp+0x68`, two arguments
passed right after. I moved the buffer to `sp+0x6C`, where the function seems to
use nothing. **The freeze moved without going away**: the abort moved into
`0x020CBF98`, with the same "mon " value. So `sp+0x6C` is not free: the structure
passed by `add r0, sp, #0x64` extends past eight bytes. Patch removed.

### What settled it: instrumenting the call

Hook on `0x021A29C0`, logging `r2` — the model code pointer read from the container
record:

```
frame 5870  code=022F6744  length= 5  "z016a"
block 8 : FREEZE
```

**A single call, with a perfectly valid code.** So there was never a formatter
overflow. But a dump of the container's 150 records gives:

```
code lengths : 15 unreadable | 2 empty | 1 of one byte | 132 of 5 bytes
18 faulty records: the FIRST 18 (species 35 to 53)
```

Their `+0x04` field points **into the record block itself** (0x022F3C98, while the
block spans 0x022F3050 to 0x022F40B8), while fields `+0x00` and `+0x14` point to
another heap (0x0232xxxx) — they are duplicated by a different allocator
(`[map+0x14]` versus `[map+0x10]`). The exact corruption mechanism remains open;
what matters is that it **predates our grafts**: v29 and v34 never touched it,
since they did not draw from the container. *(Cause found in §64: graft C itself.)*

### The fix: graft A2 validates the model code

`0x0206F500` returns the record, not just a boolean. The graft uses it:

```
ldr  r0, [r0, #4]        the model code
ldrb r0, [r0, #5]        its terminating zero
cmp  r0, #0
beq  keep                valid code: keep the species
```

Every valid code is exactly five characters ("z061a"), hence a zero at `+0x05`;
binary content only puts a zero there one time in 256. Four instructions — exactly
what was left in the graft's 128 bytes.

### Result

Five different draws (frame offsets 0, 137, 401, 913, 2111), sixty blocks of thirty
frames each:

| offset | rotations | models at the end | freeze |
|---|---|---|---|
| 0 | 3 | 11 | no |
| 137 | 4 | 8 | no |
| 401 | 4 | 10 | no |
| 913 | 5 | 9 | no |
| 2111 | 7 | 10 | no |

Against a systematic freeze before the fix, at the three offsets tried. And cold
boot stays good: context created, heap at 40,912, container at 147 species, list
at 12.

## 60. The freeze was not fixed, and what really causes it

v41 (identical to v40 except cadence, 512 instead of 256) **freezes at all three
frame offsets tried**, with the original signature:

```
lr=020D903C   r0=r4=r5=006E6F6D   pc=FFFF0108
```

So v40 simply got lucky on my five draws. Validating the model code (§59) was
necessary but not sufficient.

### Isolation chain, by elimination

| variant | freeze |
|---|---|
| v41, full rotation | **yes**, 3 offsets of 3 |
| v42, rotation WITHOUT forced setup (`mov r0, r0`) | **yes** |
| v41, trigger neutralized (`movs r7, r0` restored) | no, 2 x 60 blocks |
| v41, list clearing neutralized (`strh` -> `mov r0, r0`) | **no**, 2 x 60 blocks, and setup still fires twice |

**The culprit is clearing the preload list mid-game**
(`strh r0, [map+0x44+0x18]`), not setup — which fires harmlessly when the list is
not cleared.

The abort lands in `0x020D9034 ldrh r2, [r5, #6]`, reached through
`0x020D95D4 ldr r4, [r4]`: the FIRST WORD of the preloader's archive structure
(`sp+0x64`) holds string bytes. The preloader is spread over several frames — six
loops in five frames, measured in §57 — and it rereads the list count **at every
loop** (`0x021A2AC8`) while it sized its record array (`count * 0xB0`) once and
for all on entry. Changing the count under its feet is therefore structurally
dangerous.

### What would be needed, and why it is not done

The count must never go down: write the twelve species **over** the old ones, in
place, without touching the count. That requires graft A2 to RETURN the species
instead of passing it to `AddSpecies`, plus an indexed write loop in the rotation
— about ten instructions. But A2 is 128 bytes of 128, the rotation 16/16, 18/18
and 48/52: **one word** is left.

A way to free them: the class table no longer needs two bits per species since the
budget died (§58) — one is enough, bringing it from 96 to 48 bytes and freeing
twelve words in the area.

### The safe setting, meanwhile

`--sans-rotation` keeps everything else: draw at zone load, graft B (no invisible
monster), containers at 150 species. Checked freeze-free over 2 x 60 blocks.

**Graft C remains required even without rotation**: graft A2 checks container
membership before adding a species, and without a wide container that test would
reject almost everything — the fallback would then add unvalidated species,
precisely those whose record is corrupted.

### And the "single species, reset every second" idea

Tested (`--tirages 1 --periode 64`). It does not hold: the list never holds a
single species but **one plus the live monsters**, whose models are reloaded at
every rotation. Measured over 40 blocks, against the 12-draw setting:

| | distinct species seen | reloads |
|---|---|---|
| 12 draws, cadence 512 | 9 | 1 |
| 1 draw, cadence 64 | 14 | **9** |

More variety, but nine times more stutter — and the freeze was still there.

## 61. Rotation repaired: writing IN PLACE, and the bit that paid for the space

### The principle

The freeze came from resetting the preload list count mid-game (§60). Rotation now
writes species **over** the old ones, at indices 0, 1, 2... and **never touches the
count**. The preloader, which rereads that count at every loop after sizing its
record array on entry, no longer sees anything move under its feet.

Nice consequence: `AddSpecies` is no longer called by the rotation at all —
measured over a zone load followed by two rotations, **12 calls in total**, all at
load.

### Where the space came from

The class table held two bits per species for a budget that is dead (§58). One bit
is enough: 48 bytes instead of 96, and the area layout becomes

| | |
|---|---|
| `+0x000` | bitmap, 48 bytes, one bit per species |
| `+0x030` | graft A2, 144 bytes (140 used) |
| `+0x0C0` | graft C, last piece, 32 bytes |
| `+0x0E0` | rotation, piece D, 48 bytes (36 used) |
| `+0x110` | cadence counter |

### Graft A2's "return" mode

The encmons parser calls A2 instead of `AddSpecies` with r1 = identifier read from
the file, always below 512. **Bit 15 is therefore free**: set to 1
(`MODE_RENDRE`), the graft validates the species and RETURNS it in r0 instead of
adding it. The rotation uses that to write it itself.

### Two assembly traps paid

`strh` does **not** accept a shifted index on ARM (addressing mode 3):
`strh r1, [r4, sb, lsl #1]` is refused by the assembler, the offset must be
computed in a register. And the actor slot offset `4 * 0x70` was folded into the
literal to recover the word lost that way.

### AND A METHOD TRAP, MORE EXPENSIVE THAN THE OTHER TWO

**A savestate taken on one ROM freezes under another ROM, even with an identical
layout.** `ville_v44.State` loaded on `dq9_v45.nds` freezes within thirty frames —
with or without a RAM patch, and with no graft running. The two ROMs only differed
in 39 ranges, all in the ARM9 image.

I wrongly concluded v45 crashed. The right method is to load **the ROM the
savestate comes from** and apply the new code in RAM. Earlier field tests escaped
this by luck: their savestates were taken in the middle of a map, not in town.

### Measurements

Eight draws (frame offsets 0, 137, 401, 613, 913, 1499, 2111, 3001), sixty blocks
of thirty frames each, on the field savestate:

| | rotations | models at the end | freeze |
|---|---|---|---|
| v45 | 1 to 4 | 8 to 11 | **none in 8 tries** |
| v41 (list clearing) | 1 | — | freeze in all 3 tries |

And on the town savestate, crossing the boundary: 12 species requested, **2
outside the container, 9 models loaded**, then a new set at every rotation. Cold
boot: context created, container at 147 species, no exception.

### What is still imperfect

When several live monsters are the **same** species, it is rewritten that many
times (reading: `188, 188, 90, 188`), costing two or three slots out of twelve.
Deduplicating would require scanning the list before each write, about eight
instructions — twelve free words remain in piece D, so it is doable if the set
feels too poor in game.

## 62. The missing safeguard: rewrite nothing while the list is incomplete

In-game feedback on v45, three symptoms: a single monster looping after a teleport,
NO monster at all after a round trip to town, and a black screen on a zone change.

### The measurement, on a savestate taken in town

```
frame 2518  ROTATION  map=100  list=0  c1=150     (thirteen loops, then setup)
```

**Rotation was running in town.** And it did two silly things there:

1. It wrote twelve species while **the list count was zero**: the game never saw
   them. The flip side of writing in place — not touching the count means no
   longer CREATING it.
2. It called setup for nothing, and setup **tore down all the models**.

The same mechanism strikes during a map load, while the encmons parser is still
filling the list: rotation then rewrites a half-built list and forces a setup at
the worst moment. Hence the three symptoms.

### The fix

Three instructions at the start of piece D, before any write:

```
ldrh r0, [r4, #0x18]        the list count
cmp  r0, #12
blt  exit                   incomplete: touch nothing
```

A single test rules out both cases: the count is zero outside encounter maps, and
it grows progressively during parsing. Accepted consequence: with `--especes`
below 12, the list never reaches the threshold and rotation never fires — the price
of a three-word test.

The draw now advances `r4` itself (`strh r0, [r4], #2`) instead of recomputing an
offset: that is what freed the space. Graft A2 ignores r0 in "return" mode and
preserves r4, so nothing prevents it.

### Measurements

| situation | before | after |
|---|---|---|
| in town | 13 draw loops + a setup | **a single pass, no setup** |
| leaving town | — | list 12, **9 models** |
| field, 5 draws x 60 blocks | — | 1 to 4 rotations, 8 to 11 models, **no freeze** |
| back in town | — | list 0, counter advancing, no freeze |
| cold boot | — | context created, container at 147 |

## 63. THE WALL: setup destroys heaps, and the allocator tree cannot take it

### What the player reported on v46

A single monster looping — often the same statue — another single monster after a
round trip to town, and a black screen on a zone change, not reproducible after a
restart. "Pretty flaky".

### First defect: the feedback loop on duplicates

Reading on their field savestate:

```
models 8 : 177,177,177,177,182,84,144,83
```

**Four slots out of eight for the same species.** The mechanism feeds itself: graft
B draws among LOADED models, so 177 comes out one time in two; its actors then fill
the actor slots; rotation, which puts back the species of live actors, rewrites 177
four times; and so on until collapse to a single species.

Checked: skipping the actor scan (one word patched in RAM), models all become
distinct again — `190,144,276,258,204,126`.

### Second defect, and it is a wall

The freeze persists **even without the actor scan**, and it requires a zone
crossing FOLLOWED by a rotation: on the starting map, sixty blocks pass without
anything.

The abort, finally named:

```
0x020AF114  ldr r0, [r4, #0x18]      r4 = 0xFFFEF638
in AllocatorTree::GetParent(SignedAllocatorList*, SignedAllocatorHeader*)
```

`ElementAfter` returned a node at `0xFFFEF638`: **the global allocator tree is
corrupted**. Not a leak — the parent ExpHeap keeps its 18,002 free bytes and its
single block, measured at every setup.

The cause is structural. Setup `0x021A2FA0` first calls `0x021A316C`, which for
each context heap checks (`0x020328C4`), empties (`0x02032740`) then **destroys**
(`0x0203248C`) — and `Destroy` unlinks the heap from the allocator tree. Doing it
outside the intended life cycle, especially straddling a map change that destroys
and recreates those same heaps, ends up unlinking twice or unlinking a heap already
recreated.

I had written (§45) that setup was "reentrant and leak-free since the game calls it
from seven places". Wrong: it is reentrant **within a map's life cycle**, not at an
arbitrary moment.

### What mid-game rotation would need

Stop reusing the game's setup and load models ourselves: the preloader
(`0x021A28A8`) without the teardown, or better, the model heap converted to an
ExpHeap (§54, validated to the byte) to free and reload model by model. Both
require writing our own loading sequence — `0x0207551C` to find the member,
`0x02075664` to decompress, `0x02036814` to register, `0x0200FD48` to set the
record — about thirty instructions with clean failure handling. **Five words** are
left in the padding.

### Delivered state

`--sans-rotation`: a new set at every zone load, drawn from 150 species, no
invisible monster (graft B), no duplicates (no actor scan), no freeze — checked on
both player savestates and at cold boot. The reasonable stopping point.

## 64. The two defects the player's savestate brought down

Symptoms reported on the rotation-free version: "no monsters at all anymore, it
doesn't work". The savestate provided — just south of town, one step from the
transition — made it possible to replay six town / field round trips and settle
both, by direct comparison.

### Graft C corrupts the container records

`0x0206F240` is not made for more than twelve species. At the heart of its loop:

```
0x0206F3E8  ldrb r1, [r8, r5]        r8 = byte array, r5 = species index
0x0206F3F0  bl   0x02032554          Allocate(map heap, r1)
```

`r8` comes from `[state+0x14]`, sized for the preload list — twelve entries. With
150 species, `r5` goes up to 149: the function reads 150 bytes from a 12-entry
array, allocates arbitrary sizes on the map heap, and its string duplications end
up returning corrupted pointers. Those are the 18 faulty records of §59, whose
cause I had looked for elsewhere.

Comparison, same savestate, six passes:

| | models loaded | freeze |
|---|---|---|
| with graft C | 8, then 2, then 7 | **on the sixth pass** |
| without | 11, then 10 | none |

It only served to feed the rotation. Removed, together with the heap enlargement
that went with it: the parent heap gets 147 KiB back and the container heap returns
to 11,344 bytes.

**Lesson: do not feed a game function ten times what it expects, even when its
internal bound allows it.** The `cmp r7, #0x200` at `0x0206F324` allows 512
species; a twelve-byte side array says nothing.

### Graft B closed a loop: the game went silent

Drawing only among LOADED models removes invisible monsters, but returns -1 when
none is loaded. The game then no longer requests a monster, so nothing triggers a
reload, so no model ever comes back: **permanent silence**. Measured: ten models
after a zone load, zero after a minute of walking, and nothing afterwards.

The graft therefore falls back on the preload list in that case — at the cost of an
occasionally invisible monster, which the player had found acceptable on v29. It is
now 116 bytes and fills the whole drawer function, including the 64 bytes where
rotation piece A lived: the two became incompatible, and `--rotation` refuses to
build.

### Delivered state: `work/dq9_rand.nds`

STABLE file name, so BizHawk's save follows from one version to the next — it is
named after the ROM file (`NDS/SaveRAM/dq9 rand.SaveRAM`), and each new name
started blank.

Final measurement, six round trips: 10, 10 then 8 models, **which stay loaded while
walking**, no freeze, clean cold boot.
