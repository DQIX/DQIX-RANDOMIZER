# Shops

Version 1.3 randomizes what the **37 shops of the game** sell. This page is the
player-facing summary — what changes, what does not, and why. The reverse engineering
behind it is in [`docs/research/11-shops.md`](../research/11-shops.md); the loot
randomizer has its own page, [`LOOT.md`](LOOT.md).

## What changes

Every shop in the game gets a new stock, drawn once when the ROM is built and **fixed for
the whole playthrough** — like the red chests. Two visits to the same shop show the same
list.

**1,082 items can appear**, against 330 in the original game.

## The rules

### Each slot keeps its family

A weapon shop sells weapons, an armourer sells armour and never a sword, a grocery keeps
its exact count of accessories, and the mixed stalls stay mixed in the same proportions.
The rule is per slot, not per shop, which is what preserves the balance of the stalls that
sell several families at once.

A shop never lists the same item twice, and a slot that was empty stays empty: the counts
of 18, 12, 6 and 1 article are those of the original game, and the menu shows six lines at
a time.

### Each stall is sorted

Ordinary items first, then weapons **by type** — daggers, hammers, swords, fans, axes,
whips, wands, spears, staves, boomerangs, claws, bows — then armour from head to foot, and
inside each group **by increasing price**. A list of eighteen articles drawn at random is
unreadable in play; this makes it a shop again.

### Rarity depends on the shop

- the 33 ordinary shops sell **0 to 3 stars**;
- Dourbridge's secret shop and the **two Stornway stalls that open after the final boss**
  sell **4 and 5 stars only**.

This holds in **every mode**, Total chaos included (since 1.5): *any item in any
shop* mixes shop families, never rarity.

### Prices

The game's own rule is kept: **an article costs twice its resale value**. Items the
original game never sells have no price at all, so the randomizer writes one — and also
sets the flag that allows an item to be listed, without which the shop prints
"Invendable" whatever the price says.

| | |
|---|---|
| ordinary item | twice its sell price |
| the 26 skill books | 100,000 gold |
| the nine seeds | 10,000 gold each |
| 5-star items | 131,070 gold, the format's ceiling |

A shop's own percentage multiplies all this. Dourbridge keeps the **500 %** of the
original game — the town of thieves sells dear, that is a trait of the place. Its secret
shop and Stornway's two post-game stalls are all set to **800 %**.

### What is never on sale

| | why |
|---|---|
| the 88 key items | a key in a shop can make the game unfinishable |
| the two debug stones | *"DEBUG: USE TO SECURE VICTORY"* and *"USE FOR A WIPE-OUT"* |
| the mini medal | it would make the collector's rewards farmable |
| the dragon warrior set | handed out by an event |
| the chronocrystal shop | left untouched, stock and price |

## What this costs

The item catalogue is rewritten, so nine data files change size and **savestates taken on
another build are no longer valid**. Your in-game save is not affected.

The two debug stones are also removed from chests, pots and monster drops, so a build made
after this version no longer reproduces the checksum of 1.2 or 1.2.1.

## Still to do

Balance. The draw is uniform over the whole catalogue, so an early-game stall can offer
things far above what the player can afford. Bounding rarity or price by story progress is
the obvious next step, and it has not been done.

## Prices follow the story

The 37 shops are stored in story order, and what the original game sells in
each of them climbs steadily: 240 gold in the first village, 840, 1,750, up to
31,500 at the end. The randomizer uses that curve as a ceiling -- a shop never
offers anything pricier than what the original game sells there.

Without it, the draw is uniform over the whole catalogue and the first shop of
the game offers items worth 32,500 gold: measured, and reported twice by
players. With it, that same shop tops out at 210.

The three rare shops are exempt: they are meant to be out of reach.

*ignore story prices* in the application turns this off and gives you the 1.3
behaviour.
