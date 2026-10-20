# 18. Palette VRAM: why monster colours landed on the hero and on the text

## 101. The on-demand loader allocated wherever the cursor happened to be (ZER-40, 14 October 2026)

Players of 1.6 reported text that sometimes turns green or grey (dialogue and battle
messages), and the hero's equipment and monsters "changing colour" on the field, fixed
by entering and leaving the equipment menu. Only with monsters drawn at every spawn. §85
had ruled out the palette VRAM *filling up*; the cause turned out to be palettes
*overlapping*.

### How the game lays out palette VRAM

The frame palette manager (`InitFrmPlttVramManager`, 16 KB) is two cursors at
`0x0210CF88`: `[0]` low, `[1]` **high**. `0x020BB7DC` (`AllocPlttVram`) allocates
downwards from the high cursor when `r2 != 1`, and returns the key
`(size / 8) << 16 | address / 8`. Every loaded texture resource keeps that key in its
`TEX0` block at `+0x2C`, which is how overlaps can be read from a RAM dump.

There is no free: each owner takes a **mark** (`0x0207DFBC`, which calls `0x020BB920`)
and later **rolls back** to it (`0x0207DFA0` → `0x020BB93C`) before allocating again.
On zone load (`scripts/lua/pal_joueur.lua`, player's game, grotto):

| range | what |
|---|---|
| `0x4000-0x3AF0` | interface |
| `0x39B0-0x3990` | one 32-byte palette, allocated right after the interface (text, by the symptoms) |
| `0x3990`, `0x3390`, `0x2D90`, `0x2790` | four 0x600 blocks, one per party member; each member's equipment is reloaded inside its own block after a rollback to its top |
| `0x2190-0x1680` | the map (marks by `0x02014500`, animated every frame by `0x02014E68`) |
| `0x1190-0x1020` | field symbols and icons (`0x0203D1F8`, `0x0203F05C`) |
| below `0x1020` | the monster preloader (ovl 17), mark at `r4+0x1000` (`0x022A7D78` in this game) |

### What went wrong

The preloader rolls back to its own mark at its start (`0x021A2900 bl 0x0207DFA0`) and
takes a new mark at its end (`0x021A2AE8 bl 0x0207DFBC`). The blob's graft C skipped the
start rollback in on-demand mode (§66, §68), on the belief that it would throw away the
other monsters' textures. The trace shows it would not: the end mark is retaken after
every load, on-demand ones included, and only the preloader uses that mark (15 marks,
8 rollbacks, no other caller).

Without that rollback, an on-demand monster was allocated **at whatever the cursor was**.
The field effect system (`SetFrmTexVramState` called from `0x02043F70`, mark
`0x022A7504`) rolls back to `0x39B0` in bursts of about 25 calls. The next monster
then went straight onto the text palette and the hero's block. Measured in the player's
trace:

```
3377..3692  monsters stack normally: 0x10F0, 0x10D0, 0x1030, 0x0FD0, 0x0F90
3895        25 x rollback to 0x39B0 by the effect system (0x02043F70)
4160        ALLOC 0x60 from 0x39B0 -> 0x3950-0x39B0: the text palette and the
            top of the hero's first equipment piece
4661        player presses K: battle text in the wrong colour
```

And in the player's earlier savestate with green armour, the only overlapping pair of
`TEX0` keys is a party equipment piece (`0x38F0-0x3930`) and a model loaded after it
(`0x3910-0x3950`). Leaving the equipment menu reloads the party into their blocks, which
is why it "fixed" the colours until the next spawn.

The same skipped rollback also left the texture cursor wherever it was, so textures
were exposed in the same way.

### The fix

Graft C is removed: the preloader rolls back to its own mark, as in the original game,
and each on-demand monster is placed right under the previous one. Only `dq9rand.bin`
changes (`diff_roms.py`: MACHINE 1). Validated in play: see ZER-40.

### Tools

- `scripts/lua/dump_domaines.lua`: dumps memory domains from several savestates without
  playing (the melonDS savestate is a waterbox image, not readable offline). BizHawk's
  domain list starts at index 0.
- `scripts/lua/pal_trace.lua`: allocations, marks and rollbacks with their callers,
  on a bench savestate.
- `scripts/lua/pal_joueur.lua`: the same, while the player plays; K dumps RAM and
  marks the log.
