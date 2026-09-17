#!/usr/bin/env python3
"""Nom en jeu d'une zone, a partir de son code de fichier (C01M16...).

Deux fichiers, tous deux des scripts Nitro (voir treasure.py) :

  data/map/maplist9.bin    la liste des cartes. Opcode 0x67, un enregistrement
                           par carte : param 0 = identifiant numerique de carte,
                           param 4 = code de fichier (chaine), ex. 116 / "C01M16"
  data/map/mapname.gp2     mapname_<lg>.bin : opcode 0x67, param 0 = identifiant
                           de carte, param 1 = nom affiche (chaine)

Verifie : C01M16 -> 116 -> "Stornway Castle - B1", le nom que la minicarte
affiche sur le savestate du coffre rouge du joueur. Les 265 zones de
treasure.nsarc ont toutes un identifiant.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objets
import treasure as T


def _chaines(d):
    h, instrs = T.lire_script(d)
    donnees = d[h["off_donnees"]:]

    def s(o):
        try:
            return donnees[o:donnees.index(b"\x00", o)].decode("utf-8", "replace")
        except ValueError:
            return None
    return instrs, s


def noms_zones(rom, langue="en"):
    """Rend {code de fichier: nom affiche en jeu}."""
    m = bytes(rom.files[rom.filenames.idOf("data/map/maplist9.bin")])
    instrs, s = _chaines(m)
    code_id = {}
    for i in instrs:
        if i.op == 0x67 and len(i.types) > 4 and i.types[4] == 0:
            code_id.setdefault(s(i.valeurs[4]), i.valeurs[0])
    d = objets._membre_archive(rom, "data/map/mapname.gp2",
                               "mapname_%s.bin" % langue)
    instrs, s = _chaines(d)
    id_nom = {}
    for i in instrs:
        if i.op == 0x67 and len(i.valeurs) > 1 and i.types[1] == 0:
            id_nom[i.valeurs[0]] = objets.nettoyer(s(i.valeurs[1]) or "")
    return {c: id_nom.get(k, "") for c, k in code_id.items() if c}
