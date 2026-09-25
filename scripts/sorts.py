#!/usr/bin/env python3
"""Les sorts de Dragon Quest IX : leurs noms, et qui les apprend quand.

OU C'EST, mesure le 21 septembre 2026 :

  `data/prm/spelltable.bin` -- une table taggee, deux sortes d'enregistrements :

      tag 0x66, 2 champs   (id du sort, id d'action - 1)      65 entrees
      tag 0x67, 3 champs   (vocation, id du sort, niveau)    107 entrees

    Les 107 triplets sont LES SORTS APPRIS A NIVEAU FIXE. Neuf vocations sur
    douze en ont ; les vocations 1, 4 et 7 n'apprennent aucun sort (guerrier,
    artiste martial, gladiateur -- ce sont les vocations sans magie).

  `data/prm/actname.nat` -- les noms d'action, en anglais, pour tout ce que le
    jeu sait faire (682 entrees, 337 chaines distinctes) :

      +0x00  u16  nombre, sur les 12 bits de poids faible : 682
      +0x08       des paires (u32 offset du nom, u32 identifiant d'action)
      +0x1554     le pool de chaines, terminees par zero (le premier octet est
                  un zero de bourrage : "Attack" est a l'offset 1)

LE DECALAGE DE UN, sans quoi rien ne colle. Le second champ d'un
enregistrement 0x66 vaut l'identifiant d'action MOINS UN. Verifie sur la suite
complete : le sort 0 devient Frizz, 1 Frizzle, 2 Kafrizz, 3 Kafrizzle,
4 Crack... soit exactement les lignes de sorts du jeu, dans l'ordre. Avec le
decalage nul on obtient une bouillie (le sort 0 n'a pas de nom, le 3 devient
Fullheal).

LE POOL. 61 sorts portent un nom et sont enseignes en vanilla. Quatre
identifiants (60, 61, 62, 65) n'ont ni nom ni usage : on ne les tire pas. Un
seul, le 24, est enseigne sans porter de nom -- on le garde, puisque le jeu
lui-meme le donne a une vocation.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prmtable import PrmTable

CHEMIN_TABLE = "data/prm/spelltable.bin"
CHEMIN_NOMS = "data/prm/actname.nat"
POOL_NOMS = 5460          # debut du pool de chaines d'actname.nat
TAG_NOM, TAG_APPRIS = 0x66, 0x67


def _lire(rom, chemin):
    fid = rom.filenames.idOf(chemin)
    if fid is None:
        raise ValueError("absent de la ROM : " + chemin)
    return bytes(rom.files[fid])


def noms_actions(rom):
    """Rend {identifiant d'action: nom anglais}, lu dans `actname.nat`."""
    d = _lire(rom, CHEMIN_NOMS)
    out = {}
    k = 8
    while k + 8 <= POOL_NOMS:
        offset, ident = struct.unpack_from("<II", d, k)
        o = POOL_NOMS + offset
        fin = d.find(b"\x00", o)
        if 0 <= o < len(d) and fin > o:
            out[ident] = d[o:fin].decode("utf-8", "replace")
        k += 8
    return out


def nom_lisible(noms, ident):
    """Le nom du sort, ou `sort #24` pour celui que le jeu enseigne sans nom."""
    return noms.get(ident) or "sort #%d" % ident


def noms(rom):
    """Rend {id de sort: nom}. Un nom vide signale un identifiant inutilise."""
    table = PrmTable(_lire(rom, CHEMIN_TABLE))
    actions = noms_actions(rom)
    out = {}
    for r in table.records:
        if r.tag == TAG_NOM and len(r.fields) == 2:
            # LE DECALAGE DE UN : voir l'en-tete du module.
            out[r.fields[0]] = actions.get(r.fields[1] + 1, "")
    return out


def apprentissages(rom):
    """Rend [(index d'enregistrement, vocation, sort, niveau)], dans l'ordre."""
    table = PrmTable(_lire(rom, CHEMIN_TABLE))
    out = []
    for i, r in enumerate(table.records):
        if r.tag == TAG_APPRIS and len(r.fields) == 3:
            out.append((i, r.fields[0], r.fields[1], r.fields[2]))
    return out


def pool(rom):
    """Les sorts tirables : ceux qui portent un nom, plus ceux que le jeu
    enseigne deja. Rend une liste triee."""
    n = noms(rom)
    enseignes = {s for _i, _v, s, _l in apprentissages(rom)}
    return sorted({s for s, nom in n.items() if nom} | enseignes)


if __name__ == "__main__":
    import collections

    import ndspy.rom
    from rom_vanilla import chemin_vanilla
    rom = ndspy.rom.NintendoDSRom.fromFile(
        sys.argv[1] if len(sys.argv) > 1 else chemin_vanilla())
    n = noms(rom)
    par_voc = collections.defaultdict(list)
    for _i, v, s, niveau in apprentissages(rom):
        par_voc[v].append((niveau, s))
    print("%d sorts tirables" % len(pool(rom)))
    for v in sorted(par_voc):
        print("vocation %2d : %d sorts" % (v, len(par_voc[v])))
        for niveau, s in sorted(par_voc[v]):
            print("   niv %2d  %s" % (niveau, n.get(s, "?%d" % s)))
