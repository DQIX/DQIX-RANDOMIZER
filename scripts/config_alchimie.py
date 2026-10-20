"""La categorie `alchimie` de « Creer sa ROM » (ZER-90) : les ingredients de
chaque recette de la Marmite, pour `config_rom`.

LES CASES. Une ligne par recette (470, `recettes.py`), un a trois
ingredients (`ingredient1..3`), chacun avec sa quantite vanilla
(`quantite1..3`, ecrite pour etre lue : on ne la change pas). Le produit ne
bouge pas.

GRANDS SUCCES (joueur, 19/10/2026) : la recette de base et sa variante sont
deux lignes independantes ; changer l'une laisse l'autre telle quelle.

AUCUNE REGLE : un ingredient peut etre le produit, deux recettes peuvent
avoir le meme jeu. Le VERROU (levable) : aucun objet important ou hors
tirage parmi les ingredients -- la Marmite le consommerait.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import objets
import recettes

CHAMPS = tuple(("ingredient%d" % k, "objet") for k in (1, 2, 3))


def _place(t, table, k, l):
    return l.get("produit_nom") or str(l["produit"])


FORME = dict(tables=(("recettes", recettes.NB_RECETTES),),
             champs=CHAMPS, verrous=set(), place=_place,
             quantites={"ingredient%d" % k: "quantite%d" % k for k in (1, 2, 3)})


def interdits(rom):
    return objets.objets_importants(rom) | objets.HORS_TIRAGE


def exporter(rom, langue="en"):
    nm = objets.noms(rom, langue, accents=True)
    out = []
    for r in recettes.lire(rom):
        l = {"recette": r["id"], "produit": r["produit"],
             "produit_nom": nm.get(r["produit"], "")}
        for k, (o, q) in enumerate(r["ingredients"], 1):
            l["ingredient%d" % k] = o
            l["ingredient%d_nom" % k] = nm.get(o, "")
            l["quantite%d" % k] = q
        out.append(l)
    return {"recettes": out}


def tirer_section(rom, graine, langue="en"):
    import patch_alchimie
    patch_alchimie.patcher(rom, graine)
    return exporter(rom, langue)


def appliquer(rom, section, verrous=True, vanilla=None):
    """Ecrit les ingredients. Rend le nombre de recettes changees."""
    import patch_alchimie
    from config_rom import ConfigInvalide
    cat = objets.catalogue(rom)
    nm = objets.noms(rom, "en")
    refuses = interdits(rom) if verrous else set()
    R = recettes.lire(rom)
    lignes = section.get("recettes")
    if not isinstance(lignes, list) or len(lignes) != len(R):
        raise ConfigInvalide("alchimie.recettes : %d cases attendues" % len(R))
    tirage, n = {}, 0
    for i, (l, r) in enumerate(zip(lignes, R)):
        ou = "alchimie.recettes[%d]" % i
        try:
            if int(l["recette"]) != r["id"]:
                raise ConfigInvalide(ou + " : recette %d attendue" % r["id"])
            objs = [int(l["ingredient%d" % k])
                    for k in range(1, len(r["ingredients"]) + 1)]
        except (KeyError, TypeError, ValueError):
            raise ConfigInvalide(ou + " : %d ingredient(s) entiers attendus"
                                 % len(r["ingredients"]))
        if "ingredient%d" % (len(r["ingredients"]) + 1) in l:
            raise ConfigInvalide(ou + " : %d ingredient(s) au plus (format du "
                                 "jeu)" % len(r["ingredients"]))
        for o in objs:
            if o not in cat:
                raise ConfigInvalide(ou + " : objet %d inconnu du jeu" % o)
            if o in refuses:
                raise ConfigInvalide(ou + " : %s est un objet de quete ou de "
                                     "debug, il casserait la partie"
                                     % nm.get(o, o))
        tirage[r["id"]] = objs
        n += objs != [o for o, _q in r["ingredients"]]
    if n:
        # DEPUIS LES OCTETS VANILLA : l'archive est recompressee, et seule la
        # meme entree rend les memes octets que le tirage du randomizer.
        # Revenue a la vanilla, elle en reprend les octets.
        if vanilla is not None:
            fid = rom.filenames.idOf(recettes.CHEMIN)
            rom.files[fid] = bytes(vanilla.files[
                vanilla.filenames.idOf(recettes.CHEMIN)])
            if all(tirage[r["id"]] == [o for o, _q in r["ingredients"]]
                   for r in recettes.lire(vanilla)):
                return n
        patch_alchimie._ecrire(rom, tirage)
    return n
