# 11. Shops: the shop table, its format, and what every shop sells (§83)

Part of the [research notes](README.md). Sections keep their original numbers.
This is the groundwork for a shop randomizer; nothing here is patched yet.

## 83. `shopdata1.bin`: the 37 shops of the game

### 83.1 One file holds every shop

Every shop of the normal world lives in **a single file**,
`data/bin/menu/shopdata1.bin` (3,776 bytes). It is the **only** shop file in the ROM:
a scan of the 7,481 NitroFS entries for `shop`, `store`, `sale` returns four files, and
the other three are graphics (`bg_shop2.pac`, `obj_shop.gp2`, `bm_shop.gp2`, the menu's
art and strings). `data/prm/` holds no shop parameter file.

### 83.2 The format: the same generic Nitro script as the loot

Byte for byte the format of §79.2 — the `Script` class the game uses for `treasure.nsarc`,
`maplist9.bin` and `itemsort_en.bin`. `scripts/treasure.py:lire_script` parses it as is.

```
header, 16 bytes     i32 instruction count            40
                     u32 data section offset        3744
                     i32 data section length          27
                     u32 string count                  2
```

Opcodes present: `0x65` and `0x64` (build timestamp, `2009/03/11 20:20:41`, empty stubs in the
game), `0x66` (one integer: **37**, the shop count), and `0x67` **37 times — one per
shop**. The announced count and the instruction count agree, which is the first check
`scripts/boutiques.py` makes.

### 83.3 A shop (opcode `0x67`), 22 integer parameters

```
p0         shop identifier
p1         unknown, 1 to 5
p2 .. p19  EIGHTEEN sale slots: an item identifier, or 0 for an empty slot
p20        price percentage
p21        shop kind
```

**p0, the identifier.** 31 shops carry 0 to 30 with no gap; the six others carry 32 to 37,
i.e. `0x20 | n` for n = 0 to 5. So there are two groups, a main one of 31 and a second of
6, and the high bit tells them apart. What selects the second group is not settled.

**p2..p19, the slots.** Always 18, items packed at the front, zeros after. The fill counts
are **18 (24 shops), 12 (9 shops), 6 (3 shops) and 1 (one shop)** — every count but the
last is a multiple of six, which matches a menu that lists six lines at a time. 559 of the
666 slots are used.

