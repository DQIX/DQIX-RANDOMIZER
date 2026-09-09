#!/usr/bin/env python3
"""Reconstruit `encfld.bin` et `encmons.bin` DE FACON COHERENTE.

CE QUE CE SCRIPT REMPLACE, ET POURQUOI. Les scripts precedents agrandissaient
`encfld.bin` puis `encmons.bin` independamment. C'etait faux pour trois raisons,
etablies par desassemblage (voir `work/re/RAPPORT.md` et docs/FORMAT.md §24) :

1. Le conteneur RAM d'`encfld.bin` n'a que **6 emplacements par groupe** : un
   slot de 32 octets alloue par `AddGroup` (`0x0209BD50`, `lsl r4, r0, #5` puis
   `memset` de 0x20), soit 8 octets d'en-tete et 6 entrees de 4 octets.
   `AddEntry` (`0x0209BE54`) ecrit le compteur sans aucun controle de borne :
   les entrees 7 et suivantes debordent dans le slot du groupe suivant, que le
   prochain `AddGroup` remet a zero. Declarer 24 entrees ne conserve donc que
   les 6 premieres, et corrompt le voisin au passage.

2. **Une espece ne peut apparaitre que si elle figure dans `encmons.bin`.** Le
   test est un `return 0` sec dans le code de spawn (`0x021A2128`, overlay 17) :
   il verifie l'espece contre les collections de modeles de la carte, construites
   uniquement depuis cette liste. Le plafond code est 12 (`cmp r3, #0xc` a
   `0x0209C0A0`), alors que le fichier n'en fournit que 6 au plus.

3. Le jeu maintient un **invariant** que le vanilla respecte sur 208 cartes sur
   208 : l'union des especes des groupes d'une zone est incluse dans la liste
   `encmons` de la carte. Randomiser les deux fichiers separement le casse, et
   c'est la seule explication necessaire a l'absence d'effet de tout le travail
   precedent.

LA STRATEGIE RETENUE. Par zone, on choisit un ensemble de N especes (N <= 10,
voir plus bas), on le repartit en groupes de 6 au plus, et on ecrit ce meme
ensemble dans `encmons.bin`. L'invariant est rebati par construction.

POURQUOI N <= 10 ET PAS 12. L'overlay 17 (`0x021B4EC4`-`0x021B4F08`) ajoute 1 a
4 especes codees en dur apres la lecture du fichier. Si la liste est deja pleine
a 12, ces ajouts sont perdus en silence. On s'arrete donc a 8 ou 10.

POURQUOI PLUSIEURS GROUPES DEVIENNENT UTILES. Les parametres de groupe (tag
0x66) portent un predicat d'eligibilite : bits 0-2 = predicat jour/nuit,
bits 13-20 = masque, bits 21-24 = cadence d'apparition. En mettant le predicat a
2 (« toujours ») et le masque a 0 (« toujours eligible »), tous les groupes d'une
zone deviennent tirables a tout moment. `0x02073ED4` en choisit un au hasard a
chaque apparition, donc l'ensemble des especes de la zone devient accessible en
permanence -- au lieu d'un seul groupe fige.

DEUX PIEGES A NE JAMAIS REFAIRE :
  - le **champ 1** d'un enregistrement `encmons` n'est pas un emplacement libre,
    c'est une porte de position : un contenu non nul desactive tout
    l'enregistrement. C'est ce que j'avais ecrase, et c'est pourquoi plus aucun
    monstre n'apparaissait nulle part.
  - un zero dans les champs 2..N est **saute**, pas terminateur. Une liste
    partiellement remplie est donc legitime.

Usage: python scripts/resync_zones.py <rom.nds> <sortie.nds> <graine> [n_especes]
"""
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ndspy.rom
from agrandir_zones import construire_pool, construire_rarete
from montable import TableMonstres
from prmtable import PrmTable

CHEMIN_FLD = "data/prm/encfld.bin"
CHEMIN_MONS = "data/prm/encmons.bin"

