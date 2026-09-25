#!/usr/bin/env python3
"""Randomise les sorts appris a niveau fixe par les vocations.

CE QUI EST TOUCHE, et rien d'autre : le champ « sort » des 107 triplets
(vocation, sort, niveau) de `data/prm/spelltable.bin`. Les niveaux ne bougent
pas, le nombre de sorts d'une vocation ne bouge pas, la taille du fichier ne
bouge pas -- on reecrit 107 mots la ou ils sont.

CE QUI N'EST PAS TOUCHE : les trois vocations sans magie (guerrier, artiste
martial, gladiateur) n'ont aucun triplet, donc elles n'en recoivent aucun.
Leur en donner demanderait d'agrandir la table, donc de changer la disposition
de la ROM ; c'est un autre chantier.

DEUX MODES, comme pour le loot et les boutiques :

  equilibre (defaut)  Les sorts tires sont ranges par ordre de puissance avant
                      d'etre poses sur les niveaux. La puissance d'un sort est
                      prise du jeu lui-meme : le niveau MEDIAN auquel le
                      vanilla l'enseigne. Une vocation apprend donc encore ses
                      sorts faibles tot et ses sorts forts tard -- mais ce ne
                      sont plus les memes sorts.
  chaos               Aucun ordre : Omniheal peut tomber au niveau 1.

DANS LES DEUX CAS, un meme sort n'est jamais donne deux fois a la meme
vocation, et le tirage se fait dans un paquet melange (`Pioche`), donc les 61
sorts sortent tous quelque part tant qu'il reste des places -- 107 places pour
61 sorts.
"""
import collections
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sorts
from prmtable import PrmTable

# Les noms du jeu lui-meme, lus dans `data/bin/str_debug_en.bin` :
# None, Warrior, Priest, Mage, Martial Artist, Thief, Minstrel, Gladiator,
# Armamentalist, Paladin, Sage, Luminary, Ranger.
VOCATIONS = {
    0: "None", 1: "Warrior", 2: "Priest", 3: "Mage", 4: "Martial Artist",
    5: "Thief", 6: "Minstrel", 7: "Gladiator", 8: "Armamentalist",
    9: "Paladin", 10: "Sage", 11: "Luminary", 12: "Ranger",
}


class Pioche(object):
    """Tirage sans remise, paquet reconstitue quand il est vide.

    Meme raison que pour le loot : `rng.choice` laissait des sorts jamais
    enseignes et d'autres trois fois.
    """

    def __init__(self, rng, pool):
        self.rng = rng
        self.pool = list(pool)
        self.paquet = []

    def tirer(self, interdits):
        """Rend un sort absent d'`interdits`. Remet les refuses sous le paquet."""
        refuses = []
        try:
            for _ in range(len(self.pool) * 2 + 1):
                if not self.paquet:
                    self.paquet = list(self.pool)
                    self.rng.shuffle(self.paquet)
                choisi = self.paquet.pop()
                if choisi not in interdits:
                    return choisi
                refuses.append(choisi)
            raise AssertionError("plus aucun sort disponible")
        finally:
            # LES REFUSES REPARTENT DANS LE PAQUET, sinon une vocation qui en
            # ecarte beaucoup viderait le paquet pour les suivantes et la
            # couverture s'effondrerait.
            self.paquet = refuses + self.paquet


def puissance(appris):
    """{sort: niveau median auquel le vanilla l'enseigne}.

    C'est la seule mesure de puissance qu'on ait sans juger a la main : le jeu
    place Frizz au niveau 1 et Omniheal au 65, et cet ordre EST son echelle.
    Un sort que le vanilla n'enseigne nulle part prend le niveau median
    general, faute de mieux.
    """
    par_sort = collections.defaultdict(list)
    for _i, _v, s, niveau in appris:
        par_sort[s].append(niveau)
    medianes = {s: statistics.median(l) for s, l in par_sort.items()}
    defaut = statistics.median(list(medianes.values()) or [1])
    return medianes, defaut


def patcher(rom, rng, journal=None, chaos=False):
    """Reecrit les sorts appris. Rend un dictionnaire de comptes."""
    def note(ligne=""):
        if journal is not None:
            journal.write(ligne + "\n")

    fid = rom.filenames.idOf(sorts.CHEMIN_TABLE)
    table = PrmTable(bytes(rom.files[fid]))
    taille_avant = len(table.data)

    appris = sorts.apprentissages(rom)
    noms = sorts.noms(rom)
    pool = sorts.pool(rom)
    medianes, defaut = puissance(appris)
    pioche = Pioche(rng, pool)

    par_voc = collections.defaultdict(list)
    for i, v, s, niveau in appris:
        par_voc[v].append((i, s, niveau))

    comptes = dict(vocations=0, sorts=0)
    note("=== SORTS APPRIS PAR NIVEAU ===")
    note("mode : %s" % ("chaos" if chaos else "equilibre (ranges par puissance)"))
    for v in sorted(par_voc):
        entrees = sorted(par_voc[v], key=lambda e: e[2])
        deja = set()
        tires = []
        for _ in entrees:
            choisi = pioche.tirer(deja)
            deja.add(choisi)
            tires.append(choisi)
        if not chaos:
            # LES NIVEAUX SONT DEJA TRIES : il suffit de trier les sorts par
            # puissance pour que le faible arrive tot et le fort tard.
            tires.sort(key=lambda s: (medianes.get(s, defaut), s))
        comptes["vocations"] += 1
        note("")
        note("%-16s (%d sorts)" % (VOCATIONS.get(v, "vocation %d" % v),
                                   len(entrees)))
        for (i, ancien, niveau), neuf in zip(entrees, tires):
            table.set_field(i, 1, neuf)
            comptes["sorts"] += 1
            note("   niv %2d  %-22s -> %s"
                 % (niveau, sorts.nom_lisible(noms, ancien),
                    sorts.nom_lisible(noms, neuf)))

    if len(table.data) != taille_avant:
        raise AssertionError("spelltable.bin a change de taille")
    rom.files[fid] = bytes(table.data)
    note("")
    return comptes


def verifier(rom):
    """Controle de coherence sur une ROM deja patchee. Leve si ca cloche."""
    appris = sorts.apprentissages(rom)
    permis = set(sorts.pool(rom))
    par_voc = collections.defaultdict(list)
    for _i, v, s, niveau in appris:
        par_voc[v].append((s, niveau))
    if len(appris) != 107:
        raise AssertionError("%d apprentissages, 107 attendus" % len(appris))
    for v, l in par_voc.items():
        vus = [s for s, _n in l]
        if len(vus) != len(set(vus)):
            raise AssertionError("vocation %d : un sort y figure deux fois" % v)
        for s, _n in l:
            if s not in permis:
                raise AssertionError("vocation %d : sort %d hors du pool" % (v, s))
    return True


if __name__ == "__main__":
    import random

    import ndspy.rom
    from rom_vanilla import chemin_vanilla
    if len(sys.argv) < 3:
        sys.exit("usage: patch_sorts.py <rom.nds> <sortie.nds> [graine] [chaos]")
    r = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    g = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    print(patcher(r, g, journal=sys.stdout,
                  chaos=len(sys.argv) > 4 and sys.argv[4] == "chaos"))
    verifier(r)
    r.saveToFile(sys.argv[2])
