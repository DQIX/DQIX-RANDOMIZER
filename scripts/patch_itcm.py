#!/usr/bin/env python3
"""De la place de code SURE, a adresse fixe : la queue de l'ITCM.

LE PROBLEME QU'ON RESOUT. Les bourrages a zero de l'ARM9 ne sont pas fiables. Le
canari du projet prouve qu'une region n'est pas ECRITE par le jeu -- il ne dit
rien sur le fait qu'elle soit LUE. Preuve mesuree : une seule greffe posee a
`0x020E7100`, en simple passe-plat, casse les textures de toutes les cartes sans
monstres (`work/dq9_D.nds` contre `work/dq9_B.nds`, identiques a cette greffe
pres). Les huit regions « validees par canari » du 9 septembre sont donc toutes
suspectes, et il ne restait que 48 octets prouves par le jeu pour un besoin de
220.

CE QU'ON UTILISE A LA PLACE. Mesure sur la liste d'autoload de l'ARM9 :

    bloc 0 : dest=01FF8000  taille=5952  bss=23360   -> fin 01FFF280
    ITCM   : 01FF8000..02000000, soit 32 768 octets
    => 3 456 octets a 01FFF280 que RIEN ne revendique

Ces octets ne sont ni dans l'image ARM9, ni couverts par les donnees du bloc, ni
par son BSS. Ni l'editeur de liens ni crt0 ne les touchent.

COMMENT ON Y MET DU CODE, SANS BOOTSTRAP. crt0 traite la liste d'autoload avant
de nettoyer le BSS statique : pour chaque bloc il recopie ses donnees vers
`dest`, puis met a zero les `bss` octets suivants. Il suffit donc d'agrandir le
bloc 0 :

    taille : 5952            -> 5952 + 23360 + N
    bss    : 23360           -> 0
    donnees: [5952 o d'origine] + [23360 zeros] + [notre code de N octets]

crt0 recopie le tout, le BSS du jeu se retrouve explicitement mis a zero comme
avant, et notre code atterrit a **0x01FFF280**, adresse fixe.

Aucun fichier ajoute, aucune allocation, aucun code relogeable, et pas
d'invalidation de cache a gerer : la recopie a lieu au demarrage, avant que quoi
que ce soit n'ait ete cherche depuis ces adresses.

DISPOSITION DE L'IMAGE APRES OPERATION. Les donnees d'autoload sont contigues a
partir de `autoload_start`, puis vient la liste :

    [bloc 0 : 29312 + N][bloc 1 : 96][liste : 24]

Donc `autoload_list_start` et `_end` de ModuleParams se decalent, et il faut les
reecrire. L'image grandit d'environ 23 Ko et sa queue tombe dans la plage que
crt0 met a zero -- sans consequence, la recopie a lieu avant.
"""

import struct

BASE_ARM9 = 0x02000000
MODULE_PARAMS = 0xBBC - 0x1C
ITCM_DEBUT = 0x01FF8000
ITCM_FIN = 0x02000000

# Ou notre code atterrit : juste apres les donnees et le BSS du bloc ITCM.
# Recalcule par `reserver`, mais fixe pour cette ROM.
ITCM_LIBRE = 0x01FFF280
ITCM_DISPO = ITCM_FIN - ITCM_LIBRE          # 3 456 octets


def lire_autoload(arm9):
    """Rend (liste_debut, liste_fin, donnees_debut, [(dest, taille, bss), ...])."""
    mp = MODULE_PARAMS
    ls = struct.unpack_from("<I", arm9, mp)[0] - BASE_ARM9
    le = struct.unpack_from("<I", arm9, mp + 4)[0] - BASE_ARM9
    ds = struct.unpack_from("<I", arm9, mp + 8)[0] - BASE_ARM9
    blocs = []
    for i in range((le - ls) // 12):
        blocs.append(struct.unpack_from("<III", arm9, ls + 12 * i))
    return ls, le, ds, blocs


def adresse_libre(arm9):
    """Rend l'adresse ITCM libre et sa taille, telles que la ROM les presente."""
    _, _, _, blocs = lire_autoload(arm9)
    for dest, taille, bss in blocs:
        if dest == ITCM_DEBUT:
            fin = dest + taille + bss
            return fin, ITCM_FIN - fin
    raise SystemExit("pas de bloc d'autoload vers l'ITCM")


def reserver(arm9, blob, bavard=True):
    """Agrandit le bloc ITCM pour y embarquer `blob`, et rend (arm9, adresse).

    `arm9` est l'image DECOMPRESSEE, en bytearray. Le blob est place a la fin de
    l'espace du bloc, donc a `dest + taille + bss` de la version d'origine.
    """
    ls, le, ds, blocs = lire_autoload(arm9)
    if len(blocs) < 1 or blocs[0][0] != ITCM_DEBUT:
        raise SystemExit("le premier bloc d'autoload ne vise pas l'ITCM")
    dest, taille, bss = blocs[0]
    adresse = dest + taille + bss
    if adresse + len(blob) > ITCM_FIN:
        raise SystemExit(f"blob de {len(blob)} o : l'ITCM n'en offre que "
                         f"{ITCM_FIN - adresse}")

    # les donnees des blocs, dans l'ordre de la liste
    donnees, pos = [], ds
    for _, t, _ in blocs:
        donnees.append(bytes(arm9[pos:pos + t]))
        pos += t
    if pos != ls:
        # La liste doit suivre immediatement les donnees ; si ce n'est pas le cas
        # la disposition n'est pas celle qu'on croit et il faut s'arreter.
        raise SystemExit(f"disposition inattendue : donnees finissent a "
                         f"{BASE_ARM9 + pos:#010x}, liste a {BASE_ARM9 + ls:#010x}")

    # bloc 0 : donnees + BSS explicite + notre blob, et plus de BSS
    neuf0 = donnees[0] + bytes(bss) + bytes(blob)
    blocs_neufs = [(dest, len(neuf0), 0)] + list(blocs[1:])
    donnees_neuves = [neuf0] + donnees[1:]

    corps = b"".join(donnees_neuves)
    liste = b"".join(struct.pack("<III", *b) for b in blocs_neufs)
    arm9 = bytearray(arm9[:ds]) + corps + liste

    # ModuleParams : la liste s'est deplacee
    nls = BASE_ARM9 + ds + len(corps)
    struct.pack_into("<I", arm9, MODULE_PARAMS, nls)
    struct.pack_into("<I", arm9, MODULE_PARAMS + 4, nls + len(liste))

    if bavard:
        print(f"  itcm     : {len(blob)} o a {adresse:#010x} "
              f"({ITCM_FIN - adresse - len(blob)} o encore libres)")
        print(f"  autoload : bloc ITCM {taille} -> {len(neuf0)} o, bss {bss} -> 0 ; "
              f"image {len(arm9):,} o")
    return arm9, adresse
