#!/usr/bin/env python3
"""P3/P4 -- le portier universel, la table source, et l'emprunt de modele.

OBJECTIF. Que N'IMPORTE QUELLE espece du bestiaire puisse apparaitre a CHAQUE
apparition. Le combat est juste, l'echelle et la hitbox sont justes ; seule
l'apparence du symbole sur la carte reste empruntee a un modele deja charge --
c'est la derniere piece, et elle a maintenant tout ce qu'il lui faut.

LES TROIS VERROUS, ET CE QU'ON EN FAIT

1. LE PORTIER. L'apparition (0x021A2128) exige l'espece dans les DEUX conteneurs
   de la carte : `carte+0x2F8` (tableau d'enregistrements de 0x1C, recherche
   0x0206F500) et `carte+0x304` (liste chainee, recherche 0x0206EF28). Une espece
   absente est rejetee et le jeu reessaie en boucle -- 3 629 appels contre 2,
   mesure de FORMAT.md 20. Les conteneurs ne portent que les especes declarees
   par la zone.

   On ne les remplit pas : le constructeur 0x0206F240 indexe un tableau de douze
   octets et corrompt tout au-dela (FORMAT.md 64, greffe C retiree).

2. LA TABLE SOURCE, ET C'EST LE JEU QUI LA DONNE. `0x0206EFE8(contexte, tas)` lit
   `data/prm/mon_data.gp2` et batit la table des 438 monstres SUR LE TAS QU'ON
   VEUT, au format que la recherche generique du jeu comprend deja -- pas 0x1C,
   espece en +0x08, code de modele en +0x04, echelle en +0x12. `talon_source` la
   batit sur le tas des modeles a chaque montage, juste avant le prechargeur, ou
   patch_place a laisse 50 a 92 Ko libres.

   Mesure : SRC = {438, bloc}, especes croissantes, codes `z000a`, `z058a`,
   `z034a`, echelles 4096 (1.0) a 13926 (3.4x pour le geant, espece 217).

   Le portier cherche donc l'espece dans le conteneur de la carte, sinon dans
   cette table, et rend l'enregistrement REEL. Pas de synthese, pas de gabarit,
   pas d'enregistrement statique partage : la version precedente recopiait le
   premier enregistrement de la zone et n'ecrasait que l'espece, ce qui donnait
   une echelle et des champs approches -- d'ou la hitbox qui ne correspondait pas
   au symbole, defaut rapporte par le joueur.

3. LE MODELE. `FindLoadedModel` (0x021A2738) rend 0 quand le modele de l'espece
   n'est pas charge, et l'apparition cree alors un acteur SANS modele : le
   monstre invisible (FORMAT.md 36). On intercale une fonction qui, sur echec,
   rend un modele deja charge tire au hasard parmi les emplacements 7 a 18.
   L'apparence est empruntee, mais l'espece de l'acteur -- donc le combat, la
   taille et la hitbox -- reste celle qui a ete tiree.

   Le partage est sans risque : le jeu attache deja la meme fiche a tous les
   acteurs d'une meme espece, plusieurs a l'ecran en meme temps.

ON NE PATCHE QUE LES SITES D'APPEL, PAS LES FONCTIONS.
`0x0206F500` a vingt appelants dans tout le jeu (combat, overlays 21E/21F) : la
remplacer ferait rendre un enregistrement la ou l'appelant attend un zero. On
redirige les quatre `bl` du chemin d'apparition, et eux seuls.

ET SURTOUT PAS CEUX DU PRECHARGEUR (0x021A2988, 0x021A299C). Si le portier lui
repondait toujours oui, il chargerait le modele d'especes que la zone ne declare
pas et gacherait le tas. Il garde son comportement d'origine, et c'est parmi ses
modeles que l'apparition emprunte -- jusqu'a ce que le chargement a la demande
prenne le relais.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import capstone
import ndspy.code
import ndspy.codeCompression as cc

from patch_hasard import (assembler, bl, BASE_ARM9, ZONE_LIBRE, GREFFE_A2,
                          GREFFE_B, TAILLE_TIREUR, ROT_B, GREFFE_C, GREFFE_C2,
                          RAND, TABLE_EMPL, EMPL_MODELES, EMPLACEMENTS,
                          MODE_RENDRE, COMPRESSED_END, OVL)

# --- les fonctions du jeu qu'on rappelle ---
RECH_GENERIQUE = 0x0206F480       # BinarySearch(conteneur, cle, extracteur)
# LE CADEAU DU JEU : un chargeur de la table source en UN appel.
#   0206efe8  ldr r0, [pc]   ; "data/prm/mon_data.gp2"
#   0206f004  bl 0x207569c   ; lit le fichier -> blob
#   0206f018  bl 0x206f02c   ; construit {compte, bloc} SUR LE TAS DONNE
# Signature : 0x0206EFE8(contexte, tas). Le format produit est celui que la
# recherche generique comprend deja -- `0x0206F108` calcule la taille comme
# `0x1C * (mot0 & 0xFFFFF)`, donc pas 0x1C, espece en +0x08, code de modele en
# +0x04. On la batit sur le tas des modeles, qui a 50 a 92 Ko libres depuis
# patch_place, et le portier rend alors l'enregistrement REEL de l'espece :
# bon code de modele, bonne echelle, bons champs -- donc bonne hitbox.
CHARGE_SOURCE = 0x0206EFE8        # (contexte, tas) -> batit la table des 438
# LE SEUIL SE MESURE, IL NE SE DEVINE PAS. Premiere valeur : 0x18000 (98 304),
# choisie sur l'idee « une ville a un petit tas ». Faux : l'EGLISE a un tas de
# 171 424 octets, donc elle passait pour du terrain, on y batissait la table et
# on y bornait la confiscation -- textures etirees, symptome rapporte deux fois.
# Tailles mesurees : ville 62 280, eglise 171 424, terrain 188 384. Le seuil est
# donc place entre les deux dernieres. 0x2C000 est un immediat ARM encodable.
#
# C'EST UNE HEURISTIQUE, PAS UN PRINCIPE. Le bon critere est « la liste de
# prechargement est-elle vide », mais il coute une quinzaine d'instructions
# qu'on n'a pas (69). A remplacer des qu'on aura de la place -- le bootstrap BSS.
SEUIL_TERRAIN = 0x2C000           # au-dela, la carte porte des monstres
PRECHARGEUR = 0x021A28A8          # appele par le montage en 0x021A30FC
GET_CTX_TERRAIN = 0x021D82E4      # [ce mot] = le contexte de terrain
EXTRACTEUR = 0x0206EF50           # `ldrsh r0, [r0, #8]` : la cle d'un enreg.
TROUVE_MODELE = 0x021A2738        # FindLoadedModel(?, espece) -> fiche ou 0
TAILLE_ENREG = 0x1C               # un enregistrement du conteneur 1
SUIVANT = 0x10                    # champ « suivant » d'un noeud du conteneur 2

# --- ou loge notre code, dans du bourrage a zero deja valide par canari ---
# La zone de 280 octets porte le bitmap (48 o en +0x00) et la greffe A2 (144 o
# en +0x30) : il reste 88 octets en +0xC0. Les autres regions sont celles que le
# retrait de la greffe C et de la rotation a liberees.
F1 = ZONE_LIBRE + 0xC0            # 88 o : le portier du conteneur 1
F2 = ROT_B                        # 72 o : le portier du conteneur 2
# LES TROIS MORCEAUX DE L'EMPRUNT. Ils remplissent exactement les 72 octets de
# la region du tireur non pris par talon_source, plus la queue de la region du
# portier 1. Ordre non contigu : c'est la taille des trous qui commande, les
# branchements sont resolus par etiquettes.
TROUVE = GREFFE_B + 8             # 32 o : morceau 1
EMP3 = GREFFE_B + 8 + 32          # 40 o : morceau 3
# SEIZE octets, pas huit : le contexte porte un troisieme mot en +0x08, le bloc
# des chaines alloue par `0x0206F02C` (`0206f098 str r0, [r8, #8]`). Voir
# patch_chargeur, ou l'avoir ignore a coute deux regressions.
SRC = GREFFE_C                    # 16 o : {compte, bloc, chaines, reserve}
NOEUD = GREFFE_C2                 # 28 o : le noeud synthetique du conteneur 2
SOURCE = GREFFE_B + 8 + 72        # 52 o : le talon qui batit la table
EMP2 = ZONE_LIBRE + 0xC0 + 52     # 32 o : morceau 2, queue de la region du portier
PLACES = {F1: 52, F2: 72, TROUVE: 32, EMP3: 40, EMP2: 32, SOURCE: 52}

# --- les sites d'appel a rediriger, tous dans l'overlay 17 ---
# Verifies par comptage exhaustif des `bl` de l'ARM9 et des 35 overlays.
SITES = {
    0x021A2164: F1,      # portier 1 de l'apparition
    0x021A2178: F2,      # portier 2 de l'apparition
    0x021A22F0: F2,      # sa relecture, plus loin dans la meme fonction
    0x021A21F8: TROUVE,  # FindLoadedModel -> emprunt
    0x021A30FC: SOURCE,  # bl prechargeur -> batir la table source d'abord
    # LES DEUX SITES DU PRECHARGEUR. Il consulte les conteneurs lui aussi et
    # saute l'espece qu'il n'y trouve pas (`0x021A29AC beq`). Sans ces deux
    # redirections, un chargement a la demande ne trouverait jamais son
    # enregistrement. En mode normal le comportement est inchange : les especes
    # declarees par la zone sont bien dans le conteneur de la carte.
    0x021A2988: F1,
    0x021A299C: F2,
}
ATTENDU_OVL = {
    0x021A2164: "bl #0x206f500",
    0x021A2178: "bl #0x206ef28",
    0x021A22F0: "bl #0x206ef28",
    0x021A21F8: "bl #0x21a2738",
    0x021A30FC: "bl #0x21a28a8",
    0x021A2988: "bl #0x206f500",
    0x021A299C: "bl #0x206ef28",
}


def talon_source(adr):
    """Batit la table source des 438 monstres sur le tas des modeles.

    Remplace `0x021A30FC bl PRECHARGEUR` dans le montage : on construit la table
    d'abord, puis on enchaine sur le prechargeur comme prevu.

    Entree  r0 = le contexte de terrain (l'argument du prechargeur).

    POURQUOI ICI. Le tas des modeles (`ctx+0x113C`) vient d'etre cree deux
    instructions plus haut, il est vierge et il a 50 a 92 Ko libres depuis
    patch_place. C'est le seul endroit du cycle de vie ou l'on tient a la fois un
    tas neuf et le contexte. Et comme le tas est recree a chaque montage, la
    table doit l'etre aussi : on remet donc `SRC` a zero avant de rebatir.

    `0x113C` n'est pas un immediat ARM encodable, d'ou les deux additions.
    """
    return assembler([
        "push {r0, lr}",
        "ldr r0, [pc, #{L0}]",              # SRC
        "mov r2, #0",
        "str r2, [r0]",                     # invalider TOUJOURS : le tas est neuf
        # ON NE BATIT PAS LA TABLE SUR UNE CARTE SANS MONSTRES. Elle coute ~21 Ko
        # et le tas d'une ville n'en fait que 62 : les prendre affamait le tas des
        # requetes asynchrones, par lequel une ville charge PNJ, boutiques et
        # decors -- textures cassees, symptome rapporte deux versions de suite.
        # `r5` porte encore la taille du tas a ce point du montage (0x021A30BC
        # `mov r5, r0`, preserve par les appels intermediaires) : 62 280 en ville,
        # 188 384 sur le terrain.
        "cmp r5, #%d" % SEUIL_TERRAIN,
        "blt #{@saute}",
        "ldr r1, [sp]",                     # le contexte de terrain
        "add r1, r1, #0x1100",
        "add r1, r1, #0x3c",                # r1 = ctx + 0x113C, le tas
        "bl #%d" % CHARGE_SOURCE,
        "saute:",
        "pop {r0, lr}",
        "b #%d" % PRECHARGEUR,
    ], adr, litteraux=(SRC,))


def portier1(adr):
    """Rend l'enregistrement REEL de l'espece, meme absente du conteneur.

    Entree  r0 = conteneur (carte+0x2F8), r1 = espece.
    Sortie  r0 = enregistrement, ou 0 si l'espece n'existe nulle part.

    Deux recherches, la meme fonction du jeu pour les deux : d'abord le conteneur
    de la carte (chemin normal), sinon la table source des 438 batie par
    `talon_source`. Elle porte le vrai code de modele, la vraie echelle, les
    vrais champs -- donc l'apparition d'une espece non declaree est aussi
    correcte que celle d'une espece declaree.

    LE DECLENCHEUR DU CHARGEMENT N'EST PAS ICI, ET C'EST UNE LECON PAYEE.
    Il y etait, et le prechargeur -- qui consulte ce meme portier -- declenchait
    alors un chargement depuis l'interieur de sa propre boucle des qu'une espece
    de la liste manquait au conteneur de la carte. Il se rappelait lui-meme,
    ecrasait DEPART/BORNE, et repartait sur un etat incoherent : zero modele
    charge sur six montages, mesure. Un garde sur « suis-je deja en chargement »
    empechait la recursion infinie, pas la premiere reentree.

    Le declencheur vit donc dans `emprunt`, au site `0x021A21F8` : cette fonction
    ne tourne que dans le chemin d'apparition, jamais dans le prechargeur, et son
    role est deja exactement « le modele manque ». Ce portier-ci est alors
    partageable par les deux sites sans risque.

    Si la table n'a pas pu etre batie, `SRC` vaut {0, 0} et la recherche
    generique rend 0 sans deborder (`ldr r5,[r0,#4]` puis `cmp r5,#0`).
    """
    return assembler([
        "push {r4, lr}",
        "mov r4, r1",                       # l'espece, a l'abri de l'appel
        "ldr r2, [pc, #{L0}]",              # l'extracteur de cle
        "bl #%d" % RECH_GENERIQUE,          # le conteneur de la carte
        "cmp r0, #0",
        "popne {r4, pc}",                   # deja present : rien a faire
        "ldr r0, [pc, #{L1}]",              # SRC, la table source
        "mov r1, r4",
        "ldr r2, [pc, #{L0}]",              # le meme extracteur
        "bl #%d" % RECH_GENERIQUE,
        "pop {r4, pc}",
    ], adr, litteraux=(EXTRACTEUR, SRC))


def portier2(adr):
    """Rend le noeud de l'espece dans la liste chainee, ou en synthetise un.

    Entree  r0 = conteneur (carte+0x304), r1 = espece.
    Sortie  r0 = noeud.  Le parcours est celui de 0x0206EF28, recopie tel quel :
    espece en +0x00 (short signe), suivant en +0x10.
    """
    return assembler([
        "push {r4, lr}",
        "mov r4, r1",
        "ldr r0, [r0]",                     # la tete de liste
        "b #{@verif}",
        "boucle:",
        "ldrsh r2, [r0]",
        "cmp r2, r4",
        "popeq {r4, pc}",
        "ldr r0, [r0, #%d]" % SUIVANT,
        "verif:",
        "cmp r0, #0",
        "bne #{@boucle}",
        "ldr r0, [pc, #{L0}]",              # notre noeud statique
        "strh r4, [r0]",
        "mov r1, #0",
        "str r1, [r0, #%d]" % SUIVANT,
        "pop {r4, pc}",
    ], adr, litteraux=(NOEUD,))


def emprunt(adr1, adr2=0, adr3=0, decl=0):
    """FindLoadedModel, avec chargement a la demande puis emprunt en repli.

    Entree  r0, r1 = ceux de l'originale (r1 = espece).
    Sortie  r0 = fiche de modele, ou 0 si AUCUN modele n'est charge.

    Trois etages, dans cet ordre :

    1. la fonction d'origine -- le modele de l'espece est deja la, cas normal
       pour les especes que la zone declare ;
    2. si `decl` est fourni, le CHARGEMENT A LA DEMANDE : on demande le modele de
       l'espece, puis on retente. C'est ici qu'il faut le faire, pas dans le
       portier : cette fonction ne tourne que dans le chemin d'apparition ;
    3. sinon l'EMPRUNT : un modele deja charge tire au hasard parmi les
       emplacements 7 a 18. L'apparence est fausse mais l'espece reste juste.

    Le cas « aucun modele » doit rendre 0 et non boucler : c'est ce qui evite le
    silence definitif mesure au 64 -- l'apparition echoue, le tic reessaie a
    l'image suivante, et le prechargeur finit par repasser.

    On s'arrete au premier emplacement vide : le prechargeur les remplit dans
    l'ordre, un trou ne fait que reduire le choix.

    DECOUPAGE. 108 octets, aucun fragment ne les porte : trois morceaux relies
    par des branchements, resolus par etiquettes -- jamais d'adresse a la main.
    """
    if not decl:
        # sans chargeur : la version courte, d'un seul tenant
        return assembler([
            "push {r4, r5, lr}",
            "bl #%d" % TROUVE_MODELE,
            "cmp r0, #0",
            "popne {r4, r5, pc}",
            "ldr r4, [pc, #{L0}]",
            "mov r5, #0",
            "compte:",
            "ldr r0, [r4, r5, lsl #2]",
            "cmp r0, #0",
            "addne r5, r5, #1",
            "cmpne r5, #%d" % EMPLACEMENTS,
            "bne #{@compte}",
            "cmp r5, #0",
            "popeq {r4, r5, pc}",
            "mov r0, r5",
            "bl #%d" % RAND,
            "ldr r0, [r4, r0, lsl #2]",
            "pop {r4, r5, pc}",
        ], adr1, litteraux=(TABLE_EMPL + 4 * EMPL_MODELES,))
    # `0x021A2738` IGNORE son premier argument : `movs r6, r1` puis
    # `bl 0x200f398` pour aller chercher la table elle-meme. On n'a donc pas a
    # preserver r0 -- deux instructions economisees, et c'est ce qui fait tenir
    # les 104 octets dans les trous disponibles.
    m1 = assembler([
        "push {r4, r5, lr}",
        "mov r5, r1",                       # l'espece
        "bl #%d" % TROUVE_MODELE,
        "cmp r0, #0",
        "popne {r4, r5, pc}",               # le vrai modele est deja la
        "mov r0, r5",
        "bl #%d" % decl,                    # CHARGER le modele de l'espece
        "b #%d" % adr2,
    ], adr1)
    m2 = assembler([
        "mov r1, r5",
        "bl #%d" % TROUVE_MODELE,           # retenter apres le chargement
        "cmp r0, #0",
        "popne {r4, r5, pc}",               # charge : l'apparence est JUSTE
        "ldr r4, [pc, #{L0}]",              # sinon, emprunter
        "mov r5, #0",
        "b #%d" % adr3,
    ], adr2, litteraux=(TABLE_EMPL + 4 * EMPL_MODELES,))
    m3 = assembler([
        "compte:",
        "ldr r0, [r4, r5, lsl #2]",
        "cmp r0, #0",
        "addne r5, r5, #1",
        "cmpne r5, #%d" % EMPLACEMENTS,
        "bne #{@compte}",
        "movs r0, r5",
        "popeq {r4, r5, pc}",               # aucun modele : r0 vaut 0
        "bl #%d" % RAND,
        "ldr r0, [r4, r0, lsl #2]",
        "pop {r4, r5, pc}",
    ], adr3)
    return m1, m2, m3


def tireur_bitmap(adr):
    """Le tireur de terrain, reduit a deux instructions.

    La greffe A2 sait deja tirer une espece valide dans le bitmap des 256 et la
    RENDRE quand le bit 15 de r1 est arme (MODE_RENDRE). Le tireur n'a donc plus
    qu'a l'appeler dans ce mode : chaque apparition demande une espece neuve
    tiree dans tout le bestiaire, au lieu d'une des especes deja chargees.

    C'est cette ligne qui transforme « dix especes par zone » en « n'importe
    laquelle a chaque pop ». Tout le reste de P3 n'est la que pour qu'elle ne
    soit pas rejetee par le portier.
    """
    return assembler([
        "mov r1, #%d" % MODE_RENDRE,
        "b #%d" % GREFFE_A2,
    ], adr)


def patcher(rom, bavard=True, decl=0, mots=0):
    arm9 = bytearray(cc.decompress(bytes(rom.arm9)))
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)

    # LE TIREUR EST REMPLACE, DONC SA QUEUE EST LIBRE. patch_hasard y a pose la
    # greffe B (116 o : tirage dans les modeles charges, plus son repli). Le
    # portier la remplace par huit octets qui tirent dans le bitmap, et les 124
    # octets restants de la fonction accueillent l'emprunt de modele. On les
    # remet donc a zero AVANT le controle de virginite -- sans quoi ce controle
    # refuse a juste titre d'ecrire par-dessus du code encore en place.
    o = GREFFE_B - BASE_ARM9
    arm9[o:o + TAILLE_TIREUR] = bytes(TAILLE_TIREUR)

    # LA PLACE DE `TROUVE` DEPEND DU MODE. Sans chargeur, l'emprunt tient d'un
    # seul tenant et occupe les 72 octets ; avec, il est en trois morceaux dont
    # deux se partagent ces memes 72 octets.
    places = dict(PLACES)
    if not decl:
        places[TROUVE] = 72
        places.pop(EMP2, None)
        places.pop(EMP3, None)
    morceaux = {F1: portier1(F1), F2: portier2(F2),
                SOURCE: talon_source(SOURCE)}
    if decl:
        m1, m2, m3 = emprunt(TROUVE, EMP2, EMP3, decl)
        morceaux[TROUVE], morceaux[EMP2], morceaux[EMP3] = m1, m2, m3
    else:
        morceaux[TROUVE] = emprunt(TROUVE)
    for adr, code in morceaux.items():
        if len(code) > places[adr]:
            raise SystemExit(f"portier a {adr:#010x} : {len(code)} o pour "
                             f"{places[adr]} disponibles")
        o = adr - BASE_ARM9
        if any(arm9[o:o + len(code)]):
            raise SystemExit(f"{adr:#010x} n'est pas libre")
        arm9[o:o + len(code)] = code

    # les zones de donnees : elles doivent etre vierges elles aussi
    for adr, nom, n in ((SRC, "contexte source", 16), (NOEUD, "noeud", TAILLE_ENREG)):
        o = adr - BASE_ARM9
        if any(arm9[o:o + n]):
            raise SystemExit(f"{nom} a {adr:#010x} : region non vierge")

    # le tireur : deux instructions, ecrites PAR-DESSUS la greffe B de
    # patch_hasard, qui tirait dans les modeles charges.
    t = tireur_bitmap(GREFFE_B)
    arm9[GREFFE_B - BASE_ARM9:GREFFE_B - BASE_ARM9 + len(t)] = t

    struct.pack_into("<I", arm9, COMPRESSED_END, 0)
    rom.arm9 = bytes(arm9)

    # --- overlay 17 : les quatre sites d'appel ---
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
    for adr, cible in SITES.items():
        data[adr - base:adr - base + 4] = bl(adr, cible)

    o17.data = bytes(data)
    o17.compressed = False
    o17.compressedSize = len(data)
    rom.files[o17.fileID] = bytes(data)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)

    if bavard:
        for adr, code in sorted(morceaux.items()):
            print(f"  portier  : {len(code):3d} o a {adr:#010x}")
        print(f"  tireur   : {len(t)} o a {GREFFE_B:#010x}, tire dans le bitmap")
        print(f"  sites    : {len(SITES)} bl rediriges dans l'overlay 17")
    return len(morceaux)
