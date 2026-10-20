#!/usr/bin/env python3
"""Les recettes d'alchimie (la Marmite), lues DANS LA ROM. Lecture seule.

OU SONT LES RECETTES. `data/bin/recipe.gp2` (58 124 octets), une archive GPC2
a cinq membres compresses (LZSS type 1), un par langue : `recipe_<lg>.bin`,
41 392 octets chacun une fois decompresse. Le code qui les charge est dans
l'overlay 6 (la Marmite) : chaines `recipe.gp2` et `recipe_<LG>.bin` en
0x021602A0, constante 0x1D7 (471, le nombre d'instructions) en 0x0215B0F8.

FORMAT -- le script Nitro generique de `treasure.py` (memes boutiques, meme
loot) :

    en-tete, 16 octets   471 instructions, section de donnees en 0xA1B0
    opcode 0x66          un entier : 470, le NOMBRE DE RECETTES
    opcode 0x67 x 470    UNE RECETTE, 20 parametres entiers (88 octets)
    0xFFFF               fin

FORMAT d'une recette (opcode 0x67), 20 parametres -- MESURE :

    p0        identifiant de la recette, 1 a 471 (359 n'existe pas). C'est
              l'`alchemyIdx` + 1 du save editor (`DQIX/editor`, data.js) :
              470 sur 470 concordent.
    p1        OBJET PRODUIT (identifiant de `itemdt`, comme objets.py)
    p2, p3    ingredient 1 : objet, quantite
    p4, p5    ingredient 2 : objet, quantite   (0, 0 si absent)
    p6, p7    ingredient 3 : objet, quantite   (0, 0 si absent)
    p8..p12   (0, 100, 100, 0, 0) partout, sauf les 22 VARIANTES de grand
              succes (voir p16) : (1..7, 10|20, 40|50, 300, 999|700).
              Sens non mesure : probablement les chances du grand succes.
    p13       drapeau 0 / 1 (339 a 1). Sens INCONNU : ne suit ni les livres
              de recettes, ni la rarete, ni la categorie.
    p14       categorie du produit : 0 arme, 1 bouclier, 2 torse, 3 jambes,
              4 tete, 5 bras, 6 pieds, 7 accessoire, 8 objet. 470 sur 470
              concordent avec l'archive `itemdt_<c>` du produit.
    p15       sous-categorie (rubrique de l'alchimiepedie) : 0-11 types
              d'arme, 12 boucliers, 13-15 torse, 16 jambes, 18-19 tete,
              20-21 bras, 22-23 pieds, 24 accessoires, 25 remedes,
              28 materiaux.
    p16       sur 22 recettes de base : l'identifiant de la recette de sa
              VARIANTE de grand succes (epee supernova -> epee hypernova),
              -1 sinon. Les deux portent les MEMES ingredients.
    p17       sur la variante : l'identifiant de sa recette de base, -1 sinon.
    p18       ordre d'affichage, 1 a 471.
    p19       cle de tri alphabetique : le SEUL champ qui change d'une
              langue a l'autre (octets +0x54/0x55 de la fiche, rien d'autre).

TEMOINS. Herbe medicinale x2 -> medicament fort (recette 440) ; epee
d'acier = epee de fer + minerai de fer + pierre de lave ; les 22 armes et
armures ultimes des legendes sont des variantes de grand succes.

LES LIVRES DE RECETTES ne portent pas les ingredients. Ils vivent dans les
bibliotheques, `data/scenario/htana<X>.gp2` (C, D, H, M, R, S, X), en texte :
"<LEADER> finds recipes for a steel shield, a steel helmet and full plate
armour." -- seulement les NOMS des produits (105 livres, 287 recettes
citees). Quelques phrases d'ambiance et `questmsg.gp2` citent des
ingredients en clair (pierre solaire, acier de geant...) : elles mentiront
si l'on randomise les ingredients.

Voir docs/research/19-alchemy.md (section 102).

Usage :
  python scripts/recettes.py [rom.nds] [--langue fr] [--verifier]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gp2
import objets
import treasure as T

CHEMIN = "data/bin/recipe.gp2"
OP_NOMBRE = 0x66
OP_RECETTE = 0x67
NB_PARAMS = 20
NB_RECETTES = 470
ID_ABSENT = 359
QTE_MAX = 9
SANS = 0xFFFFFFFF
NEUTRE = (0, 100, 100, 0, 0)          # p8..p12 hors variantes
NB_VARIANTES = 22
LANGUES = ("de", "en", "es", "fr", "it")

# p14 -> archive itemdt du produit
CATEGORIE = "wsbuhaldt"
NOM_CATEGORIE = ("arme", "bouclier", "torse", "jambes", "tete", "bras",
                 "pieds", "accessoire", "objet")


class _Rom(object):
    """Adaptateur minimal sur nitrofs.NitroFS, pour lire sans ndspy.

    Rend `filenames.idOf(chemin)` et `files[fid]`, ce dont objets.py a besoin.
    """
    def __init__(self, chemin):
        import nitrofs
        fs = nitrofs.NitroFS(chemin)
        ids = {p.lstrip("/"): fid for fid, p in fs.paths.items()}

        class _Noms(object):
            def idOf(self, p):
                return ids.get(p)

        class _Fichiers(object):
            def __getitem__(self, fid):
                return fs.read(fid)

        self.filenames = _Noms()
        self.files = _Fichiers()


def ouvrir(chemin):
    """Ouvre une ROM pour la lecture, sans dependance."""
    return _Rom(chemin)


def fichier(rom, langue="en"):
    """Rend les octets decompresses de `recipe_<lg>.bin`."""
    return objets._membre_archive(rom, CHEMIN, "recipe_%s.bin" % langue)


def lire(rom, langue="en"):
    """Rend la liste des recettes, dans l'ordre du fichier.

    Chaque recette : dict(id, produit, ingredients=[(objet, qte)],
    params, drapeau, categorie, sous_categorie, variante, base, ordre, tri,
    offsets) ; `offsets` donne l'offset de chaque parametre dans le membre
    decompresse, pour une reecriture en place.
    """
    d = fichier(rom, langue)
    tete, instrs = T.lire_script(d)
    nombre = [i for i in instrs if i.op == OP_NOMBRE]
    fiches = [i for i in instrs if i.op == OP_RECETTE]
    if len(nombre) != 1 or nombre[0].valeurs[0] != len(fiches):
        raise ValueError("recipe_%s : l'opcode 0x66 n'annonce pas %d recettes"
                         % (langue, len(fiches)))
    if len(fiches) != NB_RECETTES:
        raise ValueError("recipe_%s : %d recettes, %d attendues"
                         % (langue, len(fiches), NB_RECETTES))
    out = []
    for ins in fiches:
        v = ins.valeurs
        if len(v) != NB_PARAMS or any(t != 1 for t in ins.types):
            raise ValueError("recette en 0x%X : %d parametres, pas %d entiers"
                             % (ins.debut, len(v), NB_PARAMS))
        out.append(dict(
            id=v[0], produit=v[1],
            ingredients=[(v[2 + 2 * k], v[3 + 2 * k]) for k in range(3)
                         if v[2 + 2 * k]],
            params=tuple(v[8:13]), drapeau=v[13], categorie=v[14],
            sous_categorie=v[15],
            variante=None if v[16] == SANS else v[16],
            base=None if v[17] == SANS else v[17],
            ordre=v[18], tri=v[19], offsets=ins.offsets))
    return out


def verifier(rom, recettes=None):
    """Leve si la lecture ne rend pas ce que la ROM europeenne doit rendre.

    Rend la liste des messages de controle, pour l'affichage.
    """
    R = recettes if recettes is not None else lire(rom)
    cat = objets.catalogue(rom)
    imp = objets.objets_importants(rom)
    msgs = []

    ids = [r["id"] for r in R]
    if sorted(ids) != [i for i in range(1, NB_RECETTES + 2) if i != ID_ABSENT]:
        raise ValueError("identifiants de recette inattendus")
    par_id = {r["id"]: r for r in R}

    for r in R:
        if r["produit"] not in cat:
            raise ValueError("recette %d : produit %d inconnu"
                             % (r["id"], r["produit"]))
        if not 1 <= len(r["ingredients"]) <= 3:
            raise ValueError("recette %d : %d ingredients"
                             % (r["id"], len(r["ingredients"])))
        for o, q in r["ingredients"]:
            if o not in cat or not 1 <= q <= QTE_MAX:
                raise ValueError("recette %d : ingredient (%d, %d) invalide"
                                 % (r["id"], o, q))
            if o in imp:
                raise ValueError("recette %d : ingredient important %d"
                                 % (r["id"], o))
        if r["produit"] in imp:
            raise ValueError("recette %d : produit important" % r["id"])
        if CATEGORIE[r["categorie"]] != cat[r["produit"]][0]:
            raise ValueError("recette %d : categorie %d, produit dans itemdt_%s"
                             % (r["id"], r["categorie"], cat[r["produit"]][0]))
    msgs.append("%d recettes, identifiants 1-%d sauf %d, produits et "
                "ingredients connus, quantites 1-%d, aucun objet important"
                % (len(R), NB_RECETTES + 1, ID_ABSENT, QTE_MAX))

    produits = [r["produit"] for r in R]
    if len(set(produits)) != len(produits):
        raise ValueError("un objet est produit par deux recettes")

    variantes = [r for r in R if r["base"] is not None]
    if len(variantes) != NB_VARIANTES:
        raise ValueError("%d variantes de grand succes, %d attendues"
                         % (len(variantes), NB_VARIANTES))
    for v in variantes:
        b = par_id[v["base"]]
        if b["variante"] != v["id"] or b["ingredients"] != v["ingredients"]:
            raise ValueError("variante %d : lien ou ingredients differents de "
                             "la base %d" % (v["id"], b["id"]))
        if v["params"] == NEUTRE or b["params"] != NEUTRE:
            raise ValueError("variante %d : parametres p8-p12 inattendus"
                             % v["id"])
    if any(r["params"] != NEUTRE for r in R if r["base"] is None):
        raise ValueError("parametres p8-p12 hors des variantes")
    msgs.append("%d variantes de grand succes, memes ingredients que leur "
                "base, liens dans les deux sens" % len(variantes))

    # Hors des paires, deux recettes n'ont jamais le meme jeu d'ingredients.
    vus = {}
    for r in R:
        if r["base"] is not None:
            continue
        k = tuple(sorted(r["ingredients"]))
        if k in vus:
            raise ValueError("recettes %d et %d : memes ingredients"
                             % (vus[k], r["id"]))
        vus[k] = r["id"]
    msgs.append("aucun jeu d'ingredients partage hors des variantes")

    # Les cinq langues : seule la cle de tri (p19) change.
    for lg in LANGUES:
        autre = lire(rom, lg)
        for a, b in zip(R, autre):
            ca = dict(a, tri=0, offsets=0)
            cb = dict(b, tri=0, offsets=0)
            if ca != cb:
                raise ValueError("recipe_%s, recette %d : differe de "
                                 "l'anglais hors cle de tri" % (lg, a["id"]))
    msgs.append("5 langues identiques hors cle de tri (p19)")
    return msgs


def main(argv):
    from rom_vanilla import chemin_vanilla
    langue = "en"
    controle = False
    chemin = None
    i = 0
    while i < len(argv):
        if argv[i] == "--langue":
            langue = argv[i + 1]
            i += 1
        elif argv[i] == "--verifier":
            controle = True
        else:
            chemin = argv[i]
        i += 1
    rom = ouvrir(chemin or chemin_vanilla())
    R = lire(rom, langue)
    if controle:
        for m in verifier(rom, lire(rom)):
            print("OK  " + m)
        return
    nm = objets.noms(rom, langue)

    def n(o):
        return "%s (%d)" % (nm.get(o, "?"), o)

    for r in sorted(R, key=lambda r: r["ordre"]):
        ingr = " + ".join("%d x %s" % (q, n(o)) for o, q in r["ingredients"])
        note = ""
        if r["variante"]:
            note = "  [variante de grand succes : recette %d]" % r["variante"]
        if r["base"]:
            note = "  [grand succes de la recette %d, p8-p12 %s]" % (
                r["base"], ",".join(str(x) for x in r["params"]))
        print("%3d  %-10s %-34s <- %s%s" % (
            r["id"], NOM_CATEGORIE[r["categorie"]], n(r["produit"]), ingr,
            note))


if __name__ == "__main__":
    main(sys.argv[1:])