ENTREES_PAR_GROUPE = 6      # taille du slot RAM : 32 o = 8 + 6 x 4
GROUPES_MAX = 6             # plafond code a 0x0209BD60
ESPECES_DEFAUT = 8          # <= 10, pour laisser place aux ajouts codes en dur


def descripteur(n):
    """Descripteur et taille d'un enregistrement a n champs u32."""
    bits = 0
    for i in range(n):
        bits |= 1 << (2 * i)
    n_type = -(-2 * n // 8)
    octets = bytes([(bits >> (8 * k)) & 0xFF for k in range(n_type)])
    desc = bytes([n]) + octets
    total = -(-(2 + len(desc)) // 4) * 4
    return desc + b"\xff" * (total - 2 - len(desc)), total + 4 * n


def params_toujours_eligible(v):
    """Rend les parametres de groupe rendus inconditionnels.

    bits 0-2   predicat d'eligibilite -> 2 (toujours)
    bits 13-20 masque                 -> 0 (toujours eligible)
    bits 21-24 cadence d'apparition   -> conservee
    """
    v = (v & ~0x7) | 2
    v = v & ~(0xFF << 13)
    return v


def lire_zones(rom):
    """Rend [(champs du tag 0x69, [(params, [ids])])] dans l'ordre du fichier."""
    p = PrmTable(bytes(rom.files[rom.filenames.idOf(CHEMIN_FLD)]))
    zones, zone, groupe = [], None, None
    for r in p.records:
        if r.tag == 0x69:
            zone = {"entete": r, "groupes": []}
            zones.append(zone)
        elif r.tag == 0x68 and len(r.fields) == 1 and zone is not None:
            groupe = {"cle": r, "params": None, "ids": []}
            zone["groupes"].append(groupe)
        elif r.tag == 0x66 and len(r.fields) == 1 and groupe is not None:
            groupe["params"] = r
        elif r.tag == 0x67 and len(r.fields) == 2 and groupe is not None:
            groupe["ids"].append(r.fields[0] & 0xFFF)
    return zones, p


def reconstruire(rom, rng, n_especes=ESPECES_DEFAUT, bavard=True):
    pool, _boss = construire_pool_racine(rom)
    rarete = construire_rarete()
    zones, p_fld = lire_zones(rom)

    # --- 1. choisir l'ensemble d'especes de chaque zone ---
    ens = {}
    for z in zones:
        carte = z["entete"].fields[0]
        deja = []
        for g in z["groupes"]:
            for i in g["ids"]:
                if i and i not in deja:
                    deja.append(i)
        manque = [i for i in pool if i not in deja]
        rng.shuffle(manque)
        liste = (deja + manque)[:n_especes]
        ens[carte] = liste

    # --- 2. reecrire encfld.bin ---
    desc67 = next(r.desc for r in p_fld.records
                  if r.tag == 0x67 and len(r.fields) == 2)
    desc66 = next(r.desc for r in p_fld.records
                  if r.tag == 0x66 and len(r.fields) == 1)
    corps = bytearray()

    def ecrire(tag, desc, champs):
        corps.extend(struct.pack("<H", tag) + desc)
        for c in champs:
            corps.extend(struct.pack("<I", c & 0xFFFFFFFF))

    n_groupes_ecrits = 0
    for z in zones:
        carte = z["entete"].fields[0]
        liste = ens[carte]
        ecrire(z["entete"].tag, z["entete"].desc, z["entete"].fields)
        modele = z["groupes"][0] if z["groupes"] else None
        if modele is None:
            continue
        # on repartit la liste en groupes de 6 au plus, en gardant les groupes
        # existants comme gabarits pour leurs cles et leurs parametres
        n_grp = min(GROUPES_MAX,
                    max(1, -(-len(liste) // ENTREES_PAR_GROUPE)))
        for k in range(n_grp):
            gab = z["groupes"][k] if k < len(z["groupes"]) else modele
            cle = gab["cle"].fields[0] if k < len(z["groupes"]) else \
                modele["cle"].fields[0] + 1000 + k
            ecrire(0x68, gab["cle"].desc, [cle])
            if gab["params"] is not None:
                ecrire(0x66, desc66,
                       [params_toujours_eligible(gab["params"].fields[0])])
            # 6 especes prises dans la liste, en tournant pour couvrir le tout
            for j in range(ENTREES_PAR_GROUPE):
                esp = liste[(k * ENTREES_PAR_GROUPE + j) % len(liste)]
                ecrire(0x67, desc67,
                       [(rarete.get(esp, 4) << 12) | esp, 1])
            n_groupes_ecrits += 1

    d = bytearray(bytes(rom.files[rom.filenames.idOf(CHEMIN_FLD)])[:p_fld.body])
    nb_total = n_groupes_ecrits * 2 + len(zones) \
        + n_groupes_ecrits * ENTREES_PAR_GROUPE \
        + (p_fld.nb - len(p_fld.records))
    struct.pack_into("<I", d, 0x00, nb_total)
    struct.pack_into("<I", d, 0x04, len(corps) + len(p_fld.trailing))
    rom.files[rom.filenames.idOf(CHEMIN_FLD)] = \
        bytes(d) + bytes(corps) + p_fld.trailing

    # --- 3. reecrire encmons.bin avec EXACTEMENT ces ensembles ---
    fid = rom.filenames.idOf(CHEMIN_MONS)
    brut = bytes(rom.files[fid])
    t = PrmTable(brut)
    n_paires = -(-n_especes // 2)
    n_champs = 2 + n_paires
    desc, _taille = descripteur(n_champs)
    corps2 = bytearray()
    n_maj = n_intact = 0
    for r in t.records:
        liste = ens.get(r.fields[0]) if r.tag == 0x66 and r.fields else None
        standard = r.desc.hex() in ("0315", "0455", "055501ffffff")
        if liste and standard:
            # champ 0 = carte, champ 1 = PORTE DE POSITION, a laisser a 0
            champs = [r.fields[0], 0]
            for k in range(n_paires):
                bas = liste[2 * k] if 2 * k < len(liste) else 0
                haut = liste[2 * k + 1] if 2 * k + 1 < len(liste) else 0
                champs.append((haut << 16) | bas)
            corps2.extend(struct.pack("<H", r.tag) + desc)
            for c in champs:
                corps2.extend(struct.pack("<I", c))
            n_maj += 1
        else:
            corps2.extend(struct.pack("<H", r.tag) + r.desc)
            for c in r.fields:
                corps2.extend(struct.pack("<I", c))
            n_intact += 1
    d2 = bytearray(brut[:t.body])
    struct.pack_into("<I", d2, 0x00, len(t.records) + (t.nb - len(t.records)))
    struct.pack_into("<I", d2, 0x04, len(corps2) + len(t.trailing))
    rom.files[fid] = bytes(d2) + bytes(corps2) + t.trailing

    if bavard:
        print(f"  encfld  : {len(zones)} zones, {n_groupes_ecrits} groupes de "
              f"{ENTREES_PAR_GROUPE} entrees, tous rendus toujours eligibles")
        print(f"  encmons : {n_maj} cartes portees a {n_especes} especes "
              f"({n_champs} champs), {n_intact} intactes")
    return len(zones), n_groupes_ecrits


def construire_pool_racine(rom):
    """Le pool doit venir du VANILLA, pas de la ROM en cours de modification."""
    import glob
    return construire_pool(
        glob.glob("Dragon Quest IX*.nds")[0])


if __name__ == "__main__":
    src, sortie = sys.argv[1], sys.argv[2]
    rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 0)
    n = int(sys.argv[4]) if len(sys.argv) > 4 else ESPECES_DEFAUT
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    reconstruire(rom, rng, n)
    rom.saveToFile(sortie)
    manque = os.path.getsize(src) - os.path.getsize(sortie)
    if manque > 0:
        with open(sortie, "ab") as f:
            f.write(b"\xff" * manque)
    print(f"ecrit : {sortie} ({os.path.getsize(sortie):,} o)")
