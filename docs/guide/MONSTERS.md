# How monsters are randomized

This guide explains, in plain terms, what the randomizer does to the monsters of
Dragon Quest IX (Europe, `YDQP`). It describes the current version.

## What you will see

- **Every field monster can be any of the game's 256 field monsters**, anywhere.
  A slime can walk around in the last area of the game, and a late-game monster in
  the first field.
- **Each monster that appears is drawn at random**, one by one, not a fixed set of
  species per area.
- **The monster on the map looks like the monster you fight.** Its model, size
  and way of moving are its own.
- **Bosses never appear as field monsters.** Story battles are unchanged unless
  you tick *Story bosses*, which swaps each boss for another boss.
- **Monsters keep their own stats, spells and drops.** A monster is the real
  monster, only moved somewhere else. What it drops is randomized separately, see
  [`LOOT.md`](LOOT.md).

There is **no difficulty balancing**: some areas become much harder or much
easier than in the original game. That is intended.

## Why it is harder than it sounds

On the field, the game only keeps **about ten monster models in memory at once**
for the area you are in. The original game prepares that small set when you enter
an area. To let any of the 256 monsters appear, the randomizer:

1. picks the species at the moment a monster appears, and picks again if that
   species is already on screen: you never meet two of the same at once;
2. loads its model on demand, and unloads a model that is no longer on screen;
3. gives the monster the size, hitbox and behaviour of its own species.

All of this is a patch of the game code, not only of its data. The technical
details, with their evidence, are in [`../research/`](../research/README.md).

## Known limits

- When many monsters are on screen and the model memory is full, a monster can
  still **borrow the model of another one** already loaded, until one of them
  leaves the screen.
- Versions 1.2.1 to 1.4 could fill that memory with copies of the same monster:
  few different monsters, wrong models, sometimes a freeze. This is fixed.
- Very large models are more likely to show visual glitches.
- Tested on emulator only (melonDS through BizHawk, and DeSmuME with the dynamic
  recompiler disabled), never on real hardware.

## Quest monsters

Quests that ask you to defeat a given monster still work: every one of the 256
field monsters can appear, so every quest target can be found. Quest items that
monsters drop only while a quest is active are handed out by the quest script,
which the randomizer does not touch.
