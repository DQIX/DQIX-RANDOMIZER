"""La categorie `sorts` de « Creer sa ROM » (ZER-91) : le sort que chaque
vocation apprend a chaque niveau, pour `config_rom`.

LES CASES. Les 107 triplets (vocation, sort, niveau) de `spelltable.bin`
(sorts.py) : le niveau et la vocation sont la place, le sort se choisit
parmi les sorts du jeu (`sorts.pool`, le format : un identifiant de sort
nomme), sous le nom que le jeu affiche dans la langue choisie. Les trois
vocations sans magie n'ont aucun triplet : leur en donner agrandirait la
table (patch_sorts). Aucune regle : un meme sort peut revenir
deux fois dans une vocation. Aucun verrou.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sorts
from prmtable import PrmTable


def _place(t, table, k, l):
    return t("place_sort", l.get("vocation_nom") or l["vocation"],
             l["niveau"])


FORME = dict(tables=(("appris", 107),), champs=(("sort", "sort"),),
             verrous=set(), place=_place)


def interdits(rom):
    return set()


def choisissables(rom, langue="en"):
    """[(identifiant, nom)] des sorts qu'une case peut recevoir, par nom, tels
    que le jeu les affiche dans `langue` (sorts.noms_localises)."""
    nm = sorts.noms_localises(rom, langue)
    return sorted(((s, nm.get(s) or "#%d" % s) for s in sorts.pool(rom)),
                  key=lambda x: x[1].lower())


def exporter(rom, langue="en"):
    import config_vocations
    nm = sorts.noms_localises(rom, langue)
    voc = config_vocations.noms(rom, langue)
    return {"appris": [{"vocation": v, "vocation_nom": voc.get(v, ""),
                        "niveau": niv, "sort": s,
                        "nom": nm.get(s, "")}
                       for _i, v, s, niv in sorts.apprentissages(rom)]}


def tirer_section(rom, graine, langue="en", chaos=False):
    import random
    import patch_sorts
    patch_sorts.patcher(rom, random.Random(graine), chaos=chaos)
    return exporter(rom, langue)


def appliquer(rom, section, verrous=True, vanilla=None):
    from config_rom import ConfigInvalide
    appris = sorts.apprentissages(rom)
    # le pool compte les sorts ENSEIGNES : un tirage peut en avoir retire un
    # (le sort sans nom #24), la vanilla le rend
    permis = set(sorts.pool(rom)) | (set(sorts.pool(vanilla)) if vanilla
                                     else set())
    lignes = section.get("appris")
    if not isinstance(lignes, list) or len(lignes) != len(appris):
        raise ConfigInvalide("sorts.appris : %d cases attendues" % len(appris))
    fid = rom.filenames.idOf(sorts.CHEMIN_TABLE)
    table = PrmTable(bytes(rom.files[fid]))
    n = 0
    for k, (l, (i, v, s, niv)) in enumerate(zip(lignes, appris)):
        ou = "sorts.appris[%d]" % k
        try:
            neuf, lv, ln = int(l["sort"]), int(l["vocation"]), int(l["niveau"])
        except (KeyError, TypeError, ValueError):
            raise ConfigInvalide(ou + " : 'vocation', 'niveau' et 'sort' "
                                 "entiers attendus")
        if (lv, ln) != (v, niv):
            raise ConfigInvalide(ou + " : vocation %d niveau %d attendus"
                                 % (v, niv))
        if neuf not in permis:
            raise ConfigInvalide(ou + " : %d n'est pas un sort du jeu" % neuf)
        if neuf != s:
            table.set_field(i, 1, neuf)
            n += 1
    if n:
        rom.files[fid] = bytes(table.data)
    return n
