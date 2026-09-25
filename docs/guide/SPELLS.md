# Spells and abilities

*What the randomizer does to what your characters can cast and learn.*

## Spells learned by levelling

Nine of the twelve vocations learn spells as they level up. Warriors, Martial
Artists and Gladiators learn none, and the randomizer leaves them that way --
giving them spells would mean growing the game's table and changing the layout
of the ROM.

The game stores 107 (vocation, spell, level) entries. The randomizer rewrites
the **spell** of each one and touches nothing else:

* a Priest still learns seventeen spells, at the same seventeen levels;
* no vocation ever learns the same spell twice;
* the draw is a shuffled deck, so all 61 spells of the game land somewhere.

**Balanced** keeps the power curve. The game's own ordering is the scale: the
median level at which the original game teaches a spell. A vocation therefore
still gets cheap spells early and the heavy ones late -- but not the same ones.
A Priest might open with Zam instead of Heal, and close on Kaboomle instead of
Omniheal.

**Total chaos** drops the ordering. Omniheal at level 1 is possible.

Healing is not protected. A party can end up with no healer, which is part of
the point -- items and the Zoom back to an inn still work.

## Skill trees

Every vocation spends skill points in skill trees: the weapon trees (swords,
axes, whips, bows...) plus its own vocation tree. The game has **26 trees of
11 milestones**, 286 in all. A milestone gives either an ability or a bonus
(Attack +10, critical rate up, a natural stat increase, absolute mastery).

The randomizer redeals **what each milestone gives**, abilities and bonuses
alike: a milestone that gave an ability can give a bonus, and the other way
round. The skill-point cost of each milestone stays where it was, and the
name shown in the menus follows what the milestone really gives.

**Balanced** shuffles milestones **inside** each tree. A weapon technique only
works with that weapon in hand, so a sword tree keeps granting sword
techniques. What changes is which ability or bonus sits behind which cost.

**Total chaos** shuffles across all 26 trees, within bands of similar cost. A
sword technique can then be learned in the whip tree -- you will learn it, but
you will need a sword to use it. Bonuses that name the tree's weapon ("Attack
+10 with") stay in weapon trees, where the game can show the weapon icon.

Six milestones of the original game have no name and are never shown; they
are left in place.

## Vocations

Vocation availability is **not** randomized. Six vocations are unlocked by
quests in the original game, and that gate lives in the game's code and in your
save file, not in the data the randomizer rewrites.
