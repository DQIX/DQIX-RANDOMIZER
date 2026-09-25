#!/usr/bin/env python3
"""Lire un fichier interne du jeu SANS dependre de `work/extracted`.

POURQUOI CE MODULE EXISTE. Trois lectures de la chaine de construction
ouvraient des fichiers deja extraits a la main sous `work/extracted/` :

    data/prm/encfld.bin        le pool d'especes de terrain et leur rarete
    data/event/eventbattle.bin le pool des especes de combats scriptes
    data/pack_lv5/enemy.gp2    la taille des modeles, qui decide du bitmap

Sur le PC de developpement ces fichiers sont la, donc rien ne se voyait. Mais
un joueur qui lance l'application ne les a pas : il a SA ROM, et rien d'autre.
Ces trois fichiers vivent dans la ROM, et le lecteur NitroFS maison sait les en
sortir. On les lit donc a la source, une fois pour toutes.

CE QU'ON NE CHANGE PAS : la source reste la ROM **vanilla**, resolue par
`rom_vanilla.chemin_vanilla()` (variable `DQ9_VANILLA`, puis `banc/roms/`).
Lire le pool dans une ROM deja patchee randomiserait une randomisation, et la
graine ne suffirait plus a reproduire la construction.

Le cache est indexe par chemin de ROM : une construction n'ouvre la table de
noms qu'une fois, et les 23 Mo d'`enemy.gp2` ne sont lus qu'une seule fois.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nitrofs import NitroFS
from rom_vanilla import chemin_vanilla

_index = {}     # chemin de ROM -> {chemin interne: identifiant de fichier}
_fs = {}        # chemin de ROM -> NitroFS
_contenu = {}   # (chemin de ROM, chemin interne) -> octets


def _normaliser(chemin_interne):
    """`data/prm/encfld.bin` et `/data/prm/encfld.bin` designent la meme chose."""
    return "/" + chemin_interne.replace("\\", "/").lstrip("/")


def _ouvrir(rom):
    rom = os.path.abspath(rom or chemin_vanilla())
    if rom not in _fs:
        fs = NitroFS(rom)
        _fs[rom] = fs
        _index[rom] = {c: fid for fid, c in fs.paths.items()}
    return rom, _fs[rom], _index[rom]


def lire(chemin_interne, rom=None):
    """Rend les octets du fichier `chemin_interne` de la ROM.

    `rom` vaut par defaut la ROM vanilla resolue par `rom_vanilla`. Un chemin
    absent leve `SystemExit` avec un message qui nomme le fichier : c'est
    toujours le signe d'une ROM qui n'est pas la version Europe attendue.
    """
    chemin = _normaliser(chemin_interne)
    rom, fs, index = _ouvrir(rom)
    cle = (rom, chemin)
    if cle not in _contenu:
        fid = index.get(chemin)
        if fid is None:
            raise SystemExit(
                f"{chemin} est absent de {os.path.basename(rom)}.\n"
                "  Cette ROM n'est pas la version Europe multi-langue attendue.")
        _contenu[cle] = fs.read(fid)
    return _contenu[cle]


def oublier():
    """Vide le cache. Utile a un appelant qui enchaine plusieurs ROMs."""
    _index.clear()
    _fs.clear()
    _contenu.clear()


if __name__ == "__main__":
    # Temoin : les octets lus dans la ROM sont-ils ceux de work/extracted ?
    import hashlib
    for c in ("data/prm/encfld.bin", "data/event/eventbattle.bin",
              "data/pack_lv5/enemy.gp2"):
        d = lire(c)
        h = hashlib.md5(d).hexdigest()
        ref = os.path.join("work", "extracted", c.replace("/", os.sep))
        etat = "pas de temoin sur disque"
        if os.path.isfile(ref):
            with open(ref, "rb") as f:
                hr = hashlib.md5(f.read()).hexdigest()
            etat = "identique" if hr == h else f"DIFFERENT ({hr})"
        print(f"{c:<32s} {len(d):>10,} o  {h}  {etat}")
