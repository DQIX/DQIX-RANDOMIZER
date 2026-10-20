# 20. Mini medals: Cap'n Max Meddlin's rewards

## 103. Two hard-coded tables in overlay 4 (ZER-55, 15 October 2026)

**Where.** Cap'n Max Meddlin' (Capitaine Zac Amédaï) reads two tables from **overlay 4**
(RAM `0x021536E0`, the slot shared with overlay 6), 4-byte records: `u16` number of
mini medals, `u16` item id (the `itemdt` ids of `objets.py`). Found by scanning the ARM9
and every overlay for runs of (strictly increasing count, catalogue item) pairs; nothing
else in the ROM matches.

| table | address | entries | vanilla |
|---|---|---|---|
| milestones | `0x02170010` | 10, then `(0, 0)` | 4 thief's key, 8 Mercury's bandana, 13 bunny suit, 18 jolly roger jumper, 25 transparent tights, 32 miracle sword, 40 sacred armour, 50 meteorite bracer, 62 rusty helmet, 80 dragon robe |
| shop | `0x0216FFF8` | 6 | 3 prayer ring, 5 elfin elixir, 8 saint's ashes, 10 reset stone, 15 orichalcum, 20 pixie boots |

The milestone search at `0x0216799C` walks the table with a hard bound of 10
(`cmp r3, #0xa` at `0x021679B0`) and returns the first entry whose count is above the
**total of medals already handed over**; the code references the tables from literal
pools at `0x02167A08`, `0x02167B74`, `0x02167CFC`, `0x0216823C`/`40`, `0x02168314`,
`0x021683C8`, `0x02168484`/`88`.

The dialogue (`data/bin/menu/str_mdl.gp2`) is a template: `<val_3>` for the count and
`<INDEF_ART_SGL_I_NAME>` for the item, so changing the tables needs no text change.

**Save data** (community save editor layout, CRC32 checksums verified on the player's
save): the total handed over is the `u32` at `+11460` of each 32 KB slot; mini medals in
the bag are the common-item count for id 22039 (ids at `+7664`, counts at `+7968`). The
player's post-game save: 54 handed over, 5 in the bag.

### Mini medals in a randomized game

Measured in `treasure.nsarc`: vanilla places a mini medal in **36 red chests** and in
15 draw-table lines (blue chests ranks 3-5, grottos 3-9, pots 8-10, 18, 20). Since 1.2
the medal is one item of the 1,082-item pool like any other, so the randomized loot
keeps **about one** (v17e: one red chest, no table line). The player's decision
(15 October 2026): keep them rare, no pinned medal — "la difficulté sera d'en trouver" —
and divide every count by 4 instead.

### The randomizer (`scripts/patch_medailles.py`, `--medailles`)

- Counts divided by 4, rounded half up, at least 1: milestones 1, 2, 3, 5, 6, 8, 10, 13,
  16, 20; shop 1, 1, 2, 3, 4, 5. `--medailles-seuils-vanilla` keeps the game's counts.
- Items: within one star of the vanilla item (`rarete.rouge`), or any pool item with
  `--medailles-chaos`. The thief's key (a key item) stays at the first milestone; the
  mini medal itself is never a reward; all 16 items are different. The 4-5-star shop
  rule (ZER-49) does not apply here, as in vanilla (player).
- Own generator (`random.Random("medailles:<seed>")`); `diff_roms.py` sees overlay 4
  alone (filed under AUTRE).
- In both presets of the app, with `--medailles-chaos` in "Total chaos" and in
  `--chaos-total` (player, 15 October 2026, after the shop was checked in play).

**Checked in play (CONFIRMED, player, 15 October 2026, v17f):** with a save copy set to
12 medals handed over and 10 in the bag, handing them over gave the three randomized
milestones at 13, 16 and 20, then the Cap'n's Curtsy and the shop announcement; buying from the shop works too.
