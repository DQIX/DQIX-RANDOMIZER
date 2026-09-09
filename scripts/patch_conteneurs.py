#!/usr/bin/env python3
"""Greffe C : les conteneurs portent 150 especes au lieu des 12 de la liste.

A QUOI SERT CETTE GREFFE, ET A QUOI ELLE NE SERT PAS.

Au chargement d'une carte, les deux conteneurs sont batis DEPUIS la liste de
prechargement : ils portent donc exactement les 12 especes de la liste, et ne
brident rien. Ils ne deviennent un obstacle que pour la ROTATION -- la liste
change en cours de partie, les conteneurs non (ils sont batis par une machine a
etats qui ne tourne qu'au chargement de carte, mesure du 53). Une espece neuve
n'obtient alors pas son modele et le lot ne change pas : c'est exactement ce que
le joueur a constate sur v32.

Cette greffe fait donc porter aux conteneurs un pool LARGE des le chargement,
dans lequel la rotation puisera ensuite librement.

  ovl17 0x021B52C4   bl 0x209C0D0        -> bl greffe_C      (conteneur +0x2F8)
  ovl17 0x021B52E0   add r1, sp, #0x18   -> ldr r1, [sp, #0x18]
  ovl17 0x021B53C8   bl 0x209C0D0        -> bl greffe_C      (conteneur +0x304)
  ovl17 0x021B53DC   add r1, sp, #0x10   -> ldr r1, [sp, #0x10]

`0x0209C0D0` est `CopyList(liste, tampon) -> nombre`. On la remplace par une
greffe qui alloue 1 024 octets sur le tas de carte, y ecrit les identifiants
autorises par la table des classes, depose le pointeur dans le premier mot du
tampon local et rend le compte. Le second patch fait lire ce pointeur la ou le
code d'origine prenait l'adresse du tampon.

LE PLAFOND EST UNE NECESSITE, PAS UN CHOIX. `0x0206F348` alloue le bloc
d'enregistrements en une fois et abandonne proprement s'il echoue -- conteneur
vide, pas de plantage. Mais la suite duplique TROIS chaines par espece
(`0x020DA160`) et range le resultat SANS test de nullite : une exhaustion a ce
moment-la laisse un pointeur de chaine nul que le prechargeur passe a son
formateur. Mesure : 102 especes coutent 23 028 octets, soit 226 par espece, sur
les 40 912 du tas -- capacite reelle 181. On s'arrete a 150.

LA FENETRE EST EN RANG, PAS EN IDENTIFIANT. Il faut choisir 150 especes parmi
256 ; les prendre toujours dans le meme ordre condamnerait 106 especes a ne
jamais apparaitre -- c'etait le defaut de v27. On saute donc un nombre variable
d'especes avant de commencer. En RANG et non en identifiant parce que les
identifiants sont groupes : 256 especes sur la plage 0-334 avec de grands trous,
et une fenetre de 160 identifiants ne contient parfois que 26 especes (calcul
sur le pool reel).

LE DEPART VIENT DE L'IDENTIFIANT DE CARTE, ET C'EST VOLONTAIRE. Les deux
constructeurs doivent recevoir la MEME liste, sinon l'intersection des deux
conteneurs fond -- 150 x 150 / 256 = 88 especes, le defaut de conception de v33.
Un tirage au hasard imposerait de memoriser le rang entre les deux appels, soit
sept instructions qu'il n'y a pas. `[carte+0x00] & 0x7F` est stable pour toute
la duree d'une carte, donc identique pour les deux appels, et change d'une carte
a l'autre. Les 128 departs possibles couvrent bien les 256 rangs : un depart
>= 106 englobe le dernier.

Usage: python scripts/patch_conteneurs.py <rom.nds> <sortie.nds>
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capstone
import keystone
import ndspy.code
import ndspy.codeCompression as cc
import ndspy.rom
from patch_hasard import (BASE_ARM9, BORNE, C_ZONE, CARTE, COMPRESSED_END,
                          GREFFE_C, GREFFE_C2, GREFFE_C3, PATCHES_C, PLACES,
                          TABLE_CLASSES, assembler)

HEAP_ALLOC = 0x02032554          # SafeAllocator::Allocate(taille)
COPY_LIST = 0x0209C0D0           # CopyList(liste, tampon) -> nombre
OVL = 17
PLAFOND = 150                    # especes par conteneur, sur 181 possibles
MASQUE_DEPART = 0x7F             # departs possibles : 0 a 127
OCTETS_TAMPON = 1024             # 512 u16 ; 0x400 est un immediat encodable

# LES TAILLES DE TAS DU CONTEXTE DE TERRAIN.
#
# `func_ov017_021A02F0` lit une table `{identifiant, taille}` par pas de 8 en
# 0x021D6984 et place chaque handle en `ctx + 0x38 + id * 0x14`. Le conteneur 1
# vit sur l'identifiant 8, le conteneur 2 sur le 29 -- quatre exemplaires
# chacun, un par variante de carte.
#
# D'ORIGINE 11 392 et 1 024 OCTETS : le premier conteneur plafonnait alors a 16
# a 24 especes. Portes ici a 40 960 et 8 192, soit 181 et 290 especes.
#
# ON NE PEUT PAS MONTER PLUS HAUT. Les tas du contexte sont tailles dans
# l'ExpHeap parent 0x022A3200 (1 297 864 o) et il ne lui reste que 18 002 octets
# libres avec ces valeurs -- mesure sur la sauvegarde du joueur
# (scripts/lua/tas_conteneurs.lua). C'est ce qui fixe le plafond de 150.
#
# Ces tailles sont lues UNE SEULE FOIS, a la creation du contexte de terrain :
# les patcher en RAM apres avoir charge une sauvegarde arrive toujours trop tard.
TAILLES_TAS = {
    0x021D69A8: (8, 40960), 0x021D69B0: (9, 40960),
    0x021D69B8: (10, 40960), 0x021D69C0: (11, 40960),
    0x021D6A10: (29, 8192), 0x021D6A18: (30, 8192),
    0x021D6A20: (31, 8192), 0x021D6A28: (32, 8192),
}

# LE TAMPON DE NOM DU PRECHARGEUR : ESSAI ABANDONNE, ET POURQUOI.
#
# `0x021A29C0` formate le nom du fichier de modele par `sprintf("%s_f.mon")`
# dans un tampon a `sp+0x54`, qui n'a que 16 octets avant `sp+0x64` et `sp+0x68`
# -- deux arguments passes juste apres a `0x020D9548`. J'ai cru a un debordement
# et deplace le tampon a `sp+0x6C`, ou la fonction n'utilise apparemment rien.
#
# Le gel a change de place mais n'a pas disparu, et l'instrumentation de l'appel
# a tranche : le formateur n'est appele QU'UNE FOIS, avec un code parfaitement
# valide (« z016a », cinq caracteres). Il n'y a donc pas de debordement, et
# `sp+0x6C` n'est pas libre -- la structure passee par `add r0, sp, #0x64`
# s'etend au-dela de huit octets. Deplacer le tampon ne faisait que deplacer la
# corruption. On garde donc le code d'origine.
ATTENDU_OVL = {
    PATCHES_C[0][0]: "bl #0x209c0d0",
    PATCHES_C[0][1]: "add r1, sp, #0x18",
    PATCHES_C[1][0]: "bl #0x209c0d0",
    PATCHES_C[1][1]: "add r1, sp, #0x10",
}


def morceaux_c():
    """Rend {adresse: octets} pour les quatre morceaux de la greffe C.

    Entree  r0 = liste de prechargement (ignoree), r1 = adresse du tampon local.
    Sortie  r0 = nombre d'especes ; le pointeur du tampon est ecrit dans [r1].

    ELLE CHERCHE LA CARTE ELLE-MEME. La premiere version lisait `[r6+0x10]`, ce
    qui marche dans le premier constructeur -- ou r6 est la carte -- mais pas
    dans le second, ou r6 porte l'objet d'etat : la greffe y allouait depuis une
    adresse quelconque, echouait, et rendait 0, laissant le conteneur 2 vide.

    Le bitmap est lu OCTET PAR OCTET : un octet neuf tous les huit identifiants,
    decale d'un bit a chaque tour. C'est ce qui evite le decalage variable
    (`mov r1, r1, lsr ip`) et ses deux instructions de mise en place, dans une
    greffe ou il ne reste que quatre mots de marge.
    """
    m1, m2, m3, m4 = GREFFE_C, GREFFE_C2, GREFFE_C3, C_ZONE
    apres, fin = m4, m4 + 4 * 6
    c1 = assembler([
        "push {r4, r5, r6, r7, lr}",
        "mov r4, r1",                       # ou deposer le pointeur
        "bl #%d" % CARTE,
        "ldrh r6, [r0]",                    # identifiant de carte
        "ldr r0, [r0, #0x10]",              # le tas de carte
        "mov r1, #%d" % OCTETS_TAMPON,
        "bl #%d" % HEAP_ALLOC,
        "movs r5, r0",                      # curseur d'ecriture
        "popeq {r4, r5, r6, r7, pc}",       # echec : rend 0, conteneur vide
        "b #%d" % m2,
    ], m1)
    c2 = assembler([
        "str r5, [r4]",                     # le constructeur lira le tampon la
        "and r7, r6, #%d" % MASQUE_DEPART,  # especes a sauter avant la fenetre
        "ldr r2, [pc, #{L0}]",              # base de la table des classes
        "mov r6, #0",                       # identifiant courant
        "mov r0, #0",                       # nombre retenu
        "b #%d" % m3,
    ], m2, litteraux=(TABLE_CLASSES,))
    c3 = assembler([
        "tst r6, #7",                       # un octet neuf tous les 8 ids
        "ldrbeq r1, [r2], #1",
        "tst r1, #1",                       # l'espece est-elle autorisee ?
        "beq #%d" % apres,                  # non
        "subs r7, r7, #1",
        "bge #%d" % apres,                  # encore avant la fenetre
        "strh r6, [r5], #2",
        "add r0, r0, #1",
        "b #%d" % apres,
    ], m3)
    c4 = assembler([
        "mov r1, r1, lsr #1",               # bit suivant de l'octet
        "cmp r0, #%d" % PLAFOND,
        "beq #%d" % fin,
        "add r6, r6, #1",
        "cmp r6, #%d" % BORNE,
        "blt #%d" % m3,
        "pop {r4, r5, r6, r7, pc}",
    ], m4)
    return {m1: c1, m2: c2, m3: c3, m4: c4}


def bl(depuis, vers):
    d = (vers - (depuis + 8)) >> 2
    return struct.pack("<I", 0xEB000000 | (d & 0xFFFFFF))


def patcher(rom, bavard=True):
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_ARM)

    arm9 = bytearray(cc.decompress(bytes(rom.arm9))
                     if struct.unpack_from("<I", bytes(rom.arm9), COMPRESSED_END)[0]
                     else bytes(rom.arm9))
    morceaux = morceaux_c()
    for adr, code in morceaux.items():
        if len(code) > PLACES[adr]:
            raise SystemExit(f"greffe C a {adr:#010x} : {len(code)} o pour "
                             f"{PLACES[adr]} disponibles")
        o = adr - BASE_ARM9
        if any(arm9[o:o + len(code)]):
            raise SystemExit(f"{adr:#010x} n'est pas libre")
        arm9[o:o + len(code)] = code
    struct.pack_into("<I", arm9, COMPRESSED_END, 0)          # arm9 en clair
    rom.arm9 = bytes(arm9)

    # --- overlay 17 : rediriger les deux constructeurs, agrandir les tas ---
    ovl = rom.loadArm9Overlays()
    o17 = ovl[OVL]
    data = bytearray(o17.data)
    base = o17.ramAddress
    for adr, attendu in ATTENDU_OVL.items():
        i = adr - base
        ins = next(md.disasm(bytes(data[i:i + 4]), adr), None)
        lu = f"{ins.mnemonic} {ins.op_str}" if ins else "?"
        if lu != attendu:
            raise SystemExit(f"ovl17 {adr:#010x} : attendu {attendu!r}, lu {lu!r}")
    for appel, adr_tampon, decalage in PATCHES_C:
        data[appel - base:appel - base + 4] = bl(appel, GREFFE_C)
        neuf, _ = ks.asm("ldr r1, [sp, #%d]" % decalage, adr_tampon)
        data[adr_tampon - base:adr_tampon - base + 4] = bytes(neuf)
    # LE GARDE-FOU QUI MANQUAIT : verifier l'identifiant qui precede chaque
    # taille. Sans lui, un premier essai avait balaye la table au-dela de son
    # terminateur {0,0} et corrompu la paire voisine.
    for adr, (ident, taille) in TAILLES_TAS.items():
        i = adr - base
        lu = struct.unpack_from("<I", data, i - 4)[0]
        if lu != ident:
            raise SystemExit(f"ovl17 {adr - 4:#010x} : identifiant {lu} au lieu "
                             f"de {ident} -- la table a bouge")
        struct.pack_into("<I", data, i, taille)

    # L'overlay est compresse ; on le stocke en clair, comme l'ARM9.
    #
    # PIEGE : `Overlay.save()` rend les DONNEES de l'overlay, pas son entree de
    # table -- les joindre pour reconstruire `arm9OverlayTable` fabrique une
    # « table » de 11 Mo et fait echouer `rom.saveToFile` sur un IndexError.
    o17.data = bytes(data)
    o17.compressed = False
    o17.compressedSize = len(data)
    rom.files[o17.fileID] = bytes(data)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)

    if bavard:
        total = sum(len(c) for c in morceaux.values())
        print(f"  greffe C : {total} o en {len(morceaux)} morceaux, {PLAFOND} "
              f"especes par conteneur, {MASQUE_DEPART + 1} departs possibles")
        print("  ovl17    : deux constructeurs rediriges ; tas 8-11 a 40 960 o, "
              "29-32 a 8 192 o")
    return PLAFOND


if __name__ == "__main__":
    src, sortie = sys.argv[1], sys.argv[2]
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    patcher(rom)
    rom.saveToFile(sortie)
    manque = os.path.getsize(src) - os.path.getsize(sortie)
    if manque > 0:
        with open(sortie, "ab") as f:
            f.write(b"\xff" * manque)
    print(f"ecrit : {sortie} ({os.path.getsize(sortie):,} o)")
