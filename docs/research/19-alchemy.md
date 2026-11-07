# 19. Alchemy: the Krak Pot recipes

## 102. `recipe.gp2`, decoded (ZER-52, 14 October 2026)

First step towards randomizing alchemy (ZER-53 will randomize the **ingredients**,
the player's choice). Static reading only, no patch. Reader: `scripts/recettes.py`
(read-only, no dependency; `--verifier` runs the checks below, `--langue fr` lists in
French).

### Where the recipes live

`data/bin/recipe.gp2` (58,124 bytes) is a GPC2 archive with five members compressed
with LZSS type 1, one per language: `recipe_de.bin`, `_en`, `_es`, `_fr`, `_it`,
41,392 bytes each once decompressed. The code that loads them is in **overlay 6**, the
Krak Pot (the community decomp calls overlay 6 "the alchemy pot"). The strings
`recipe.gp2` and `recipe_<LG>.bin` are at `0x021602A0` and are loaded at `0x0215A77C`;
the constant `0x1D7` (471) is at `0x0215B0F8`.

### Format: the generic Nitro script again

The member is the same generic script as the loot (`treasure.nsarc`, §79) and the
shops (`shopdata1.bin`, §83), and `treasure.lire_script` reads it unchanged:

| what | value |
|---|---|
| header (16 bytes) | 471 instructions, data section at `0xA1B0` (= file size: no strings) |
| opcode `0x66` | one integer: **470**, the number of recipes |
| opcode `0x67` × 470 | **one recipe**, 20 integer parameters (descriptor `67 00 14 55 55 55 55 55`, then 80 bytes: 88 bytes per recipe) |
| `0xFFFF` | end |

Fields of one recipe (opcode `0x67`):

| param | meaning | evidence |
|---|---|---|
| p0 | recipe id, 1–471, **359 does not exist** | equals `alchemyIdx + 1` in the community save editor (`DQIX/editor`, `src/game/data.js`): 470/470 match. The editor has one typo: it also gives `alchemyIdx: 1` to the debug item BLARNEY STONE (22126) |
| p1 | **item produced**: the `itemdt` item id used by `objets.py`, `patch_loot`, `patch_boutiques` | all 470 are in the 1,178-item catalogue |
| p2, p3 | ingredient 1: item, quantity | |
| p4, p5 | ingredient 2: item, quantity (`0, 0` if none) | |
| p6, p7 | ingredient 3: item, quantity (`0, 0` if none) | slots are filled from the start; never an empty slot followed by a full one |
| p8–p12 | `(0, 100, 100, 0, 0)` everywhere except the 22 great-success variants (see p16): `(1..7, 10 or 20, 40 or 50, 300, 999 or 700)` | **HYPOTHESIS**: the great-success odds. The community function list names a "lottery for the great alchemical success" on the BT generator |
| p13 | flag 0/1 (339 recipes at 1) | **UNKNOWN**. Not explained by the recipe books (209/78/130/53), rarity, category, number of ingredients, or whether the product is itself an ingredient |
| p14 | product category: 0 weapon, 1 shield, 2 body, 3 legs, 4 head, 5 arms, 6 feet, 7 accessory, 8 item | 470/470 match the `itemdt_<c>` archive the product lives in |
| p15 | sub-category (the Alchenomicon section): 0–11 weapon types, 12 shields, 13–15 body, 16 legs, 18–19 head, 20–21 arms, 22–23 feet, 24 accessories, 25 remedies, 28 materials | constant within each weapon type |
| p16 | on 22 base recipes: the id of the recipe of their **great-success variant**; -1 elsewhere | |
| p17 | on the variant: the id of its base recipe; -1 elsewhere | links always go both ways |
| p18 | display order, 1–471 | Celestria's gown (id 471, the last id) sits at order 330 among the body armour |
| p19 | alphabetical sort key | **the only field that differs between the five languages** (bytes `+0x54/+0x55` of the record, nothing else); sorting by it gives the English names in alphabetical order (1 inversion, against 223 with the wrong alignment) |

**Known recipes checked (CONFIRMED).** Medicinal herb ×2 → strong medicine (recipe 440);
steel broadsword = iron broadsword + iron ore + lava lump; strong medicine ×2 → special
medicine; plus 470/470 products matching the save editor's independent table.

### What the data says about the recipe set

- 470 recipes: 331 with three ingredients, 135 with two, 4 with one.
- Quantities 1 to 9 (888 × 1, 223 × 3, 108 × 2, then 5, 6, 4, 9, 7).
- 488 distinct ingredient items, from every category (159 weapons, 90 common items…).
- **No key item** (`objets.objets_importants`) and nothing from `objets.HORS_TIRAGE`,
  neither as ingredient nor as product. No item is produced by two recipes.
- **The 22 great-success pairs** are the ultimate legendary equipment: supernova sword →
  hypernova sword, split-pot poker → red-hot poker, … sentient sandals. Base and variant
  carry **identical ingredients**; the pot presumably picks the variant by a draw
  (**HYPOTHESIS**). These are
  the only recipes sharing an ingredient set: apart from them, no two recipes use the
  same set, and none use the same items in different quantities.
- Some recipes loop: the "reset stone" recipes turn the top of a legendary chain back
  into its bottom (supernova sword + reset stone → stardust sword).

### Recipe books carry product names only

Bookshelves are `data/scenario/htana<X>.gp2` (`hondana`, bookshelf), seven files (C, D,
H, M, R, S, X), five languages each. A recipe book is plain text:
"`<LEADER>` finds recipes for a steel shield, a steel helmet and full plate armour." —
105 books, naming 287 recipes, **by product name only**. Whatever the Alchenomicon shows as
ingredients must come from `recipe.gp2` (**HYPOTHESIS**, to watch in play with ZER-53's
first ROM).

What will lie once ingredients are randomized:

- flavour lines in the same books ("Iron ore and lava lumps are essential for
  steel-weapon making", `htanaX`; "start stockpiling toad oil", `htanaC`);
- quest texts in `questmsg.gp2` and the town scripts that spell out an ingredient list
  (the sunstone request: "mirrorstones, lucida shards and Hephaestus' flames"; the
  "potato-roasting stone" rhyme in `C01*0.gp2`).

### For ZER-53

- Rewriting in place is enough: every ingredient is a u32 already present
  (`lire()` returns the offset of each parameter), the five language members must get
  the same values, and the archive must be recompressed (`gp2_ecrire.py`, LZSS
  shorter than its output, see the guardrails).
- Keep each great-success pair on the **same** ingredient set, and keep the sets unique
  across the other recipes (otherwise one input would match two recipes; which one the
  pot picks is not measured).
- Unknown before playing: whether the pot matches ingredients regardless of order, and
  whether a recipe that has not been learned can be made blind.

### 102.1 The ingredient randomizer (ZER-53, 14 October 2026)

`scripts/patch_alchimie.py`, option `--alchimie` (off by default, outside the
presets and `--chaos-total` until checked in play). Player's choices: draw from the
whole item pool (`objets.pool`: 1,082 items, no key item, nothing from
`HORS_TIRAGE`), keep every vanilla quantity. Each recipe gets as many ingredients as in
vanilla, three different items, never its own product; the variant of a great-success
pair copies its base, and neither product enters the pair's recipe; sets stay unique.
The draw has its own generator (`random.Random("alchimie:<seed>")`), so ticking the
option changes nothing else in the ROM: `diff_roms.py` between the same build with and
without it shows `data/bin/recipe.gp2` alone (58,124 → 64,136 bytes for seed 42, the
compressor being a little less tight than the game's), monster machinery identical.
`verifier()` compares with vanilla: only p2/p4/p6 move. Matrix: essai
"alchimie : ingredients tires", control `alchimie`.

**Checked in play (CONFIRMED, player, 14 October 2026, v17e):** the vanilla input for
strong medicine (medicinal herb ×2) no longer works, the new one (2 × an equipment piece)
does, and an unlearned recipe can be made blind with its new ingredients. The game reads
the ingredients from `recipe.gp2` and nothing else.

### 102.2 Bookshelf scripts and the bookshelf randomizer (ZER-105, 27 October 2026)

**Format (measured).** Each `htana<X>_<lg>.bin` is a Nitro script
(`treasure.lire_script`); one bookshelf is one opcode `0x66`:

| param | type | meaning |
|---|---|---|
| p0 | int | shelf id (5704, 5902, 6001...) |
| p1–p3 | int | p1 shelf index in the room; p2 = 1 if the shelf teaches; **p3 = book number**, the "read" flag (see below) |
| p4 | string | "There don't seem to be any books of particular interest." (shared, offset 27) |
| p5 | string | the book: title page, a flavour page (often an ingredient hint), then pages of three product names, each ending with `<SE_RECIPE>` |
| p6 | string | the same title and flavour, then "`<LEADER>` already knows the recipes in this book." |
| p7… | int | **the recipes learned**: `recipe.gp2` ids (`recettes.py` `id`) |

String parameters are offsets into the script's data area; the text is ASCII with tags
(`<1>` apostrophe, `<'e>` é, `<PAGE>`, `<Cap>`, `<LEADER>`). The ids are identical in the
five languages. 58 shelves teach something: 105 books, 345 slots, 327 distinct recipes
(18 are in two books). Checked: `htanaS` first book = recipes 204, 206, 318 (ogre shield,
big boss shield, mythril helm), as its text says.

**The randomizer** (`scripts/patch_bibliotheques.py`, `--alchimie-bibliotheques`, off
by default, independent of `--alchimie`): 345 recipes drawn without replacement from the
448 base recipes (great-success variants excluded), same draw in the five languages,
each book keeps its count. p5 and p6 are rewritten **in place**, shorter: title page,
then the drawn products by name, three per page, each page ending with `<SE_RECIPE>`
("`<LEADER>` finds these recipes`<:>` A`<,>` B`<,>` C."; names from `itemname` with
their tags, German inflection marks `[gs]` removed; `<:>` is the game's colon). The hint
page goes. A message that would not fit, or that two shelves with different draws
share, keeps a generic line ("`<LEADER>` learns the recipes in this book."): 4 of 54
in every language. The rest of the old string is zeroed. No member changes size.
Own generator (`random.Random("bibliotheques:<seed>")`). `verifier()` and the matrix
essai "bibliotheques" check it. **Not measured yet**: whether the game picks p5 or p6
from the p3 flag or from the recipes already known (a read shelf on an advanced save
might not teach its new recipes).

**The "already read" flag (read in the code, measured, 29 October 2026).** The shelf
handler of overlay 17 (state 5, `0x021AC7FC`) first checks game flag `0x777`, then, if
the shelf teaches (node `+0x14` = 1), game flag **`0x114C + p3`** (node `+0x15`). Flag
set: the p6 text, nothing learned. Flag clear: the recipes are learned (`0x020AC2E4`,
node `+0x16` = count) and the flag is set (`0x0206DF7C`). Game flags are a bit field
at the game object `0x02108844` + `0x8C` (byte `n >> 3`, bit `n & 7`; getter
`0x0206DFC0`), i.e. **+11724 in each 32 KB save slot** (found by matching RAM and
save). Ablithia's book (p3 = 2): flag `0x114E`, RAM byte `0x02108AF9` bit 6, save
`+12277` bit 6. Bench (`scripts/lua/etagere_drapeau.lua`, the player's Ablithia
savestate): that bit cleared and the recipe list emptied, the shelf teaches its 3
recipes; bit 5 cleared instead (control), nothing. The recipes already known play no
part. So **on a save where a book was read, the randomized shelf teaches nothing new**;
on a new game every shelf works. The 58 teaching shelves use 54 book numbers (1–55,
not 8); the player's late-game save had 53 of them set.
