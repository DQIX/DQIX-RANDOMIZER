#!/usr/bin/env python3
"""P4, etape 1 : faire de la place dans le tas des modeles.

DEUX MOTS, ET ILS DEBLOQUENT LE CHARGEMENT A LA DEMANDE.

Le montage d'une carte (0x021A2FA0) fait ceci, desassemble :

    021a30b8  bl 0x2032804        ; GetFree(ctx+0x1244)  -> r5
    021a30cc  bl 0x2032554        ; Allocate(ctx+0x1244, r5)
    021a30e0  bl 0x2032500        ; CreateTypeA(ctx+0x113C, bloc, r5)   <- FRAME
    021a30fc  bl 0x21a28a8        ; le prechargeur remplit le tas
    021a3108  bl 0x2032804        ; GetFree(ctx+0x113C)  -> r0
    021a310c  mov r5, r0          ; <- TOUT le reliquat
    021a311c  bl 0x2032554        ; Allocate(ctx+0x113C, r5)
    021a312c  bl 0x2032500        ; CreateTypeA(ctx+0x11C0, bloc, r5)

Donc le tas des modeles se voit CONFISQUER tout son libre au profit du tas
`ctx+0x11C0`, et se retrouve a zero octet disponible. C'est ce qui interdisait
tout chargement a la demande, et ce qui obligeait toutes les tentatives de
rotation a repasser par le montage -- le mur du 63.

Mesure au temoin (scripts/lua/montage.lua, six montages) :

    ville   : tas 62 280   libre apres prechargement 62 228   confisque 62 228
    terrain : tas 188 384  libre 93 892   5 modeles            confisque 93 892
    terrain : tas 188 384  libre 99 308   5 modeles            confisque 99 308
    terrain : tas 188 384  libre 36 532   9 modeles            confisque 36 532

36 a 99 Ko jetes a chaque chargement de zone, soit deux a cinq modeles.

Et `ctx+0x11C0` n'en consomme RIEN pendant le jeu : occupation 0 octet sur seize
zigzags de marche, echantillonnee image par image. Il n'est pas inutile pour
autant -- `0x021C20B4` le passe en r2 a `0x0202FD0C`, la mise en file d'une
requete de fichier asynchrone -- mais son besoin reel se compte en kilo-octets :
les trois allocations de `0x021C1FD0` font 0x24 + 0x964 + 0x2D4, soit 3 152
octets, et chacune a sa sortie d'erreur propre. En vanilla, sur une carte pleine,
il ne recevait que 1 828 octets : ces allocations echouaient DEJA. Lui en
reserver 16 Ko rend donc le jeu plus robuste que l'origine, pas moins.

LES DEUX CORRECTIFS

1. `0x021A310C` : garder `GARDE` octets au tas des modeles au lieu de tout ceder.
2. `0x021A30E0` : creer le tas des modeles en **ExpHeap** au lieu d'un frame
   heap. Sur un frame heap, `Free` rembobine tout ou rien (`0x020AF944` fait
   `[tas+0x24] = [tas+0x18]` et ignore le pointeur) : l'eviction modele par
   modele est impossible. Sur un ExpHeap elle l'est, et `NNS_FndFreeToExpHeap`
   fusionne les blocs adjacents.

   Recette validee a l'octet au 54 : talon `mov r3, #4 ; b 0x02032498`. Le
   `mov r3, #4` est l'ALIGNEMENT et il est indispensable -- avec r3 = 0, plus
   aucun modele ne se charge.

Ces deux mots ne font rien tout seuls : ils preparent le chargeur a la demande.
Mais ils sont mesurables separement -- la signature du tas passe de `FRMH` a
`EXPH` et son libre cesse d'etre nul -- donc on les valide avant d'ecrire la
suite.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import capstone
import ndspy.code
import ndspy.codeCompression as cc

from patch_hasard import (assembler, bl, BASE_ARM9, ROT_C, GREFFE_C,
                          COMPRESSED_END, OVL)

# LE DRAPEAU « CETTE CARTE A DES MONSTRES » EXISTE DEJA, GRATUITEMENT.
# `talon_source` (patch_portier) ne batit la table des especes que sur une carte
# a monstres, et le compte de la table est son premier mot. Donc `SRC[0] != 0`
# est exactement le critere qu'il faut ici, sans mot supplementaire.
#
# Il fallait bien deux criteres distincts : `talon_source` decide AVANT le
# prechargement, sur la taille du tas ; cette borne agit APRES, et le libre
# restant y vaut ~77 Ko sur le terrain -- sous n'importe quel seuil qui exclut
# l'eglise. Comparer le libre ne pouvait donc pas marcher.
SRC = GREFFE_C

CREE_FRAME = 0x02032500           # SafeAllocator::CreateTypeA (frame heap)
CREE_EXP = 0x02032498             # SafeAllocator::CreateTypeB (ExpHeap)
ALIGNEMENT = 4                    # le r3 de CreateTypeB -- indispensable (54)

# CE QU'ON GARDE POUR LE CHARGEMENT A LA DEMANDE -- et non ce qu'on donne.
#
# La borne plafonnait d'abord ce que le tas des modeles CEDE au tas des requetes
# asynchrones : `min(libre, 16 Ko)`. Sur une carte de terrain, ou le vanilla lui
# en cede ~77 Ko, cela revenait a l'amputer de 61 Ko. Le besoin de 3 152 octets
# qui justifiait ce chiffre avait ete mesure EN VILLE, au repos ; la transition
# de combat est le plus gros chargement qui passe par ce chemin, et le joueur
# voyait un ecran noir une entree en combat sur deux ou trois.
#
# On inverse donc le sens de la borne : on garde une reserve fixe pour le
# chargement a la demande et on cede TOUT LE RESTE, ce qui ne retire au tas
# asynchrone que ce dont le chargeur a strictement besoin.
# 48 KIO. Un modele de terrain pese 13 Ko en moyenne : 32 Kio n'en laissaient
# passer qu'un seul une fois le tampon du systeme de fichiers deduit. 48 Kio en
# laissent trois ou quatre, ce qui est le regime ou l'eviction commence a avoir
# du sens.
GARDE = 0xC000                    # 48 Ko gardes pour les modeles a la demande
# EN DESSOUS DE CE LIBRE, ON NE BORNE PAS : c'est une carte sans monstres, donc
# le tas des modeles n'a rien a garder, et le tas des requetes asynchrones a tout
# a y gagner. Une VILLE charge enormement par ce chemin (PNJ, boutiques, decors)
# et son tas de modeles ne fait que 62 Ko : lui en confisquer 16 l'affamait, et
# les textures de la ville en sortaient cassees -- symptome rapporte par le
# joueur sur deux versions de suite. Le terrain, lui, depasse largement ce seuil.
# Voir patch_portier : mesure sur trois cartes, ville 62 280, eglise 171 424,
# terrain 188 384. L'eglise passait pour du terrain avec 0x18000.
SEUIL_TERRAIN = 0x2C000

# LE PLAFOND DU PRECHARGEUR, ET POURQUOI IL EST INDISPENSABLE.
#
# Mesure apres la conversion en ExpHeap : le prechargeur ne charge plus 5 modeles
# mais 11, 10, 8 -- sur le frame heap, des allocations echouaient et il abandonnait
# des especes (c'est l'enigme du 57, « quatre modeles avec 127 Ko libres »). Bonne
# nouvelle pour l'apparence empruntee de P3, mais il remplit alors le tas jusqu'a
# huit octets pres : il ne reste RIEN a garder pour le chargement a la demande, et
# la borne de la confiscation ne sert plus a rien puisqu'elle ne fait que reduire.
#
# On borne donc le nombre de tours. `0x021A2ACC bl 0x0209C0FC` relit le compte de
# la liste a chaque tour ; on le remplace par un talon qui rend min(compte, N).
#
# CE N'EST PAS LE GEL DU 60. Celui-la venait de MODIFIER le compte en memoire
# pendant que le prechargeur iterait, alors qu'il avait dimensionne son tableau de
# fiches une fois pour toutes a l'entree. Ici la liste n'est pas touchee et le
# tableau reste dimensionne au vrai compte : on en utilise seulement moins.
PLAFOND = 5                       # especes prechargees, le reste du tas est libre
COMPTE_LISTE = 0x0209C0FC         # `ldrh r0, [r0, #0x18] ; bx lr`
BOUCLE = 0x021A2ACC               # bl COMPTE_LISTE, dans le test de boucle

CREATION = 0x021A30E0             # bl CreateTypeA(ctx+0x113C, ...)
CONFISCATION = 0x021A310C         # mov r5, r0
ATTENDU_OVL = {
    CREATION: "bl #0x2032500",
    CONFISCATION: "mov r5, r0",
    BOUCLE: "bl #0x209c0fc",
}

# Les trois talons logent dans le morceau C de l'ancienne rotation : 52 octets a
# 0x020F1D2C, valides par canari (57) et libres depuis son abandon (63).
TALON_EXP = ROT_C
TALON_BORNE = ROT_C + 16
TALON_PLAFOND = ROT_C + 36        # pose seulement SANS le chargeur, exclusif
# LES 52 OCTETS DE ROT_C SONT PRIS AU MOT PRES : 16 pour le talon d'ExpHeap
# devenu conditionnel, 36 pour la borne. Le seuil y tient en immediat --
# 0x2C000 vaut 0xB0 tourne de 22 -- ce qui evite un litteral et les quatre
# octets qui auraient fait deborder.
PLACES = {TALON_EXP: 16, TALON_BORNE: 36, TALON_PLAFOND: 16}


def talon_expheap(adr, seuil=SEUIL_TERRAIN):
    """ExpHeap sur les cartes a monstres, frame heap partout ailleurs.

    Entree  r0 = handle, r1 = bloc, r2 = taille -- ceux de CreateTypeA.
    On ajoute r3 = alignement et on branche sur l'un ou l'autre constructeur,
    qui rend au meme appelant : le talon ne consomme ni pile ni lr.

    LE CRITERE EST DEJA EN MAIN. `r2` porte la taille du bloc du tas -- 62 Ko en
    ville, 171 a l'eglise, 188 sur le terrain -- et c'est exactement le chiffre
    que `talon_source` compare au meme seuil. Le miroir ne servirait pas ici :
    il est ecrit plus tard dans le montage, il porterait donc la carte
    precedente.

    POURQUOI CONDITIONNER. Applique a toutes les cartes, l'ExpHeap cassait les
    textures des villes et des batiments : sur un frame heap `Free` rembobine
    tout le tas et le jeu compte dessus, alors qu'un ExpHeap ne rend qu'un bloc.
    Applique aux seules cartes a monstres, il donne au chargement a la demande
    la liberation par bloc dont l'eviction a besoin, et laisse intact tout ce qui
    marchait.
    """
    return assembler([
        "cmp r2, #%d" % seuil,
        "movge r3, #%d" % ALIGNEMENT,
        "bge #%d" % CREE_EXP,
        "b #%d" % CREE_FRAME,
    ], adr)


def talon_borne(adr, garde=GARDE):
    """Retient `garde` octets dans le tas des modeles, cede le reste.

    Entree  r0 = le libre restant du tas des modeles.
    Sortie  r5 = max(r0 - garde, 0), la ou le `mov r5, r0` qu'on remplace cedait
            tout. Sur une carte sans monstres on ne retient rien : le tas des
            modeles n'a rien a y garder, et une ville charge enormement par le
            chemin asynchrone.

    Le `bl` qui nous appelle ecrase lr, ce qui est sans consequence : le montage
    a deja empile le sien (`pop {r4..r8, pc}` en sortie) et fait de toute facon
    quatre autres appels avant d'y revenir.
    """
    return assembler([
        "mov r5, r0",
        "ldr r1, [pc, #{L0}]",              # SRC
        "ldr r1, [r1]",                     # le compte de la table source
        "cmp r1, #0",
        "bxeq lr",                          # pas de table : carte sans monstres
        "subs r5, r0, #%d" % garde,
        "movmi r5, #0",                     # jamais negatif : le tas est petit
        "bx lr",
    ], adr, litteraux=(SRC,))


def talon_plafond(adr, plafond=PLAFOND):
    """Rend min(compte de la liste, plafond) au test de boucle du prechargeur.

    Entree  r0 = carte+0x44, la liste de prechargement.
    Sortie  r0 = le compte a ne pas depasser.

    Le corps de `0x0209C0FC` est recopie ici (`ldrh r0, [r0, #0x18]`) plutot
    qu'appele : on evite ainsi de sauver lr, et le talon tient en quatre
    instructions.
    """
    return assembler([
        "ldrh r0, [r0, #0x18]",
        "cmp r0, #%d" % plafond,
        "movgt r0, #%d" % plafond,
        "bx lr",
    ], adr)


def patcher(rom, bavard=True, garde=GARDE, plafond=PLAFOND, expheap=False):
    """`expheap=False` PAR DEFAUT, et c'est le resultat d'un defaut mesure.

    La conversion du tas des modeles en ExpheHeap s'applique a TOUTES les cartes,
    et rien ne la conditionne. Sur un frame heap, `Free` REMBOBINE TOUT le tas et
    ignore le pointeur (`0x020AF944` fait `[tas+0x24] = [tas+0x18]`). Sur un
    ExpHeap il ne libere qu'un bloc. Donc tout code du jeu qui liberait ce tas
    d'un coup ne recupere plus rien : le tas se remplit, les allocations suivantes
    echouent, et les textures n'arrivent pas.

    Symptome rapporte par le joueur sur quatre builds de suite : dans les
    batiments, les villes et les lieux neutres -- les cartes SANS monstres, celles
    qui n'ont rien d'autre a faire de ce tas -- des textures etirees qui
    clignotent. La version `p3`, qui n'avait pas cette conversion, etait propre.

    Et elle ne sert a rien tant que l'eviction n'est pas ecrite : elle n'existait
    que pour permettre de liberer modele par modele. Elle est donc desactivee
    jusque-la. Le chargement a la demande, lui, n'en a pas besoin -- `Allocate`
    fonctionne aussi bien sur un frame heap, c'est `Free` qui differe.
    """
    arm9 = bytearray(cc.decompress(bytes(rom.arm9)))
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)

    morceaux = {TALON_BORNE: talon_borne(TALON_BORNE, garde)}
    if plafond and expheap:
        raise SystemExit("le talon de plafond et celui d'ExpHeap "
                         "se disputent la meme place dans ROT_C")
    if expheap:
        morceaux[TALON_EXP] = talon_expheap(TALON_EXP)
    # PLAFOND 0 = pas de plafond. Deux configurations utiles, mesurees :
    #   sans plafond : le prechargeur charge 8 a 11 modeles au lieu de 5, donc
    #     l'apparence empruntee de P3 est beaucoup plus variee -- mais le tas est
    #     rempli a huit octets pres, il ne reste rien pour le streaming ;
    #   plafond 5    : 5 residents et 50 a 92 Ko libres d'un seul bloc, le
    #     substrat du chargement a la demande.
    if plafond:
        morceaux[TALON_PLAFOND] = talon_plafond(TALON_PLAFOND, plafond)
    for adr, code in morceaux.items():
        if len(code) > PLACES[adr]:
            raise SystemExit(f"talon a {adr:#010x} : {len(code)} o pour "
                             f"{PLACES[adr]} disponibles")
        o = adr - BASE_ARM9
        if any(arm9[o:o + len(code)]):
            raise SystemExit(f"{adr:#010x} n'est pas libre")
        arm9[o:o + len(code)] = code

    struct.pack_into("<I", arm9, COMPRESSED_END, 0)
    rom.arm9 = bytes(arm9)

    ovl = rom.loadArm9Overlays()
    o17 = ovl[OVL]
    data = bytearray(o17.data)
    base = o17.ramAddress
    controles = dict(ATTENDU_OVL)
    if not plafond:
        del controles[BOUCLE]
    if not expheap:
        del controles[CREATION]
    for adr, attendu in controles.items():
        i = adr - base
        ins = next(md.disasm(bytes(data[i:i + 4]), adr), None)
        lu = f"{ins.mnemonic} {ins.op_str}" if ins else "?"
        if lu != attendu:
            raise SystemExit(f"ovl17 {adr:#010x} : attendu {attendu!r}, lu {lu!r}")
    if expheap:
        data[CREATION - base:CREATION - base + 4] = bl(CREATION, TALON_EXP)
    data[CONFISCATION - base:CONFISCATION - base + 4] = bl(CONFISCATION, TALON_BORNE)
    if plafond:
        data[BOUCLE - base:BOUCLE - base + 4] = bl(BOUCLE, TALON_PLAFOND)

    o17.data = bytes(data)
    o17.compressed = False
    o17.compressedSize = len(data)
    rom.files[o17.fileID] = bytes(data)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)

    if bavard:
        if expheap:
            print(f"  tas modeles : ExpHeap (talon {len(morceaux[TALON_EXP])} o a "
                  f"{TALON_EXP:#010x}), alignement {ALIGNEMENT}")
        else:
            print("  tas modeles : frame heap (vanilla) -- ExpHeap desactive, il "
                  "cassait les cartes sans monstres")
        print(f"  confiscation: {garde:,} o gardes pour les modeles (talon "
              f"{len(morceaux[TALON_BORNE])} o a {TALON_BORNE:#010x})")
        if plafond:
            print(f"  prechargeur : plafonne a {plafond} especes (talon "
                  f"{len(morceaux[TALON_PLAFOND])} o a {TALON_PLAFOND:#010x})")
        else:
            print("  prechargeur : sans plafond (8 a 11 modeles, mesure)")
    return garde
