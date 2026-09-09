#!/usr/bin/env python3
"""Mesure ce que coute le modele de terrain de chaque espece, en RAM principale.

POURQUOI. Le tas des modeles d'une carte tient environ 8 modeles. A 10 ou 12
especes par zone, certains modeles ne se chargent pas et le monstre apparait
sans modele -- invisible (docs/FORMAT.md 36). Mais toutes les especes ne coutent
pas la meme chose : de 5,5 Kio a 61 Kio. En ecartant les plus gros modeles du
tirage, on doit pouvoir tenir 10 ou 12 especes la ou 10 quelconques echouaient.

LA CHAINE. `data/pack_lv5/enemy.gp2` porte 601 membres nommes `<code>.mon`
(version complete) et `<code>_f.mon` (version terrain, celle du prechargeur, qui
construit son nom par `sprintf("%s_f.mon")`). Ces membres ne sont PAS compresses
au niveau GPC2 : chacun est une archive NARC Nitro. Dans le NARC, les fichiers
`.cchr` et `.cmot` sont, eux, compresses en LZ77 -- et la taille decompressee est
lisible dans l'en-tete, sans rien decompresser : `entete >> 8`.

Ce qui occupe la RAM principale est le `.cchr` decompresse. C'est ce qu'on
mesure. Les versions terrain n'ont jamais de `.cmot`.

Usage: python scripts/tailles_modeles.py [seuil_en_octets]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gp2 import GP2
from montable import TableMonstres
from monnames import charger

ROM = "Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds"
ARCHIVE = "work/extracted/data/pack_lv5/enemy.gp2"


def fichiers_narc(d):
    """Rend {nom: (debut, fin)} des fichiers d'une archive NARC Nitro."""
    if d[:4] != b"NARC":
        raise ValueError("pas une archive NARC")
    n_blocs = struct.unpack_from("<H", d, 14)[0]
    pos = struct.unpack_from("<H", d, 12)[0]
    fat, noms, img = None, None, None
    for _ in range(n_blocs):
        magie = d[pos:pos + 4]
        taille = struct.unpack_from("<I", d, pos + 4)[0]
        if magie == b"BTAF":
            nb = struct.unpack_from("<H", d, pos + 8)[0]
            fat = [struct.unpack_from("<II", d, pos + 12 + i * 8)
                   for i in range(nb)]
        elif magie == b"BTNF":
            noms = (pos + 8, d[pos:pos + taille])
        elif magie == b"GMIF":
            img = pos + 8
        pos += taille
    if fat is None or img is None:
        raise ValueError("archive NARC incomplete")

    # Table de noms : en-tete de 8 octets par repertoire, puis des entrees
    # { u8 longueur, chaine }. Une seule racine ici, sans sous-repertoire.
    out = {}
    if noms:
        base, bloc = noms
        deb = struct.unpack_from("<I", bloc, 8)[0]
        p = 8 + deb
        i = 0
        while p < len(bloc) and i < len(fat):
            lg = bloc[p]
            if lg == 0:
                break
            nom = bloc[p + 1:p + 1 + lg].decode("ascii", "replace")
            out[nom] = (img + fat[i][0], img + fat[i][1])
            p += 1 + lg
            i += 1
    if not out:            # pas de noms : on indexe par position
        out = {str(i): (img + a, img + b) for i, (a, b) in enumerate(fat)}
    return out


def taille_cchr(d):
    """Taille du `.cchr` decompresse, lue dans l'en-tete LZ77 (`mot >> 8`)."""
    for nom, (a, b) in fichiers_narc(d).items():
        if ".cchr" in nom:
            entete = struct.unpack_from("<I", d, a)[0]
            if entete & 0xFF != 0x10:
                return None, nom      # pas du LZ77 : on ne sait pas
            return entete >> 8, nom
    return None, None


def mesurer():
    g = GP2(ARCHIVE)
    brut = g.d
    par_code = {}
    # La table de noms suit l'ordre des entrees TRIEES PAR OFFSET MASQUE, pas
    # l'ordre brut de l'index. Apparier sans trier ne rend aucun `_f.mon`.
    entrees = sorted(g.entrees, key=lambda e: e[1] & 0xFFFFFF)
    for i, (h, offs, taille) in enumerate(entrees):
        nom = g.noms[i] if i < len(g.noms) else None
        if not nom or not nom.endswith("_f.mon"):
            continue
        pos = g.first_file * 4 + (offs & 0xFFFFFF) * 4
        # PAS de u32 de controle ici : les membres d'enemy.gp2 ne sont pas
        # compresses au niveau GPC2 (bit 0x10000000 de totalFileSize), l'archive
        # NARC commence directement a `pos`. Les 4 octets de l'ecart entre deux
        # membres consecutifs sont du bourrage APRES, pas un en-tete avant.
        d = brut[pos:pos + taille]
        try:
            n, _ = taille_cchr(d)
        except Exception:
            n = None
        if n:
            par_code[nom[:-6]] = n
    return par_code


if __name__ == "__main__":
    seuil = int(sys.argv[1]) if len(sys.argv) > 1 else None
    par_code = mesurer()
    print(f"{len(par_code)} modeles de terrain mesures")
    t = sorted(par_code.values())
    print(f"  .cchr decompresse : min {t[0]:,}  med {t[len(t)//2]:,}  "
          f"moy {sum(t)//len(t):,}  max {t[-1]:,}")
    for label, borne in (("<= 8 Kio", 8192), ("<= 16 Kio", 16384),
                         ("<= 24 Kio", 24576), ("<= 32 Kio", 32768)):
        print(f"  {label:<10s} : {sum(1 for x in t if x <= borne):3d} modeles")

    table, _ = TableMonstres.depuis_rom(ROM)
    noms = charger(ROM, "fr")
    lignes = []
    for i, m in enumerate(table):
        code = noms[i]["modele"]
        n = par_code.get(code)
        if n:
            lignes.append((m.id, code, n, noms[i]["nom"]))
    print(f"\n{len(lignes)} especes rattachees a un modele de terrain")
    lignes.sort(key=lambda x: -x[2])
    print("  les 8 plus gros :")
    for i, c, n, nm in lignes[:8]:
        print(f"     {n:7,} o  id {i:3d}  {c:<8s} {nm}")
    print("  les 5 plus petits :")
    for i, c, n, nm in lignes[-5:]:
        print(f"     {n:7,} o  id {i:3d}  {c:<8s} {nm}")

    with open("work/tailles_modeles.txt", "w", encoding="utf-8") as f:
        f.write("# id\tcode\ttaille_cchr\tnom\n")
        for i, c, n, nm in sorted(lignes):
            f.write(f"{i}\t{c}\t{n}\t{nm}\n")
    print("\necrit : work/tailles_modeles.txt")
    if seuil:
        gard = [x for x in lignes if x[2] <= seuil]
        print(f"avec un seuil de {seuil:,} o : {len(gard)} especes retenues")
