#!/usr/bin/env python3
"""Genere la documentation publique du loot (en anglais) a partir d'une ROM.

Ecrit dans <dossier> :
  containers_by_rank.md   chaque coffre bleu et chaque pot/tonneau/placard,
                          range par rang, avec le nom de la zone en jeu ;
                          plus la liste des coffres rouges
  drop_rates.md           la chance de drop de chaque monstre de terrain
  rank_tables.md          ce que contient chaque rang : pourcentages d'objet,
                          d'or, d'embuscade et de vide, et etoiles admises

Les rangs jumeaux 6, 7, 8 des coffres bleus sont affiches 3b, 4b, 5b.

Usage :
  python scripts/doc_loot.py <rom.nds> docs/guide/loot
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ndspy.rom
import objets
import rarete
import treasure as T
from monnames import charger as noms_monstres
from monstres_nommes import MONSTRES
from zones import noms_zones

CONTENEUR = {1: "pot", 2: "barrel", 3: "cupboard"}
CHANCE = {0: "always", 1: "1/8", 2: "1/16", 3: "1/32", 4: "1/64", 5: "1/128",
          6: "1/256", 7: "never"}
ETIQ_BLEU = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "3b", 7: "4b", 8: "5b"}


def etoiles_txt(ens):
    ens = sorted(ens)
    if len(ens) == 1:
        return "%d★" % ens[0]
    return "%d-%d★" % (ens[0], ens[-1])


def main(chemin, dossier):
    os.makedirs(dossier, exist_ok=True)
    rom = ndspy.rom.NintendoDSRom.fromFile(chemin)
    zen = noms_zones(rom, "en")
    nen = objets.noms(rom, "en")
    arc = bytes(rom.files[rom.filenames.idOf("data/scenario/treasure.nsarc")])
    membres = T.membres_narc(arc)

    bleus = collections.defaultdict(list)
    pots = collections.defaultdict(list)
    rouges = []
    for zone, (deb, _f) in sorted(membres.items()):
        if zone in T.TABLES:
            continue
        code = zone[:-4]
        for c in T.conteneurs(arc, deb):
            lieu = (zen.get(code, "") or "?", code, c["unique"])
            if c["conteneur"] == 4:
                bleus[c["item"]].append(lieu)
            elif c["conteneur"] in CONTENEUR:
                pots[c["item"]].append(lieu + (CONTENEUR[c["conteneur"]],))
            elif c["conteneur"] == 0:
                if c["loot"] == T.TYPE_OBJET:
                    contenu = "fixed item"
                    if c["item"] in objets.objets_importants(rom):
                        contenu = "%s (kept: key item)" % nen.get(c["item"], "?")
                elif c["loot"] == T.TYPE_OR:
                    contenu = "%d gold (kept)" % c["item"]
                else:
                    contenu = "empty (kept)"
                rouges.append(lieu + (contenu,))

    def tableau(entetes, lignes):
        out = ["| " + " | ".join(entetes) + " |",
               "|" + "|".join("---" for _ in entetes) + "|"]
        out += ["| " + " | ".join(str(x) for x in l) + " |" for l in lignes]
        return "\n".join(out) + "\n"

    # ---------------- containers_by_rank.md ----------------
    L = ["# Containers by rank\n",
         "Generated from `%s` by `scripts/doc_loot.py`. The rank of a "
         "container is fixed by the game data of its room and does **not** "
         "depend on the seed.\n" % os.path.basename(chemin),
         "Each container is listed as *in-game location* (`map file`, unique "
         "ID). The same unique ID in two rooms is the same container seen at "
         "two points of the story.\n",
         "## Blue chests\n",
         "Ranks 3b, 4b and 5b are **twins** of ranks 3, 4 and 5: identical "
         "odds, a different item list (see [`../LOOT.md`](../LOOT.md)). The game stores them as "
         "ranks 6, 7 and 8.\n"]
    for rang in (1, 2, 3, 6, 4, 7, 5, 8):
        lot = sorted(bleus.get(rang, []))
        L.append("### Rank %s — %s — %d chest(s)\n" % (
            ETIQ_BLEU[rang], etoiles_txt(rarete.BLEU[rang]), len(lot)))
        L.append(tableau(["Location", "Map file", "Unique ID"],
                         [(z, "`%s`" % c, u) for z, c, u in lot]))
    L.append("## Pots, barrels and cupboards\n")
    L.append("Rank 0 containers have no loot table and are always empty.\n")
    lignes_ttt = [o for _o, o in T.outcomes(arc, membres[T.TABLE_POTS][0])]
    sans_objet = ({o["rang"] for o in lignes_ttt}
                  - {o["rang"] for o in lignes_ttt if o["loot"] == T.TYPE_OBJET})
    for rang in sorted(pots):
        lot = sorted(pots[rang])
        if not rang:
            titre = "### Rank 0 — always empty — %d container(s)\n" % len(lot)
        elif rang in sans_objet:
            titre = "### Rank %d — gold only — %d container(s)\n" % (rang, len(lot))
        else:
            titre = ("### Rank %d — %s — %d container(s)\n"
                     % (rang, etoiles_txt(rarete.pot(rang)), len(lot)))
        L.append(titre)
        L.append(tableau(["Location", "Map file", "Unique ID", "Type"],
                         [(z, "`%s`" % c, u, t) for z, c, u, t in lot]))
    L.append("## Red chests\n")
    L.append("Red chests are not ranked: each one holds a fixed item, rolled "
             "once when the ROM is built, from every rarity (0-5★). Gold, empty "
             "and key-item chests keep their vanilla content.\n")
    L.append(tableau(["Location", "Map file", "Unique ID", "Content"],
                     [(z, "`%s`" % c, u, t) for z, c, u, t in sorted(rouges)]))
    open(os.path.join(dossier, "containers_by_rank.md"), "w",
         encoding="utf-8", newline="\n").write("\n".join(L))

    # ---------------- rank_tables.md ----------------
    L = ["# What each rank contains\n",
         "Generated from `%s`. Percentages are per opening; what is left to "
         "100 %% is **nothing**. They are the vanilla odds: the randomizer only "
         "replaces which items fill the *item* share, and splits that share "
         "into more lines so that more different items can come out.\n"
         % os.path.basename(chemin)]
    for table, titre, etiq, regle in (
            (T.TABLE_COFFRES_BLEUS, "Blue chests (`randTBox.bin`)",
             lambda r: ETIQ_BLEU.get(r, str(r)), lambda r: rarete.BLEU[r]),
            (T.TABLE_POTS, "Pots, barrels, cupboards (`randTTT.bin`)",
             str, rarete.pot)):
        rangs = collections.OrderedDict()
        for _o, o in T.outcomes(arc, membres[table][0]):
            r = rangs.setdefault(o["rang"], dict(obj=0, n=0, gold=[], amb=[]))
            if o["loot"] == T.TYPE_OBJET:
                r["obj"] += o["pct"]
                r["n"] += 1
            elif o["loot"] == T.TYPE_OR:
                r["gold"].append("%d gold %d%%" % (o["id"], o["pct"]))
            else:
                r["amb"].append("%d%%" % o["pct"])
        lignes = []
        if table == T.TABLE_COFFRES_BLEUS:
            ordre = sorted(rangs, key=lambda r: (JUM.get(r, r), r))
        else:
            ordre = sorted(rangs)
        for r in ordre:
            v = rangs[r]
            vide = 100 - v["obj"] - sum(int(g.split()[-1][:-1]) for g in v["gold"]) \
                - sum(int(a[:-1]) for a in v["amb"])
            lignes.append((etiq(r), "%d%% (%d lines)" % (v["obj"], v["n"]),
                           ", ".join(v["gold"]) or "—", ", ".join(v["amb"]) or "—",
                           "%d%%" % vide,
                           etoiles_txt(regle(r)) if v["n"] else "— (gold only)"))
        L.append("## %s\n" % titre)
        L.append(tableau(["Rank", "Item", "Gold", "Ambush", "Nothing", "Rarity"],
                         lignes))
    open(os.path.join(dossier, "rank_tables.md"), "w",
         encoding="utf-8", newline="\n").write("\n".join(L))

    # ---------------- drop_rates.md ----------------
    mon = bytes(rom.files[rom.filenames.idOf("data/prm/mon_btldata.nat")])
    mons = noms_monstres(chemin, "en")
    vus, lignes = set(), []
    for k in sorted(MONSTRES):
        nom = objets.nettoyer(mons[k]["nom"] or "")
        if not nom or nom in vus:
            continue
        vus.add(nom)
        r = mon[4 + k * 132:]
        lignes.append((nom, CHANCE[r[2]], etoiles_txt(rarete.DROP[r[2]]),
                       CHANCE[r[3]], etoiles_txt(rarete.DROP[r[3]])))
    L = ["# Monster drop rates\n",
         "Generated from `%s`. Every field monster has a common and a rare "
         "drop. When a monster is defeated the game rolls the **rare** drop "
         "first; only if it fails does it roll the common one. The rates are "
         "vanilla; the randomizer changes which items drop, following the "
         "rarity column.\n" % os.path.basename(chemin),
         tableau(["Monster", "Common drop", "Common rarity", "Rare drop",
                  "Rare rarity"], sorted(lignes))]
    open(os.path.join(dossier, "drop_rates.md"), "w",
         encoding="utf-8", newline="\n").write("\n".join(L))
    print("ecrit : containers_by_rank.md, rank_tables.md, drop_rates.md dans " + dossier)


JUM = {6: 3.5, 7: 4.5, 8: 5.5}

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
