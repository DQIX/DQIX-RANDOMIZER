#!/usr/bin/env python3
"""P4 etape 2 -- le chargement a la demande, par le prechargeur lui-meme.

L'IDEE. On n'ecrit pas de chargeur : le prechargeur `0x021A28A8` fait deja toute
la sequence -- ouvrir `enemy.gp2`, extraire le membre, trouver le sous-chunk
`.cchr`, decompresser sur le tas, enregistrer le modele, poser la fiche dans
l'emplacement. On le transforme en « charge UNE espece dans UN emplacement » par
cinq greffes de quatre a dix instructions, et on l'appelle depuis l'apparition.

CE QUI REND CELA POSSIBLE, ET QUI N'ETAIT PAS VRAI AVANT LE 68

1. Le prechargeur prend le code de modele dans l'enregistrement du conteneur 1
   (`0x021A29B4 ldr r2, [r0, #4]`), et le portier rend desormais
   l'enregistrement REEL de n'importe laquelle des 438 especes, grace a la table
   source batie par `talon_source`. Donc lui demander l'espece X suffit : il
   trouvera son vrai code et chargera le bon fichier.
2. Le tas des modeles est un ExpHeap et il a 50 a 92 Ko libres, parce que
   `patch_place` a borne la confiscation (67).
3. Le spawn reessaie indefiniment quand l'apparition echoue (`0x02073D40`), donc
   un echec de chargement ne coute qu'une image.

TROIS MOTS PLUTOT QU'UN TEST PARTOUT

`DEMANDE` vaut 0 en fonctionnement normal, espece+1 pour un chargement unique.
`DEPART` et `BORNE` sont l'index de depart et la borne de la boucle du
prechargeur. Le prechargeur les lit betement ; c'est la greffe A, qui tourne en
tete dans les deux modes, qui les remet a 0 et au plafond en mode normal.

Cette indirection fait tomber deux greffes de douze instructions a quatre, et
supprime le talon de plafond de `patch_place` -- son role devient la valeur
initiale de `BORNE`.

LES CINQ GREFFES

| # | site | en mode DEMANDE |
|---|---|---|
| A | `0x021A28CC` `bl 0x021A27E8` | ne PAS vider les emplacements ; sinon initialise DEPART/BORNE |
| C | `0x021A2900` `bl 0x0207DFA0` | ne PAS faire le rollback du watermark VRAM |
| B | `0x021A28E0` `bl 0x0209C0FC` | rendre 1 : une seule fiche a dimensionner |
| D | `0x021A295C` `mov sb, #0`    | `sb = DEPART` |
| F | `0x021A2ACC` `bl 0x0209C0FC` | rendre `BORNE` |

LA GREFFE C EST LA PLUS IMPORTANTE, ET ELLE EST NEUVE. Le prechargeur commence
par `0x021A2900 bl 0x0207DFA0`, qui restaure l'etat du gestionnaire de VRAM de
textures a un point de reprise -- autrement dit qui JETTE toutes les textures
allouees depuis. En mode normal c'est voulu. En mode demande ce serait
catastrophique : les textures des autres modeles disparaitraient. La VRAM de
textures est un watermark dont le `free` est un stub vide (66), donc nos
chargements successifs avancent le curseur sans jamais rien liberer -- et quand
il sature, l'allocation echoue et le modele se charge sans texture. Il faudra
alors un rafraichissement en bloc, c'est-a-dire un appel du prechargeur en mode
NORMAL. C'est la derniere piece, et elle vient apres celle-ci.

LA GREFFE B BORNE UNE FUITE. Le prechargeur alloue son tableau de fiches
(`compte * 0xB0`) a chaque appel. En mode demande on lui fait annoncer 1 : il
n'alloue donc que 0xB0 octets par chargement au lieu de douze fois plus. La fuite
subsiste -- 176 octets par apparition, ~50 Ko en 300 apparitions -- mais elle est
bornee par la duree de vie du tas, recree a chaque changement de zone. Reutiliser
un tableau unique couterait 52 octets de code ; a mesurer en jeu avant de payer.

CE QU'ON NE FAIT PAS. On ne touche pas au montage `0x021A2FA0` : c'est le mur du
63, il detruit des tas et delie l'arbre des allocateurs. Le prechargeur seul ne
detruit rien.

OU LOGE TOUT CELA. Les regions neuves sont validees par canari le 9 septembre --
motif ecrit en RAM, relu apres huit marches, un franchissement de zone et un
retour : 0 mot ecrase sur les huit, temoin compris (69).
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import capstone
import ndspy.code
import ndspy.codeCompression as cc

from patch_hasard import assembler, bl, BASE_ARM9, COMPRESSED_END, OVL

# --- les fonctions du jeu qu'on court-circuite ---
VIDE_EMPLACEMENTS = 0x021A27E8    # ClearAllMonsterModelSlots
ROLLBACK_VRAM = 0x0207DFA0        # SetFrmTexVramState : jette les textures
COMPTE_LISTE = 0x0209C0FC         # `ldrh r0, [r0, #0x18] ; bx lr`
GET_ESPECE = 0x0209C0B8           # GetSpecies(liste, i)
PRECHARGEUR = 0x021A28A8
GET_CTX_TERRAIN = 0x021D82E4      # [ce mot] = le contexte de terrain
EMPLACEMENTS = 12
PLAFOND = 5                       # especes prechargees en mode normal

# --- les trois mots de commande, contigus, dans la region de SRC ---
# LE CONTEXTE DE LA TABLE SOURCE FAIT PLUS DE HUIT OCTETS, et l'ignorer a coute
# deux regressions de suite. `0x0206F02C` alloue un SECOND bloc -- les chaines --
# et le range en `+0x08` (`0206f098 str r0, [r8, #8]`). Avec les mots de commande
# a SRC+8, le jeu ecrasait donc `DEMANDE` avec ce pointeur a chaque montage : le
# prechargeur se croyait en mode demande, sautait son initialisation et le vidage
# des emplacements, et travaillait avec DEPART/BORNE aleatoires. Symptomes
# successifs : zero modele charge, puis un montage qui semblait ne jamais finir.
#
# On reserve donc SEIZE octets au contexte. GREFFE_C en fait 40 : 16 pour SRC,
# 12 pour les mots, 12 de reste.
# LES TROIS MOTS VIVENT DESORMAIS EN ITCM, comme le code. `plan()` fixe leur
# adresse ; les greffes la lisent au moment de l'assemblage.
MOTS = 0                          # +0x00 DEMANDE, +0x04 DEPART, +0x08 BORNE
TAILLE_MOTS = 12

# --- ou loge le code : DU CODE MORT, valide par surveillance d'execution ---
#
# TROIS ECHECS AVANT CELUI-LA, et chacun apprend quelque chose.
#
# 1. Les BOURRAGES A ZERO de l'ARM9 ne sont pas fiables. Le canari prouve qu'une
#    region n'est pas ECRITE ; il ne dit rien sur le fait qu'elle soit LUE, et une
#    plage de zeros peut etre une table que le moteur consulte. Mesure : une seule
#    greffe posee a 0x020E7100, en simple passe-plat, casse les textures de toutes
#    les cartes sans monstres (work/dq9_D.nds contre work/dq9_B.nds, identiques a
#    cette greffe pres).
# 2. La QUEUE DE L'ITCM (3 456 octets a 0x01FFF280, que rien ne declare) est bien
#    libre, mais y acceder demande d'agrandir le bloc d'autoload -- et crt0 refuse
#    cette restructuration : la ROM se bloque au demarrage, PC fige dans la boucle
#    d'attente. Verifie en isolant le contenu du mecanisme (work/dq9_F.nds, meme
#    agrandissement rempli de zeros, sans aucune redirection : bloque aussi).
#    Module conserve : scripts/patch_itcm.py.
# 3. Le CODE MORT, lui, se valide par le BON test -- la surveillance d'execution,
#    dont on sait qu'elle fonctionne (temoin positif oblige). Et une region de code
#    jamais executee ne peut pas etre une table lue par le moteur.
#
# Releve sur deux sessions tres differentes -- savestate hors ville puis demarrage
# a froid avec menus et interieurs, temoin `Allocate` a 5 692 puis 1 754 :
#
#   0200341C (2080 o)    779 /    669   VIVANT (muet au chargement, revele par
#                                       les menus -- d'ou l'obligation d'elargir)
#   0204C044 (1500 o) 136594 /  80576   VIVANT
#   02002CB8 (1888 o)      0 /      0   muet   <- retenu
#   0200702C (1732 o)      0 /      0   muet
#   0200884C (1368 o)      0 /      0   muet
#
# CE N'EST PAS UNE PREUVE. « Muet sur deux sessions » n'est pas « mort » : le 33
# avait deja note que le critere ne couvre pas les appels formes par des tables
# construites a l'execution. Si un defaut apparait dans un contexte non exerce --
# un combat, une grotte, un dialogue particulier -- C'EST LA PREMIERE PISTE.
CODE_MORT = 0x02002CB8            # 1 888 octets, huit fois le besoin
CODE_MORT_TAILLE = 1888
# Les bourrages a zero de l'ARM9 se sont reveles non fiables : une seule greffe
# posee a 0x020E7100, en passe-plat, casse les textures des cartes sans monstres.
# Voir patch_itcm : 3 456 octets a 0x01FFF280 que rien ne revendique, obtenus en
# agrandissant le bloc d'autoload de l'ITCM. L'espace etant contigu, plus aucun
# decoupage n'est necessaire -- le declencheur redevient une seule piece.
# --- les sites, tous dans l'overlay 17 ---
SITE_VIDE = 0x021A28CC
SITE_TABLEAU = 0x021A28E0
SITE_VRAM = 0x021A2900
SITE_ESPECE = 0x021A2974          # bl GetSpecies(liste, i)
SITE_DEPART = 0x021A295C
SITE_BOUCLE = 0x021A2ACC
ATTENDU_OVL = {
    SITE_VIDE: "bl #0x21a27e8",
    SITE_TABLEAU: "bl #0x209c0fc",
    SITE_VRAM: "bl #0x207dfa0",
    SITE_DEPART: "mov sb, #0",
    SITE_ESPECE: "bl #0x209c0b8",
    SITE_BOUCLE: "bl #0x209c0fc",
}


def greffe_a(adr, plafond=PLAFOND):
    """Init des mots de boucle, et saut du vidage des emplacements.

    Tourne en tete du prechargeur, dans les deux modes. En mode normal elle
    remet `DEPART` a 0 et `BORNE` au plafond, puis vide les emplacements comme
    d'origine. En mode demande elle ne fait rien du tout : les emplacements
    gardent leurs modeles, et `DEPART`/`BORNE` sont ceux que le declencheur a
    poses.
    """
    return assembler([
        "ldr r1, [pc, #{L0}]",              # les trois mots
        "ldr r2, [r1]",                     # DEMANDE
        "cmp r2, #0",
        "bxne lr",                          # mode demande : ne rien toucher
        "mov r2, #0",
        "str r2, [r1, #4]",                 # DEPART = 0
        "mov r2, #%d" % plafond,
        "str r2, [r1, #8]",                 # BORNE = plafond
        "b #%d" % VIDE_EMPLACEMENTS,
    ], adr, litteraux=(MOTS,))


def greffe_c(adr):
    """Saut du rollback du watermark VRAM en mode demande.

    Sans ce saut, chaque chargement unique jetterait les textures de tous les
    autres modeles : le prechargeur remet le gestionnaire a son point de reprise
    avant de recharger (66).
    """
    return assembler([
        "ldr r1, [pc, #{L0}]",
        "ldr r1, [r1]",
        "cmp r1, #0",
        "bxne lr",
        "b #%d" % ROLLBACK_VRAM,
    ], adr, litteraux=(MOTS,))


def greffe_e(adr):
    """Greffe E : rendre l'espece DEMANDEE au lieu de celle de la liste.

    SANS ELLE, LE CHARGEUR NE SERT A RIEN, et c'est ce qui est arrive : elle
    existait dans la premiere version du module et je l'ai perdue en le
    reecrivant autour des trois mots. Mesure : `spawn=4 decl1=4 prech=4` -- toute
    la chaine partait -- mais les emplacements ne changeaient JAMAIS d'espece.
    Le prechargeur chargeait `GetSpecies(liste, DEPART)`, soit une espece de la
    zone deja chargee, au lieu de celle qu'on venait de tirer.
    """
    return assembler([
        "ldr r2, [pc, #{L0}]",
        "ldr r2, [r2]",                     # DEMANDE
        "cmp r2, #0",
        "subne r0, r2, #1",                 # l'espece demandee
        "bxne lr",
        "b #%d" % GET_ESPECE,
    ], adr, litteraux=(MOTS,))


def greffe_d(adr):
    """L'index de depart de la boucle : `sb = DEPART`.

    Remplace `mov sb, #0`. Aucun test de mode : la greffe A a deja mis DEPART a
    0 en fonctionnement normal.
    """
    return assembler([
        "ldr sb, [pc, #{L0}]",
        "ldr sb, [sb, #4]",
        "bx lr",
    ], adr, litteraux=(MOTS,))


def greffe_borne(adr):
    """`min(compte de la liste, BORNE)` -- pour les DEUX sites.

    UN TABLEAU DIMENSIONNE PAR UN COMPTE ET INDEXE PAR UN AUTRE : c'est ce qui a
    casse le jeu, de deux facons.

    Le prechargeur appelle `0x0209C0FC` a deux endroits : en `0x021A28E0` pour
    dimensionner son tableau de fiches (`compte * 0xB0`), et en `0x021A2ACC` pour
    borner sa boucle. Les deux recoivent `carte+0x44`. Si les deux valeurs
    divergent, la boucle ecrit des fiches hors du tableau.

    - En VILLE la liste est vide : `Allocate(tas, 0)`, et une premiere version
      qui bornait la boucle a 5 y ecrivait cinq fiches de 0xB0 -- 880 octets
      deborde sur le tas. Symptomes rapportes : textures cassees et decor qui
      bouge en ville.
    - En MODE DEMANDE une autre version annoncait 1 -- un tableau de 0xB0 --
      alors que l'index vaut `DEPART`, jusqu'a 7 : 1 232 octets debordes, donc
      plantage a la premiere apparition hors de la ville.

    La seule forme correcte est donc la meme valeur aux deux sites, et c'est
    `min(compte reel, BORNE)` : en ville zero tour et zero fiche, en mode demande
    `DEPART + 1` fiches pour un index qui va jusqu'a `DEPART`.

    LE `min` EST INDISPENSABLE, et l'avoir oublie a casse le jeu.

    L'ancien plafond de `patch_place` rendait `min(compte, N)`. Ma premiere
    version rendait `BORNE` tout court -- or **en ville la liste de prechargement
    est vide** (`liste=0`, mesure au temoin de montage). La boucle tournait donc
    cinq fois sur une liste sans entrees, `GetSpecies(liste, i)` rendait
    n'importe quoi, et le prechargeur chargeait cinq modeles bidon dans les
    emplacements 7 a 11.

    Symptomes rapportes par le joueur : textures cassees et decors qui bougent en
    ville, puis plantage aux premiers pas hors de la ville -- la premiere
    apparition dereferencait ces fiches corrompues.

    En mode demande le compte vaut douze et `BORNE` vaut `DEPART + 1`, donc le
    `min` rend bien `DEPART + 1`. En ville le compte vaut zero, donc zero tour.
    """
    return assembler([
        "ldr r1, [pc, #{L0}]",
        "ldr r1, [r1, #8]",                 # BORNE
        "ldrh r0, [r0, #0x18]",             # le compte reel de la liste
        "cmp r0, r1",
        "movgt r0, r1",
        "bx lr",
    ], adr, litteraux=(MOTS,))


def declencheur(adr):
    """Demande le chargement d'une espece. UNE SEULE PIECE, enfin.

    Entree  r0 = espece.

    Il etait decoupe en trois morceaux relies par des branchements, faute de
    trouver 68 octets contigus dans les bourrages de l'ARM9. L'ITCM en offre
    3 456 d'un tenant : le decoupage disparait, et avec lui la principale source
    d'erreur du projet (58, 61, et deux des defauts du 71).

    Le contexte de terrain est lu ici plutot que passe en argument : rien ne
    garantit qu'il soit dans `fp` au site d'appel.
    """
    return assembler([
        "push {r4, lr}",
        "ldr r4, [pc, #{L0}]",              # les trois mots
        "add r2, r0, #1",
        "str r2, [r4]",                     # DEMANDE = espece + 1
        "ldr r0, [pc, #{L1}]",
        "ldr r0, [r0]",                     # r0 = le contexte de terrain
        "ldr r2, [r4, #4]",                 # l'emplacement courant
        "add r2, r2, #1",
        "and r2, r2, #7",                   # rotation sur huit emplacements
        "str r2, [r4, #4]",                 # DEPART
        "add r2, r2, #1",
        "str r2, [r4, #8]",                 # BORNE = DEPART + 1 : un seul tour
        "bl #%d" % PRECHARGEUR,
        "mov r2, #0",
        "str r2, [r4]",                     # DEMANDE = 0
        "pop {r4, pc}",
    ], adr, litteraux=(MOTS, GET_CTX_TERRAIN))


# BISECTION. `greffes` limite les sites reellement detournes, pour isoler celui
# qui casse une carte. Cinq hypotheses deduites se sont revelees fausses avant
# qu'on en vienne la : la bissection vaut mieux que la deduction des qu'on a un
# oracle -- ici le joueur, qui voit les textures.
TOUTES = ("A", "TAB", "VRAM", "DEPART", "ESPECE", "BOUCLE")


def plan(arm9, plafond=PLAFOND):
    """Rend (mots, {nom: (adresse, code)}, adresse du declencheur).

    Deterministe : l'adresse de base de l'ITCM est fixee par la ROM, et les
    tailles par l'assemblage. Permet a `patch_portier` de connaitre l'adresse du
    declencheur avant que le blob ne soit ecrit.
    """
    global MOTS
    base, dispo = CODE_MORT, CODE_MORT_TAILLE
    MOTS = base
    a = base + TAILLE_MOTS
    pieces = {}
    for nom, f in (("A", lambda x: greffe_a(x, plafond)), ("BORNE", greffe_borne),
                   ("VRAM", greffe_c), ("DEPART", greffe_d), ("ESPECE", greffe_e)):
        code = f(a)
        pieces[nom] = (a, code)
        a += len(code)
    code = declencheur(a)
    pieces["DECL"] = (a, code)
    a += len(code)
    if a - base > dispo:
        raise SystemExit(f"chargeur : {a - base} o pour {dispo} en ITCM")
    return MOTS, pieces, pieces["DECL"][0]


def patcher(rom, bavard=True, plafond=PLAFOND, greffes=TOUTES):
    arm9 = bytearray(cc.decompress(bytes(rom.arm9)))
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)

    mots, pieces, _ = plan(arm9, plafond)
    base = CODE_MORT
    # ON ECRASE DELIBEREMENT du code -- pas de controle de virginite ici, la
    # region n'est pas vide : elle porte une fonction que rien n'appelle. On met
    # d'abord toute la zone a zero, pour qu'un reste d'ancien code ne puisse pas
    # etre atteint par erreur.
    o = base - BASE_ARM9
    arm9[o:o + CODE_MORT_TAILLE] = bytes(CODE_MORT_TAILLE)
    blob = bytearray(TAILLE_MOTS)
    for adr, code in sorted(pieces.values()):
        if base + len(blob) != adr:
            raise SystemExit(f"trou dans le blob : {adr:#010x} attendu "
                             f"{base + len(blob):#010x}")
        blob += code
    if len(blob) > CODE_MORT_TAILLE:
        raise SystemExit(f"chargeur : {len(blob)} o pour {CODE_MORT_TAILLE}")
    arm9[o:o + len(blob)] = blob

    struct.pack_into("<I", arm9, COMPRESSED_END, 0)
    rom.arm9 = bytes(arm9)

    ovl = rom.loadArm9Overlays()
    o17 = ovl[OVL]
    data = bytearray(o17.data)
    ovbase = o17.ramAddress
    for adr, attendu in ATTENDU_OVL.items():
        i = adr - ovbase
        ins = next(md.disasm(bytes(data[i:i + 4]), adr), None)
        lu = f"{ins.mnemonic} {ins.op_str}" if ins else "?"
        if lu != attendu:
            raise SystemExit(f"ovl17 {adr:#010x} : attendu {attendu!r}, lu {lu!r}")
    choix = {"A": (SITE_VIDE, "A"), "TAB": (SITE_TABLEAU, "BORNE"),
             "VRAM": (SITE_VRAM, "VRAM"), "DEPART": (SITE_DEPART, "DEPART"),
             "ESPECE": (SITE_ESPECE, "ESPECE"), "BOUCLE": (SITE_BOUCLE, "BORNE")}
    for nom in greffes:
        site, piece = choix[nom]
        data[site - ovbase:site - ovbase + 4] = bl(site, pieces[piece][0])

    o17.data = bytes(data)
    o17.compressed = False
    o17.compressedSize = len(data)
    rom.files[o17.fileID] = bytes(data)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)

    if bavard:
        total = sum(len(c) for _, c in pieces.values())
        print(f"  chargeur : {total} o a {CODE_MORT:#010x} (code mort), "
              f"mots a {mots:#010x}, "
              f"plafond normal {plafond} especes")
        print(f"  sites    : {len(greffes)} bl rediriges ({','.join(greffes)})")
    return total
