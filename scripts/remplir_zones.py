#!/usr/bin/env python3
"""Remplit les emplacements d'espece LIBRES de chaque zone.

CONSTAT QUI MOTIVE CE SCRIPT (voir docs/RESEARCH.md §20). Le jeu ne peut faire
apparaitre que les especes dont il a precharge le modele au chargement de la
carte, et cette liste vient de la table de la zone. Tirer en dehors fait echouer
l'apparition : le monstre n'apparait pas et le jeu reessaie en boucle (3 629
appels mesures contre 2 pour une espece valide).

La variete par zone est donc bornee par la TAILLE de la table, pas par le
hasard. Or `encmons.bin` laisse 564 emplacements libres sur 209 cartes -- la
plupart n'utilisent que 5 places sur 8 -- et certaines zones d'`encfld.bin` en
comptent jusqu'a 13. Le moteur sait donc gerer davantage d'especes qu'il n'en
declare habituellement.

Ce script remplit les emplacements libres avec des especes tirees au hasard,
ce qui augmente la variete par zone sans rien ajouter au fichier : on n'ecrit
que dans des champs qui existent deja.

Usage: python scripts/remplir_zones.py <rom.nds> <sortie.nds> <graine>
"""
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ndspy.rom
from montable import TableMonstres
from prmtable import PrmTable

CHEMIN = "data/prm/encmons.bin"


def remplir(rom, rng, ids_valides, choix):
    fid = rom.filenames.idOf(CHEMIN)
    t = PrmTable(rom.files[fid])
    ajouts = 0
    for ir, r in enumerate(t.records):
        if r.tag != 0x66 or len(r.fields) < 2:
            continue
        for ic in range(1, len(r.fields)):
            v = r.fields[ic]
            neuf = v
            for dec in (0, 16):
                if ((neuf >> dec) & 0xFFFF) not in ids_valides:
                    neuf = (neuf & ~(0xFFFF << dec)) | (rng.choice(choix) << dec)
                    ajouts += 1
            if neuf != v:
                t.set_field(ir, ic, neuf)
    rom.files[fid] = bytes(t.data)
    return ajouts


if __name__ == "__main__":
    src, sortie = sys.argv[1], sys.argv[2]
    graine = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    rng = random.Random(graine)
    table, _ = TableMonstres.depuis_rom(src)
    ids = {m.id for m in table}
    # on ne tire que parmi les especes de terrain plausibles (identifiants <= 347)
    choix = sorted(i for i in ids if i <= 347)
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    n = remplir(rom, rng, ids, choix)
    print(f"{n} emplacements libres remplis, parmi {len(choix)} especes")
    rom.saveToFile(sortie)
    print(f"ecrit : {sortie} ({os.path.getsize(sortie):,} o)")
