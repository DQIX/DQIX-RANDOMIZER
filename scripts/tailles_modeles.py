#!/usr/bin/env python3
"""Mesure ce que coute le modele de terrain de chaque espece, en RAM principale.

POURQUOI. Le tas des modeles d'une carte tient environ 8 modeles. A 10 ou 12
especes par zone, certains modeles ne se chargent pas et le monstre apparait
sans modele -- invisible (docs/research/RESEARCH.md 36). Mais toutes les especes ne coutent
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

from source_rom import lire as lire_rom

# L'ARCHIVE VIENT DE LA ROM, plus de `work/extracted`. Elle pesait 23 Mo
# extraits a la main, que le joueur d'une application n'aura jamais ; le
# lecteur NitroFS la sort de la ROM pour le meme resultat, temoin a l'appui
# (`python scripts/source_rom.py`).
ARCHIVE = "data/pack_lv5/enemy.gp2"


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


def mesurer(rom=None):
    g = GP2(ARCHIVE, donnees=lire_rom(ARCHIVE, rom))
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


def taille_mon(d):
    """Poids d'un `<code>.mon` COMPLET (celui du combat) : chaque membre du
    NARC decompresse s'il est en LZ77 (`entete >> 8`), brut sinon."""
    tot = 0
    for _nom, (a, b) in fichiers_narc(d).items():
        h = struct.unpack_from("<I", d, a)[0] if b - a >= 4 else 0
        tot += (h >> 8) if (h & 0xFF) == 0x10 else (b - a)
    return tot


_combat = {}
_modeles = {}
_declarees = {}

# LES ESPECES QU'UNE AUTRE AMENE DANS LE COMBAT : leurs modeles sont charges
# avec elle, APRES les especes du combat (coupees les premieres si la place
# manque : le renfort ne vient pas, rien ne gele). Deux sources, overlay 0 :
#  - la table de 4 x 16 o en 0x02183070, lue en 0x0216571C (75, 77) ;
#  - les APPELS DE RENFORT du kit de l'espece (0x0216564C : chaque action de
#    type 0xC est cherchee dans la table action -> espece de 0x02182E6C,
#    lue par 0x0215FB54), releves sur les kits du jeu d'origine (ZER-110,
#    29/10 : Monte-gluancien amenait 180, vu au banc). Un renfort tire par
#    les options d'actions n'est pas compte : au pire il ne vient pas.
SUPPLEMENTS = {43: (35,), 64: (128,), 75: (15, 3), 77: (19, 27), 78: (145,),
               79: (146,), 119: (15,), 120: (17,), 121: (19,), 225: (180,),
               266: (179,), 267: (75,), 298: (19,)}


MARGE_NULLE = 1.3


def tailles_declarees(rom=None):
    """{IDENTIFIANT d'espece: taille de modele DECLAREE, en Ko}, le champ
    +0x2A de sa fiche de `mon_btldata` (meme rang que `mon_moddata`).

    C'EST CE QUE LE COMBAT COMPTE (ZER-110, research §108) : avant de charger
    ses modeles, un combat scripte soustrait, espece par espece, cette taille
    x 1024 de la place libre de son tas (overlay 0, 0x02165C54) et coupe la
    liste a la premiere qui ne tient pas. Les fichiers reels n'y sont pour
    rien.

    SAUF UNE TAILLE DECLAREE NULLE (Nokturnus et 769-775) : le combat ne la
    compte pas, mais le modele se charge quand meme (Nokturnus : 98 Ko
    reels). Monte-gluancien + Larstastnaras + Nokturnus, 150 Ko declares :
    ECRAN NOIR au chargement (joueur, 29/10). Partout ailleurs la taille
    declaree depasse la reelle (de 3 a 26 Ko, x1,25 au plus) : une taille
    nulle est remplacee par la reelle x MARGE_NULLE, pour NOTRE compte."""
    if rom in _declarees:
        return _declarees[rom]
    btl = lire_rom("data/prm/mon_btldata.nat", rom)
    mod = lire_rom("data/prm/mon_moddata.nat", rom)
    n = struct.unpack_from("<I", mod, 0)[0]
    out = {}
    for i in range(n):
        ident = struct.unpack_from("<H", mod, 4 + i * 64)[0]
        out.setdefault(ident, struct.unpack_from("<H", btl,
                                                 4 + i * 132 + 0x2A)[0])
    reelles = tailles_combat(rom)
    for e, ko in out.items():
        if ko == 0 and reelles.get(e):
            out[e] = -(-int(reelles[e] * MARGE_NULLE) // 1024)
    _declarees[rom] = out
    return out


def modeles_combat(rom=None):
    """{IDENTIFIANT d'espece: code du `.mon` qu'elle charge en combat}. Deux
    especes au meme code (deux decarions, une variante sans `.mon` a elle)
    ne chargent le modele qu'UNE fois (ZER-110)."""
    tailles_combat(rom)
    return _modeles[rom]


def tailles_combat(rom=None):
    """{IDENTIFIANT d'espece: poids du modele EN COMBAT}, boss compris (ZER-104).

    LE COMBAT A SON TAS. Un combat scripte trop lourd n'affiche que ses
    premiers emplacements, sans gel : hypothermiasme / Barbarus / vampivolle
    (202 Ko) n'a montre que l'hypothermiasme, gluant / Barbarus / gluante
    (131 Ko) les trois (joueur, 27/10/2026). Le poids d'un combat compte
    chaque modele une fois (`modeles_combat`, `escortes.poids`) : le plus
    lourd du vanilla pese 116 232 o (l'archer vert du rang 97 a un nombre 0,
    ZER-110)."""
    if rom in _combat:
        return _combat[rom]
    from montable import ids_par_index
    from rom_vanilla import chemin_vanilla
    g = GP2(ARCHIVE, donnees=lire_rom(ARCHIVE, rom))
    par_code = {}
    entrees = sorted(g.entrees, key=lambda e: e[1] & 0xFFFFFF)
    for i, (_h, offs, taille) in enumerate(entrees):
        nom = g.noms[i] if i < len(g.noms) else None
        if not nom or not nom.endswith(".mon") or nom.endswith("_f.mon"):
            continue
        pos = g.first_file * 4 + (offs & 0xFFFFFF) * 4
        try:
            par_code[nom[:-4]] = taille_mon(g.d[pos:pos + taille])
        except Exception:
            pass
    chemin = rom or chemin_vanilla()
    noms = charger(chemin, "fr")
    out, modeles = {}, {}
    for r, ident in enumerate(ids_par_index(chemin)):
        try:
            f = noms[r]
        except (KeyError, IndexError):
            continue
        code = f.get("modele") if isinstance(f, dict) else None
        if not code:
            continue
        n = par_code.get(code)
        if n is None and code[-1:].isalpha() and code[-1] != "a":
            code = code[:-1] + "a"
            n = par_code.get(code)
        if n:
            out[ident] = n
            modeles[ident] = code
    _combat[rom] = out
    _modeles[rom] = modeles
    return out


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

    from rom_vanilla import chemin_vanilla
    rom = chemin_vanilla()
    table, _ = TableMonstres.depuis_rom(rom)
    noms = charger(rom, "fr")
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
