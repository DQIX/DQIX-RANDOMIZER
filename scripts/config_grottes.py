"""La categorie `grottes` de « Creer sa ROM » (ZER-92) : les lignes de
`randTD.bin`, la table des coffres des grottes (rangs 1 a 10), pour
`config_rom`. Meme lecture, memes plafonds et memes verrous que les tables
de `config_coffres` (242 lignes, 32 par rang : meme tampon, meme `Sample`).
Les embuscades ne se changent pas (ZER-21).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config_coffres as CC
import objets
import treasure as T

FORME = dict(tables=(("lignes", None),),
             champs=(("objet", "objet"), ("or", "nombre")),
             bornes={"or": (0, 0xFFFF)}, verrous=set(),
             place=CC.place_ligne)


def interdits(rom):
    return CC.interdits(rom)


def exporter(rom, langue="en"):
    nm = objets.noms(rom, langue, accents=True)
    return {"lignes": CC.lignes_table(rom, T.TABLE_GROTTOS, nm)}


def tirer_section(rom, graine, langue="en", **options):
    return CC.tirer_section(rom, graine, langue, categorie="grottes", **options)


def appliquer(rom, section, verrous=True, vanilla=None):
    n = CC.ecrire_tables(rom, {T.TABLE_GROTTOS: CC.lignes_voulues(
        rom, "grottes.lignes", section.get("lignes"), verrous)})
    CC.vanilla_si_egale(rom, vanilla)
    return n
