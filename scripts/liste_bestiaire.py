#!/usr/bin/env python3
"""La liste des 256 monstres tirables, pour que les testeurs cochent.

POURQUOI. `verif_bestiaire.py` prouve ce que le tirage a le DROIT de sortir, en
relisant le bitmap de la ROM. Il ne prouve pas ce qui apparait reellement a
l'ecran : entre le tirage et le symbole il y a le portier, l'emprunt de modele et
les emplacements de la carte. Cette verification-la ne peut venir que du jeu, donc
des testeurs -- d'ou une liste qu'ils puissent cocher.

LES DEUX NUMEROTATIONS. Le bestiaire du jeu numerote ses monstres de 1 a 256. La
table interne, elle, porte 288 identifiants pour ces 256 noms : 26 noms ont
plusieurs entrees (variantes de rang, versions d'antre). On liste donc par NOM, en
indiquant tous les identifiants internes qui le portent.

Les noms viennent de la ROM vanilla, pas d'un wiki : c'est la seule source qui ne
puisse pas se tromper sur l'orthographe du jeu.

Usage:
    python scripts/liste_bestiaire.py                 liste lisible (fr + en)
    python scripts/liste_bestiaire.py --json <sortie>  donnees pour un outil
    python scripts/liste_bestiaire.py --csv <sortie>   tableur
"""
import json
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import monnames
from monstres_nommes import MONSTRES
from rom_vanilla import chemin_vanilla


def sans_accents(s):
    """La console Windows est en cp1252 : on translittere pour l'affichage."""
    return "".join(c for c in unicodedata.normalize("NFD", str(s))
                   if unicodedata.category(c) != "Mn")


def construire(rom=None):
    """Rend la liste des 256 monstres : nom fr, nom en, identifiants internes."""
    # "ids" : RANGS d'enregistrement (numerotation de MONSTRES et des noms).
    # "identifiants" : ce que portent les acteurs et ce que tire le jeu -- c'est
    # celle-ci que les releves des sondes contiennent (ZER-16).
    from montable import ids_par_index
    rom = rom or chemin_vanilla()
    ident = ids_par_index(rom)
    tables = {lg: monnames.charger(rom, lg) for lg in ("fr", "en")}
    groupes = {}
    for i in sorted(MONSTRES):
        if i >= len(tables["fr"]):
            continue
        cle = tables["fr"][i]["nom"]
        g = groupes.setdefault(cle, {"fr": cle, "en": tables["en"][i]["nom"],
                                     "ids": [], "identifiants": [], "modeles": []})
        g["ids"].append(i)
        g["identifiants"].append(ident[i])
        m = tables["fr"][i].get("modele")
        if m and m not in g["modeles"]:
            g["modeles"].append(m)
    # ordre : par premier identifiant interne, qui suit l'ordre du bestiaire
    return sorted(groupes.values(), key=lambda g: g["ids"][0])


def main():
    liste = construire()
    args = sys.argv[1:]

    if "--json" in args:
        dest = args[args.index("--json") + 1]
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(liste, f, ensure_ascii=False, indent=1)
        print(f"ecrit : {dest}  ({len(liste)} monstres)")
        return

    if "--csv" in args:
        dest = args[args.index("--csv") + 1]
        with open(dest, "w", encoding="utf-8", newline="") as f:
            f.write("n,nom_fr,nom_en,identifiants_internes,vu\n")
            for n, g in enumerate(liste, 1):
                ids = " ".join(str(i) for i in g["ids"])
                f.write(f'{n},"{g["fr"]}","{g["en"]}","{ids}",\n')
        print(f"ecrit : {dest}  ({len(liste)} monstres)")
        return

    print(f"Les {len(liste)} monstres que le randomizer peut faire apparaitre.")
    print("Aucun boss n'est dans cette liste : s'il en apparait un, c'est un bug.")
    print()
    print(f"{'n':>4}  {'nom (fr)':<26} {'name (en)':<26} ids internes")
    print("-" * 92)
    for n, g in enumerate(liste, 1):
        ids = ",".join(str(i) for i in g["ids"])
        print(f"{n:>4}  {sans_accents(g['fr']):<26} "
              f"{sans_accents(g['en']):<26} {ids}")


if __name__ == "__main__":
    main()