**p20, the price percentage.** 100 for 35 shops, **500 for exactly two** (file order #14
and #33). A shop can therefore sell at five times the normal price, and the multiplier is
per shop, not per item. Whether the percentage applies to the buy price alone is not
settled — see §83.6.

**p21, the shop kind.** Deduced, and the 37 shops are consistent with it: the value is
constant over each family of stall and never mixes a family in.

| p21 | kind | shops | what its slots hold |
|---|---|---|---|
| 0 | weapons | 8 | 138 weapons, nothing else |
| 1 | armour | 10 | shields, head, torso, arms, legs, feet — never a weapon, never an item |
| 2 | items | 10 | 84 common items and 7 accessories |
| 3 | general | 6 | items, weapons, armour, accessories in one stall |
| 4 | weapons + armour | 2 | both, no common item |
| 5 | mixed | 1 | items, weapons and school clothes (one shop only) |

Two things follow for a randomizer. **Vanilla keeps type discipline**: a weapon shop
holds only weapons, an armour shop only armour. And **accessories are item-shop goods**,
not armour-shop goods — they appear in kinds 2, 3 and 5, never in 1 or 4.

### 83.4 The census

`scripts/boutiques.py <rom> <prefix>` writes `<prefix>_shops.txt` (aligned columns) and
`<prefix>_shops.csv` (semicolon, one row per slot). Measured on the EU ROM:

- **37 shops**, 559 slots used, **330 distinct items** on sale;
- **zero key items on sale** — checked against the 88 of §79.8, so the key-item rule of
  the item randomizer costs nothing here;
- 122 of the 330 items are sold in more than one shop; the most widespread are the
  medicinal herb and the chimaera wing (15 shops each);
- what is on sale, by family, against the whole catalogue: 105 weapons of 268, 17 shields
  of 45, 50 torso of 183, 40 head of 132, 24 arms of 78, 39 legs of 85, 31 feet of 101,
  6 accessories of 52, 18 common items of 146. **Shops sell a quarter of the catalogue.**

Two pairs of shops carry **exactly the same stock**: ids 1 and 36 (armour), and ids 26 and
29 (items). Same shop at two moments of the story, or two towns sharing a list — the same
ambiguity as the twin red chests of §79.6. A randomizer that treats them as one keeps them
consistent; treating them separately is also defensible since they are distinct entries.

### 83.5 Where each shop is: settled by cross-checking a community census

`shopdata1.bin` carries no map identifier, and **no data file of the ROM links a shop id to a
place**. Checked: `maplist9.bin` (22 parameters per map, none tracking the shops),
`data/map/*`, `data/scenario/*.npc` (NPC model and position only), the town text banks
(dialogue, opcodes 1 and 2 only) and `eventlist6.bin` (cutscenes). The only occurrence of the
string `shopdata1` in the ROM is its own NitroFS filename entry, so the ARM9 opens the file by
id and the shop identifier is passed by event code.

The places were therefore settled **from outside the ROM**: the French community census on
[dragonquest-fan.com](https://www.dragonquest-fan.com/forum/index.php?showtopic=11003) lists,
town by town, what every shop sells and at what price. Its 35 blocks were parsed and matched
against the 37 stocks by item identifier. **The match is decisive**: 15 blocks land on a shop
with a Jaccard index of 1.00 (same set, exactly), and the rest sit at 0.78 to 0.94 only because
the census has typos in 21 item names. No block has a close second — the runner-up is usually
below 0.40. The file order of `shopdata1.bin` also follows the story order, which is a second,
independent clue on the same assignment.

Result, using the French town names of the census (Ablithia = Stornway, Pontaudy = Dourbridge,
Chérubelle = Angel Falls…):

| id | place | stall | id | place | stall |
|---|---|---|---|---|---|
| 32 | Chérubelle | objets (general) | 17 | Ouadi | armes |
| 0 | Ablithia | armes 1 | 18 | Ouadi | armures |
| 1, 36 | Ablithia | armures 1 (two identical entries) | 19 | Ouadi | objets |
| 2 | Ablithia | objets | 20 | Batsureg | armes |
| 35 | Ablithia | armures 2 | 21 | Batsureg | armures |
| 37 | Ablithia | armes 2 | 22 | Batsureg | objets |
| 3 | Le Plicata | objets (general) | 23 | École Saint-Sévaire | armes/armures |
| 4 | Bacilli | armes | 24 | Dracocardis | armes |
| 5 | Bacilli | armures | 25 | Dracocardis | armures |
| 6 | Bacilli | objets | 26 | Dracocardis | objets |
| 7 | Abbaye des Vocations | objets (general) | 27 | Kilimagmaro | armes |
| 8 | Port Ehcep | armes/armures | 28 | Kilimagmaro | armures |
| 9 | Port Ehcep | objets | 29 | Kilimagmaro | objets |
| 10 | Rivesall | objets (general) | 30 | Côte de l'Exil | chronocrystal, **outside any town** |
| 11 | Pontaudy | armes/armures | 34 | **unknown** | 6 items, 500 % |
| 12 | Pontaudy | objets, **500 %** | | | |
| 13-16 | Finefleur | armes, armures 1, armures 2, objets | | | |
| 33 | Pontaudy | **secret shop** | | | |

**id=34, the shop no census lists** — six ordinary items at 500 % — is almost certainly
**Pontaudy's item shop in an earlier state**. Three clues, all measured: its six items are a
**strict subset** of the twelve that id=12 (Pontaudy, objets) sells; it carries the **same
500 %**, and 500 % appears nowhere else in the game; and it sits in the **second group**
(p0 = `0x20 | 2`), the group that otherwise holds shop variants — Ablithia's two post-game
stalls, the twin of Ablithia's armourer, Pontaudy's secret shop. A second, independent
source agrees on the town: [thonky's shop list](https://www.thonky.com/dragon-quest-ix/list-of-shops)
gives the Dourbridge (= Pontaudy) item shop a medicinal herb at **40 gold**, which is exactly
8 × 500 %. To confirm it is the same NPC at two moments still needs a look in play.

**id=1 versus id=36** cannot be told apart, since their stock is identical to the item; same
for **id=26 versus id=29**, assigned to Dracocardis and Kilimagmaro by file order alone.

### 83.6 Prices: sell price in the item record, buy price in the next field

The item record of §79.8 carries **two** money fields, not one:

| offset | type | meaning |
|---|---|---|
| `+0x16` | u16 | the **sell price** — what the shop pays the player |
| `+0x18` | i16 | the **buy price**, literally when positive, by code when negative |

The codes, read off the data and then confirmed against the census:

| `+0x18` | buy price | count in the catalogue |
|---|---|---|
| ≥ 0 | that value (bamboo lance 85, halberd 11,200) | 332 |
| −1 | 2 × sell | 731 |
| −2 | 2 × sell + 1 (chimaera wing 12 → 25) | 4 |
| −3 | 2 × sell − 1 (leather hat 33 → 65) | 2 |
| −4 | 10 × sell (copper sword 15 → 150 — the starting gear) | 108 |

and the shop's own percentage (§83.3) multiplies the result, so Pontaudy's item shop asks
5 × 8 = 40 for a medicinal herb.

**Witness.** Of the census's prices, 511 can be tied to a catalogue item; the rule reproduces
**511 of 511, with no discrepancy**. Two independent confirmations of the sell column on top of
that: the DQ9 wiki gives the copper sword at 150 to buy and 15 to sell, which is exactly a −4
record, and the chronocrystal's 25,000 doubles to the 50,000 the census quotes.

This also kills the earlier, tempting reading that the column at `+0x16` was the buy price: it
never is. A randomizer that moves an item from one slot to another moves both its prices with
it, since both live on the item and neither lives on the slot.

### 83.7 Rewriting without moving anything

A slot is a `u32` already present in the file, so a shop randomizer overwrites 559 words
in place and **no file size changes** — the same property as §79.9, which is what keeps
the ROM layout and the savestates valid. `scripts/boutiques.py:lire` already returns each
slot's byte offset for that purpose.

### 83.9 Two ceilings, both measured in play (18 September)

Version 1.3 was first built with prices up to 655,350 and with the nine item archives
rewritten. Both choices were wrong, and the player's savestates said so in one pass.

**The buy price is a u16: past 65,535 the shop displays `0`.** On his savestate of
Ablithia's first weapon shop, the game shows `Anarc 33 300` (a −4 record, 10 × 3,330)
but `0` for the Assommoir, which our data prices at 200,000, and `0` again for the
cherub bow (300,000) and for the two 5-star items we had pushed to 655,350. The shop's
own percentage is applied **afterwards and in a wider type**: the same build displays
270,000 without trouble in a 500 % stall. So a base price must stay **≤ 65,535**, and
Dourbridge can display up to **327,675**. The i16 of the field (§83.6) was never the
binding limit — this is.

**The game decompresses in place, so a stream may not be larger than its output.**
`gp2_ecrire.py` first emitted literal-only LZSS: a valid stream, 12.5 % *larger* than
the data. Every shop looked right, but opening the item list aborted —
`ARM9: data abort (02003F18)`, reproduced from the player's savestate by
`scripts/lua/boutique_ecran.lua`. Writing a real LZSS compressor (matches of 3 to 18
bytes, window 4,096) fixed it: the nine archives now grow by **2,460 bytes in total**
instead of 254 KB, and the item list opens — checked on a cold boot with
`scripts/lua/reprise_menu.lua`, list rendered, no abort.

Both facts are cheap to forget and expensive to rediscover: a stream that decompresses
correctly on the PC can still kill the game, and a price that our tables accept can
still display as zero.

### 83.10 The table the game actually reads is `itemdt.gp2`, not `itemdt_<c>.gp2`

Prices written into the nine per-category archives changed nothing in play: every
newly priced item still showed **"Achat impossible"** and `0`, while items carrying the
vanilla `-1` code (lamb's wool, 90 → 180) bought and sold normally.

The answer came from RAM. `scripts/lua/prix_ram.lua`, run on the player's savestate
inside a grocery, scans main RAM for the item's record — identifier, then sell price,
then buy field. The slime drop's record sat at `0x00392198` with **sell 14, buy 0**,
while our patched file said 28. So the runtime table is not built from the files we
had rewritten.

It comes from **`data/prm/itemdt.gp2`**: five members (one per language) holding the
same 32-byte record for all 1,178 items. The slime drop is there at offset 40,324 of
`itemdt_fr.nat` as `(22087, 14, 0)`, and lamb's wool at 40,836 as `(22103, 90, -1)` —
exactly what RAM shows. `patch_prix.py` now writes the ten archives: this one, which
the shop reads, and the nine per-category ones so the catalogue stays consistent with
it. Each record is located by the signature *(identifier, vanilla sell price, 0)* and
the patch refuses to run unless it matches exactly once per member.

**And only the `-1` code is written, never an explicit price.** The three items in the
whole game whose field holds a positive value are weapons (bamboo lance 85, halberd
11,200, lightning conductor 15,800); no ordinary item has one, and every ordinary item
we had given an explicit price read as "Achat impossible". Rather than settle why, the
patcher sticks to the mechanism the game demonstrably uses everywhere: *buy = 2 × sell*.
When an item has no sell price, that is what gets written — half the intended price.

Consequence for the pool: an item whose sell price exceeds 32,767 cannot be priced at
all (twice it would pass the u16 ceiling of §83.9), so **fourteen 5-star items stay out
of the stalls** rather than have their resale value cut.

### 83.11 The price class: a three-bit field, and 2 is not always the right value

Giving an unpriced item a price is not enough: the shop still prints **"Invendable"** in
place of its price. The gate is a **three-bit field at bits 13-15 of the flag word at
`+0x04`** of the item record.

```
(flags >> 13) & 7 == 0   this item can never be listed in a shop
(flags >> 13) & 7 == 2   the value carried by all 330 items vanilla sells
```

Two independent confirmations, one measured and one experimental:

- **Measured.** Every one of the 330 articles vanilla shops sell carries the value **2**,
  with no exception. Every item the game refused in our own shops — the Erdrick set, the
  26 skill books, both debug stones — carries **0**. And the 50 items with no sell price
  at all carry 0 as well, which is why "has a vanilla sell price" looked like the rule for
  a while: it was a consequence, not the cause.
- **Experimental.** `scripts/lua/essai_drapeau.lua`, run on the player's savestate with
  the buy list open, sets those bits on Erdrick's helmet **in RAM only**, leaves the list
  and re-enters it to force a rebuild. The article changes from "Invendable" to
  **900,000 po**. Nothing else was touched.

**But the field is a class, not a yes/no**, and a second in-game test paid for that
lesson. Writing 2 everywhere — the value of the 330 vanilla articles — made 101 items that
carried **5** go back to "Invendable" as soon as their price passed what class 2 accepts.
In a 2000 % stall: `robe de Celestelle`, class 5 untouched, displays 530,000; `armure
victorieuse`, class 5 overwritten with 2, refuses at 800,000. The RAM experiment above had
set class **5**, which is why it worked.

What the three values mean, as far as measured:

| class | what it does |
|---|---|
| 0 | the article can never be listed |
| 2 | the 330 vanilla articles, none above 50,000 gold; refuses large amounts |
| 5 | carries large amounts — 530,000 measured in a shop, 2,621,400 in the RAM test |

`patch_prix.py` therefore **never touches a non-zero class** and writes **5** on the items
it prices that have none. `patch_boutiques.verifier` refuses to produce a ROM where a
class-2 article would display more than 65,535 gold, which is the conservative reading of
that ceiling until someone measures it exactly.

An earlier reading of this section blamed a missing vanilla sell price and concluded the
gate could not be found. That was wrong, and it is kept here as the wrong turn it was: the
bit scan that missed it compared "has a price" against "has none", and the flag does not
separate those two sets — it separates *sellable* from *not sellable*, which is a
different question.

### 83.12 How high a price can go: the ×10 code breaks long before the format does

The ceiling is **not** on the magnitude of a price. It is on the `-4` code.

What the player's captures showed at first looked like a u16 boundary: base prices of
33,300 and 54,000 display, 200,000 and 300,000 display **0**. But every one of the broken
ones came through **code −4** (ten times the sell price), and every one of the good ones
through **−1**. Testing the `-1` path directly settles it: `scripts/lua/essai_prix.lua`
pushes the hallowed helm's sell price to 65,535 in RAM, rebuilds the list, and the article
shows **2,621,400** in a 2000 % stall — a base of **131,070**, twice what we thought the
format allowed.

So, for the randomizer:

- **base price = 2 × sell price, up to 131,070**, written through code −1, and nothing has
  to be dropped for being too valuable;
- the **total** after the shop's percentage is not bounded in any way we have met: the
  player has confirmed 1,000,000 on screen, and this experiment 2,621,400;
- code **−4** is left alone. Vanilla only uses it on starter gear (ten times a sell price
  of 15 or so), and pushed high it renders as 0.

An earlier version of this section stated a 65,535 ceiling on the base price. That was the
wrong conclusion from the right observation, and the mistake is kept visible here: two
items that displayed 0 had been read as proof of a format limit, when they only proved
that one of the four price codes misbehaves.

