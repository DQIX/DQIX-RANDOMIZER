#!/usr/bin/env python3
"""Randomiser les INGREDIENTS des recettes d'alchimie (ZER-53, 1.7).

DECISION DU JOUEUR (13 et 14/10/2026) : on garde ce que produit chaque
recette et on tire ses ingredients ; le tirage se fait dans TOUT le pool
d'objets (`objets.pool` : le catalogue moins les objets importants et
`objets.HORS_TIRAGE`), et chaque emplacement GARDE SA QUANTITE vanilla.

Le format est dans `recettes.py` et research §102. Ce qu'on reecrit : les
parametres p2, p4 et p6 (l'objet de chaque ingredient), EN PLACE, dans les
cinq membres `recipe_<lg>.bin` -- les memes valeurs partout, puisque seule la
cle de tri change d'une langue a l'autre. L'archive est recompressee
(`gp2_ecrire.reecrire`, vrai LZSS) : sa taille change, donc la disposition
de la ROM aussi (les savestates d'une autre construction ne valent plus ; la
sauvegarde de partie, si).

REGLES DU TIRAGE :
  - une recette a autant d'ingredients qu'en vanilla, chacun avec sa
    quantite vanilla ;
  - trois objets DIFFERENTS par recette, et jamais l'objet qu'elle produit ;
  - les 22 paires de grand succes (epee supernova / hypernova...) gardent
    les MEMES ingredients : on tire pour la base, la variante recopie ; aucun
    des deux produits n'entre dans la recette ;
  - deux recettes n'ont jamais le meme jeu d'ingredients (sinon une meme
    entree dans la Marmite viserait deux recettes, ce qu'on ne sait pas
    trancher), paires exceptees.

Le tirage a SON PROPRE generateur, derive de la graine : cocher ou non
l'alchimie ne change rien au reste de la ROM, et l'alchimie ne depend pas des
autres options.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gp2_ecrire
import objets
import recettes

ESSAIS = 1000


def generateur(seed):
    """Le generateur de l'alchimie, independant de celui du reste."""
    return random.Random("alchimie:%d" % seed)


def _ecrire(rom, tirage):
    """Pose {id de recette: [objets]} dans les cinq langues."""
    fid = rom.filenames.idOf(recettes.CHEMIN)
    clairs = {}
    for lg in recettes.LANGUES:
        d = bytearray(recettes.fichier(rom, lg))
        for r in recettes.lire(rom, lg):
            neufs = tirage[r["id"]]
            if len(neufs) != len(r["ingredients"]):
                raise AssertionError("recette %d : %d ingredients au lieu de %d"
                                     % (r["id"], len(neufs),
                                        len(r["ingredients"])))
            for k, o in enumerate(neufs):
                off = r["offsets"][2 + 2 * k]
                d[off:off + 4] = o.to_bytes(4, "little")
        clairs["recipe_%s.bin" % lg] = bytes(d)
    rom.files[fid] = gp2_ecrire.reecrire(bytes(rom.files[fid]), clairs)


def patcher(rom, seed, langue="en", journal=None):
    """Tire et pose les ingredients. Rend un dictionnaire de comptes."""
    def note(ligne=""):
        if journal is not None:
            journal.write(ligne + "\n")

    rng = generateur(seed)
    pool = objets.pool(rom)
    R = recettes.lire(rom)
    par_id = {r["id"]: r for r in R}
    tirage = {}
    pris = set()
    for r in R:
        if r["base"] is not None:
            continue                     # la variante suit sa base
        exclus = {r["produit"]}
        if r["variante"] is not None:
            exclus.add(par_id[r["variante"]]["produit"])
        candidats = [o for o in pool if o not in exclus]
        qtes = [q for _o, q in r["ingredients"]]
        for _ in range(ESSAIS):
            choix = rng.sample(candidats, len(qtes))
            cle = tuple(sorted(zip(choix, qtes)))
            if cle not in pris:
                break
        else:
            raise RuntimeError("recette %d : pas de jeu d'ingredients unique "
                               "en %d essais" % (r["id"], ESSAIS))
        pris.add(cle)
        tirage[r["id"]] = choix
        if r["variante"] is not None:
            tirage[r["variante"]] = choix
    _ecrire(rom, tirage)

    nm = objets.noms(rom, langue)
    note("=== ALCHIMIE : INGREDIENTS DES RECETTES ===")
    note("tout le pool d'objets (%d), quantites vanilla" % len(pool))
    for r in sorted(R, key=lambda r: r["ordre"]):
        ingr = " + ".join("%d x %s" % (q, nm.get(o, o)) for o, (_v, q)
                          in zip(tirage[r["id"]], r["ingredients"]))
        note("%3d  %-32s <- %s" % (r["id"], nm.get(r["produit"]), ingr))
    return dict(recettes=len(R), paires=sum(1 for r in R if r["base"]),
                pool=len(pool))


def verifier(rom, vanilla):
    """Leve si les recettes de `rom` ne suivent pas les regles ci-dessus.

    `vanilla` : la ROM d'origine (meme interface que `rom`), pour comparer
    tout ce qui ne doit pas bouger. Rend le nombre de recettes changees.
    """
    recettes.verifier(rom)          # format, liens, paires, unicite, langues
    pool = set(objets.pool(rom))
    avant = {r["id"]: r for r in recettes.lire(vanilla)}
    apres = recettes.lire(rom)
    changees = 0
    for r in apres:
        v = avant[r["id"]]
        if dict(r, ingredients=0) != dict(v, ingredients=0):
            raise ValueError("recette %d : un champ autre que les ingredients "
                             "a change" % r["id"])
        if [q for _o, q in r["ingredients"]] != [q for _o, q in
                                                  v["ingredients"]]:
            raise ValueError("recette %d : quantites changees" % r["id"])
        objs = [o for o, _q in r["ingredients"]]
        if len(set(objs)) != len(objs):
            raise ValueError("recette %d : ingredient en double" % r["id"])
        if r["produit"] in objs:
            raise ValueError("recette %d : produit parmi ses ingredients"
                             % r["id"])
        hors = [o for o in objs if o not in pool]
        if hors:
            raise ValueError("recette %d : ingredient hors du pool %s"
                             % (r["id"], hors))
        if r["ingredients"] != v["ingredients"]:
            changees += 1
    return changees


if __name__ == "__main__":
    from rom_vanilla import chemin_vanilla
    van = recettes.ouvrir(chemin_vanilla())
    print("vanilla : %d recettes changees (attendu 0)" % verifier(van, van))
