#!/usr/bin/env python3
"""Met en tableau les lots de monstres releves par scripts/lua/lots.lua.

Le releve brut ne porte que des identifiants ; on y ajoute les noms, et on
marque d'un signe les especes qui SURVIVENT d'un lot au suivant -- ce sont les
monstres encore vivants a l'ecran, que la rotation doit conserver sous peine de
liberer leur modele sous eux.
"""
import sys

noms = {}
for ligne in open("work/tailles_modeles.txt", encoding="utf-8"):
    if ligne.startswith("#"):
        continue
    c = ligne.rstrip("\n").split("\t")
    noms[int(c[0])] = c[3]


# La console Windows n'est pas en UTF-8 : on translittere pour l'affichage.
ACCENTS = str.maketrans("aaaeeeeiioouuuc", "aaaeeeeiioouuuc")
TRANS = {"e": "eeee", "a": "aa", "i": "ii", "o": "o", "u": "uu", "c": "c"}


def sans_accent(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def nom(i):
    return sans_accent(noms.get(i, f"?{i}"))


precedent = set()
for ligne in open(sys.argv[1], encoding="utf-8"):
    if ligne.startswith("FIN"):
        break
    n, image, liste, mods = ligne.rstrip("\n").split("\t")
    dem = [int(x) for x in liste.split(",") if x]
    charges = [int(x) for x in mods.split(",") if x]
    garde = [e for e in charges if e in precedent]
    print(f"\n  ROTATION {n}  (image {image})   "
          f"{len(charges)} modeles charges sur {len(dem)} demandes"
          + (f"   dont {len(garde)} conserve(s)" if garde else ""))
    print("  " + "-" * 74)
    for i in range(0, len(charges), 2):
        paire = []
        for e in charges[i:i + 2]:
            marque = "=" if e in precedent else " "
            paire.append(f"  {marque} {e:3d}  {nom(e):<28s}")
        print("  " + "".join(paire))
    perdus = [e for e in precedent if e not in charges]
    if perdus:
        print(f"    remplaces : " + ", ".join(sorted(nom(e) for e in perdus)))
    precedent = set(charges)
print("\n  = espece conservee du lot precedent (monstre encore vivant a l'ecran)")
