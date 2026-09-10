#!/usr/bin/env python3
"""Aligne `encmons.bin` sur `encfld.bin` : la liste de prechargement suit le tirage.

LE DIAGNOSTIC, etabli par mesure en jeu (docs/RESEARCH.md §23).

Deux fichiers, deux roles, et ils etaient desynchronises :

    encfld.bin   table de tirage ponderee   -> 24 especes apres agrandissement
    encmons.bin  liste de prechargement     -> 6 especes au maximum

Une espece ne peut apparaitre que si son modele est precharge. Mesure sur la
ROM v9, carte 20001 : le tireur rendait 25 especes distinctes, mais
l'intersection des deux listes ne comptait que **4** especes -- exactement ce que
le joueur voyait a l'ecran. Agrandir la table de tirage sans agrandir la liste de
prechargement ne sert donc a rien.

Ce script reecrit `encmons.bin` pour que chaque carte declare EXACTEMENT les
especes que son groupe de tirage peut produire.

FORMAT D'UN ENREGISTREMENT, verifie :

    u16 tag = 0x66
    u8  nb_champs
    ... types, 2 BITS PAR CHAMP (valeur 1 = u32), puis bourrage 0xFF de sorte
        que (2 + longueur du descripteur) soit un multiple de 4
    N x u32  les champs : [id_carte, 0, paire, paire, ...]
             chaque paire porte deux identifiants (u16 bas | u16 haut)

Le modele est valide : il reproduit a l'identique les trois formes presentes dans
le fichier d'origine.

    3 champs  -> desc 0315          taille 16
    4 champs  -> desc 0455          taille 20
    5 champs  -> desc 055501ffffff  taille 28
   14 champs  -> desc 0e55555555ff  taille 64   (construit ici, 24 identifiants)

ATTENTION AUX ZEROS. Les moities de u16 qui ne portent pas d'identifiant valent
0 (560 occurrences) ou 0xFFFF (4). Ce sont des TERMINATEURS : les remplir sans
allonger l'enregistrement avait fait disparaitre tous les monstres du jeu. Ici on
allonge l'enregistrement et on ne laisse aucun trou avant la fin de la liste.

Usage: python scripts/agrandir_encmons.py <rom.nds> <sortie.nds>

OBSOLETE : remplace par `scripts/resync_zones.py`, qui reconstruit les deux
fichiers ENSEMBLE. Deux erreurs ici : les moities de u16 nulles ne sont pas des
terminateurs (elles sont sautees), et le champ 1 n'est pas libre mais une porte
de position. Voir docs/RESEARCH.md 24.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ndspy.rom
from prmtable import PrmTable

CHEMIN_MONS = "data/prm/encmons.bin"
CHEMIN_FLD = "data/prm/encfld.bin"


def descripteur(n):
    """Descripteur et taille totale d'un enregistrement de tag 0x66 a n champs."""
    bits = 0
    for i in range(n):
        bits |= 1 << (2 * i)            # type 1 pour chaque champ
    n_type = -(-2 * n // 8)
    octets = bytes([(bits >> (8 * k)) & 0xFF for k in range(n_type)])
    desc = bytes([n]) + octets
    total = -(-(2 + len(desc)) // 4) * 4
    return desc + b"\xff" * (total - 2 - len(desc)), total + 4 * n


def especes_par_carte(rom):
    """Rend {id_carte: [identifiants]} d'apres les groupes d'encfld.bin.

    Une carte peut avoir plusieurs groupes ; on prend l'union, car le
    prechargement doit couvrir tout ce que la carte est susceptible de produire.
    """
    p = PrmTable(bytes(rom.files[rom.filenames.idOf(CHEMIN_FLD)]))
    out, carte = {}, None
    for r in p.records:
        if r.tag == 0x69:
            carte = r.fields[0]
            out.setdefault(carte, [])
        elif r.tag == 0x67 and len(r.fields) == 2 and carte is not None:
            i = r.fields[0] & 0xFFF
            if i and i not in out[carte]:
                out[carte].append(i)
    return out


def agrandir(rom, capacite=24, bavard=True):
    par_carte = especes_par_carte(rom)
    fid = rom.filenames.idOf(CHEMIN_MONS)
    brut = bytes(rom.files[fid])
    t = PrmTable(brut)
    entete = brut[:t.body]
    non_parses = t.nb - len(t.records)

    n_paires = -(-capacite // 2)
    n_champs = 2 + n_paires
    desc, taille = descripteur(n_champs)

    corps = bytearray()
    n_reecrits = n_intacts = 0
    for r in t.records:
        liste = par_carte.get(r.fields[0]) if r.tag == 0x66 and r.fields else None
        # on ne reecrit que les enregistrements de carte reconnus et de forme
        # standard ; tout le reste est recopie tel quel
        standard = r.desc.hex() in ("0315", "0455", "055501ffffff")
        if liste and standard:
            champs = [r.fields[0], 0]
            liste = liste[:capacite]
            for k in range(n_paires):
                bas = liste[2 * k] if 2 * k < len(liste) else 0
                haut = liste[2 * k + 1] if 2 * k + 1 < len(liste) else 0
                champs.append((haut << 16) | bas)
            corps += struct.pack("<H", r.tag) + desc
            for c in champs:
                corps += struct.pack("<I", c)
            n_reecrits += 1
        else:
            corps += struct.pack("<H", r.tag) + r.desc
            for c in r.fields:
                corps += struct.pack("<I", c)
            n_intacts += 1

    d = bytearray(entete)
    struct.pack_into("<I", d, 0x00, len(t.records) + non_parses)
    struct.pack_into("<I", d, 0x04, len(corps) + len(t.trailing))
    neuf = bytes(d) + bytes(corps) + t.trailing
    rom.files[fid] = neuf
    if bavard:
        print(f"  encmons.bin : {n_reecrits} cartes portees a {capacite} especes "
              f"({n_champs} champs, {taille} o par enregistrement), "
              f"{n_intacts} enregistrements intacts")
        print(f"                {len(brut):,} -> {len(neuf):,} octets")
    return n_reecrits


if __name__ == "__main__":
    src, sortie = sys.argv[1], sys.argv[2]
    cap = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    agrandir(rom, cap)
    rom.saveToFile(sortie)
    manque = os.path.getsize(src) - os.path.getsize(sortie)
    if manque > 0:
        with open(sortie, "ab") as f:
            f.write(b"\xff" * manque)
    print(f"ecrit : {sortie} ({os.path.getsize(sortie):,} o)")
