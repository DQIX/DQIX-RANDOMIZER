#!/usr/bin/env python3
"""Objectif B : le lot de monstres tourne PENDANT le jeu, pas seulement aux zones.

CE QUI REND L'OPERATION POSSIBLE, ET CE QUI LA REND SURE.

`0x021A2FA0(ctx)` est le montage complet des monstres d'une carte : il demonte le
precedent (`0x021A316C`) puis recharge les modeles depuis la liste de
prechargement. Il est reentrant et sans fuite -- le jeu l'appelle depuis sept
endroits. Et sur un tas de type FRAME HEAP -- ce qu'est le tas des modeles,
signature `FRMH` mesuree -- la regeneration totale est la seule liberation
possible : `Free` y rembobine tout ou ne fait rien (docs/FORMAT.md 47). Il n'y a
donc pas d'eviction fine a esperer, et ce montage est exactement le bon outil.

CE QU'IL NE FAIT PAS : reconstruire les conteneurs. Ils sont batis par une
machine a etats qui ne tourne qu'au chargement de carte. Une espece absente des
conteneurs n'obtient donc pas son modele, quoi qu'on mette dans la liste --
c'est pourquoi la rotation exige la greffe C, qui leur fait porter 150 especes
des le chargement. Sans elle, v32 ne montrait qu'un seul monstre.

CE QUI LA REND SURE : les acteurs deja vivants gardent un pointeur sur leur objet
de modele, et le tas est rembobine. Si leur espece ne figure pas dans la nouvelle
liste, ils pointent sur de la memoire rendue -- que le moteur 3D relit a chaque
image. Le balayage des acteurs vivants n'est donc pas une precaution, c'est la
condition. Predicat valide sur temoin (docs/FORMAT.md 50) :

    variante = [carte+0x02] & 3
    base     = 0x70 + 12 * variante
    pour i : a = [table + 8 + 4*(base+i)] ; si a != 0 et (short)[a+2] >= 0
             alors l'espece [a+2] est vivante

ON REMET LES ACTEURS, PAS LES MODELES. Remettre les douze emplacements de modele
serait plus simple et plus sur, mais le tas etant rembobine chaque espece remise
est RECHARGEE au prix plein : les modeles deja la occuperaient toute la place et
le lot ne changerait jamais. Les acteurs vivants sont trois a cinq (mesure), ce
qui laisse le reste aux especes neuves.

LE DECLENCHEUR, ET SA CADENCE REELLE. `0x020733F0` (`movs r7, r0`) est en tete du
tic d'apparition ; il faut donc preserver r0 -- d'ou le registre supplementaire
pousse -- puis reproduire le `movs` avec ses drapeaux, que l'instruction suivante
consomme (`ldrbne r0, [r7, #0xc]`).

Mais ce tic n'est PAS appele a chaque image : mesure sur la sauvegarde du joueur,
600 appels en une minute de marche, puis plus rien des que la carte porte son
quota de symboles. La periode se compte donc en appels, pas en images, et une
periode de 1 024 ne partait qu'une seule fois. A 256, la rotation part environ
toutes les 25 secondes de marche -- et jamais quand la carte est deja pleine, ce
qui tombe bien.

LA PLACE : trois morceaux relies par des branchements, tous dans du bourrage
verifie (voir le plan memoire de patch_hasard.py). Ils tiennent au mot pres,
16/16 et 18/18, le troisieme a 48 sur 52.

Usage: python scripts/patch_rotation.py <rom.nds> <sortie.nds> [periode]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capstone
import ndspy.rom
from patch_hasard import (ACCROCHE, ADD_ESPECE, ATTENDU_ACCROCHE, BASE_ARM9,
                          CARTE, COMPRESSED_END, COMPTEUR, EMPL_ACTEURS,
                          EMPLACEMENTS, GET_CTX, GREFFE_A2, MONTAGE,
                          CARTE_MOT, MODE_RENDRE, PERIODE, PLACES, ROT_A,
                          ROT_B, ROT_C, ROT_D, ROT_E, TABLE_EMPL, TIRAGES,
                          ZONE_LIBRE, assembler)


def lignes_c():
    """Le montage, puis la sortie commune. Son adresse est calculee, pas ecrite."""
    return [
        "bl #%d" % GET_CTX,                 # le contexte de terrain
        # Le montage dereference son argument des sa premiere instruction, et
        # rien ne garantit qu'un contexte existe.
        "cmp r0, #0",
        "blne #%d" % MONTAGE,
        # sortie commune : on restaure, on reproduit l'instruction otee avec ses
        # drapeaux, et on rend la main
        "pop {r0, r4, r5, r6, r7, r8, sb, lr}",
        "movs r7, r0",
        "bx lr",
    ]


def adresse_sortie():
    """L'adresse du `pop` de sortie, ou aboutissent les deux sorties du morceau A.

    Elle est CHERCHEE dans la liste des lignes, jamais ecrite en dur : une
    version precedente portait `ROT_C + 4 * 10`, et en retirant deux instructions
    en tete du morceau le `pop` a recule d'une instruction. Les branchements
    visaient alors le `movs` qui le suit : sept mots fuyaient sur la pile a chaque
    appel du tic d'apparition, et sa fonction appelante depilait ensuite une
    adresse de retour corrompue.
    """
    instructions = [l for l in lignes_c()
                    if not (l.endswith(":") and " " not in l.strip())]
    i = next(k for k, l in enumerate(instructions) if l.startswith("pop"))
    return ROT_C + 4 * i


def morceau_a(adr, periode):
    """Cherche la carte, DETECTE UN CHANGEMENT DE CARTE, puis compte.

    POURQUOI LE CHANGEMENT DE CARTE REMET LE COMPTEUR A ZERO. Le prechargeur du
    chargement de carte est asynchrone -- une entree par image, mesure du 57. Si
    la rotation part pendant ce vol, son montage demonte les modeles que le
    premier prechargeur est en train de poser, et un second prechargeur demarre
    par dessus. Resultat rapporte par le joueur : un seul monstre en boucle apres
    une teleportation ou une sortie de ville, et parfois un ecran noir au
    changement de zone.

    En remettant le compteur a zero des que `[carte+0x00]` change, la premiere
    rotation d'une carte ne peut pas arriver avant une periode entiere -- une
    vingtaine de secondes de marche, largement de quoi laisser le chargement
    finir.

    La suite du compteur est dans le morceau E, faute de place ici.
    """
    return assembler([
        "push {r0, r4, r5, r6, r7, r8, sb, lr}",
        "ldr r8, [pc, #{L0}]",              # base de la zone libre
        "bl #%d" % CARTE,
        "movs r6, r0",
        "beq #%d" % adresse_sortie(),       # pas de carte : sortir
        "ldrh r0, [r6]",                    # identifiant de carte
        "ldr r1, [r8, #%d]" % (CARTE_MOT - ZONE_LIBRE),
        "str r0, [r8, #%d]" % (CARTE_MOT - ZONE_LIBRE),
        "cmp r0, r1",
        "movne r0, #0",
        "strne r0, [r8, #%d]" % (COMPTEUR - ZONE_LIBRE),
        "bne #%d" % adresse_sortie(),       # carte changee : on repart de zero
        "ldr r0, [r8, #%d]" % (COMPTEUR - ZONE_LIBRE),
        "add r0, r0, #1",
        "b #%d" % ROT_E,
    ], adr, litteraux=(ZONE_LIBRE,))


def morceau_e(adr, periode):
    """La fin du compteur, logee dans la queue libre du morceau C."""
    return assembler([
        "cmp r0, #%d" % periode,
        "movge r0, #0",
        "str r0, [r8, #%d]" % (COMPTEUR - ZONE_LIBRE),
        "bne #%d" % adresse_sortie(),       # pas encore l'heure
        "add r4, r6, #0x44",                # la liste de prechargement
        "mov sb, #0",                       # index d'ecriture
        "b #%d" % ROT_D,                    # -> le garde-fou
    ], adr)


def morceau_b(adr):
    """Ecrit d'abord les especes des acteurs VIVANTS. Condition de surete.

    Les acteurs deja vivants gardent un pointeur sur leur objet de modele, et le
    montage rembobine le tas : si leur espece ne figure pas dans la nouvelle
    liste, ils pointent sur de la memoire rendue, que le moteur 3D relit a chaque
    image. Les mettre EN TETE garantit en outre que le prechargeur, qui suit
    l'ordre de la liste, les recharge en premier.

    Il y a au plus douze emplacements d'acteur, donc au plus douze ecritures aux
    index 0 a 11 : l'index ne peut pas atteindre 12, ou il ecraserait le compte
    de la liste (`carte+0x44+0x18`).
    """
    return assembler([
        "ldr r7, [pc, #{L0}]",              # emplacements d'acteur, variante 0
        "ldrh r0, [r6, #2]",
        "and r0, r0, #3",                   # la variante de carte
        "add r0, r0, r0, lsl #1",           # 3 x variante
        "add r7, r7, r0, lsl #4",           # + 4 x 12 x variante
        "mov r5, #%d" % EMPLACEMENTS,
        "boucle:",
        "subs r5, r5, #1",
        "bmi #%d" % (ROT_D + 4 * 4),        # fini : le tirage, dans le morceau D
        "ldr r0, [r7, r5, lsl #2]",
        "cmp r0, #0",
        "beq #{@boucle}",
        "ldrsh r1, [r0, #2]",
        "cmp r1, #0",
        # `strh` n'accepte PAS d'index decale sur ARM (mode d'adressage 3) : il
        # faut calculer le deplacement dans un registre.
        "movge r2, sb, lsl #1",
        "strhge r1, [r4, r2]",              # ecriture EN PLACE
        "addge sb, sb, #1",
        "b #{@boucle}",
    ], adr, litteraux=(TABLE_EMPL + 4 * EMPL_ACTEURS,))


def morceau_d(adr, tirages=None):
    """LE GARDE-FOU, puis le tirage. Les deux tiennent dans les douze mots.

    POURQUOI CE GARDE-FOU EXISTE. Sans lui la rotation tournait EN VILLE et
    PENDANT LES CHARGEMENTS DE CARTE -- mesure : `carte=100 liste=0` avec treize
    tours de tirage suivis d'un montage. Elle ecrivait douze especes alors que le
    compte de la liste valait zero, donc le jeu ne les voyait jamais, et elle
    appelait le montage pour rien : celui-ci demontait tous les modeles. En
    pleine transition, elle reecrivait une liste a moitie construite. Symptomes
    rapportes par le joueur : un seul monstre apres une teleportation, plus aucun
    apres un aller-retour en ville, ecran noir au changement de zone.

    On ne touche donc a rien tant que la liste n'est pas COMPLETE. Le compte vaut
    zero hors carte a rencontres, et il monte progressivement pendant le parsage
    d'encmons : exiger le compte plein ecarte les deux cas d'un seul test.

    Le tirage avance ensuite `r4` lui-meme (`strh r0, [r4], #2`), ce qui evite de
    recalculer un deplacement a chaque tour. La greffe A2 ignore r0 en mode
    « rendre » et preserve r4, donc rien ne s'y oppose.
    """
    n = tirages or TIRAGES
    return assembler([
        "ldrh r0, [r4, #0x18]",             # le compte de la liste
        "cmp r0, #%d" % n,
        "blt #%d" % adresse_sortie(),       # incomplete : ne rien toucher
        "b #%d" % ROT_B,                    # -> les acteurs vivants
        "add r4, r4, sb, lsl #1",           # <- retour : curseur d'ecriture
        "boucle:",
        "cmp sb, #%d" % n,
        "bge #%d" % ROT_C,
        "mov r1, #%d" % MODE_RENDRE,
        "bl #%d" % GREFFE_A2,
        "strh r0, [r4], #2",
        "add sb, sb, #1",
        "b #{@boucle}",
    ], adr)


def morceau_c(adr):
    """Regenere les modeles depuis la liste reecrite."""
    return assembler(lignes_c(), adr)


def bl(depuis, vers):
    d = (vers - (depuis + 8)) >> 2
    return struct.pack("<I", 0xEB000000 | (d & 0xFFFFFF))


def patcher(rom, bavard=True, periode=None, tirages=None, force=True):
    per = periode or PERIODE
    tir = tirages or TIRAGES
    arm9 = bytearray(bytes(rom.arm9))
    if struct.unpack_from("<I", arm9, COMPRESSED_END)[0]:
        raise SystemExit("l'ARM9 de cette ROM est compresse : appliquer "
                         "d'abord --hasard")
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)

    ins = next(md.disasm(bytes(arm9[ACCROCHE - BASE_ARM9:
                                    ACCROCHE - BASE_ARM9 + 4]), ACCROCHE), None)
    lu = f"{ins.mnemonic} {ins.op_str}" if ins else "?"
    if lu != ATTENDU_ACCROCHE:
        raise SystemExit(f"a {ACCROCHE:#010x} : attendu {ATTENDU_ACCROCHE!r}, "
                         f"lu {lu!r}")

    morceaux = {ROT_A: morceau_a(ROT_A, per), ROT_B: morceau_b(ROT_B),
                ROT_D: morceau_d(ROT_D, tir), ROT_C: morceau_c(ROT_C),
                ROT_E: morceau_e(ROT_E, per)}
    for adr, code in morceaux.items():
        if len(code) > PLACES[adr]:
            raise SystemExit(f"rotation a {adr:#010x} : {len(code)} o pour "
                             f"{PLACES[adr]} disponibles")
        o = adr - BASE_ARM9
        if any(arm9[o:o + len(code)]):
            raise SystemExit(f"{adr:#010x} n'est pas libre")
        arm9[o:o + len(code)] = code
    arm9[ACCROCHE - BASE_ARM9:ACCROCHE - BASE_ARM9 + 4] = bl(ACCROCHE, ROT_A)
    struct.pack_into("<I", arm9, COMPTEUR - BASE_ARM9, 0)
    rom.arm9 = bytes(arm9)

    if bavard:
        print(f"  rotation : {tir} especes tirees tous les {per} appels du tic "
              f"d'apparition" + ("" if force else ", SANS montage force"))
        print(f"    accroche {ACCROCHE:#010x} -> "
              + ", ".join(f"{a:#010x} ({len(c)}/{PLACES[a]} o)"
                          for a, c in morceaux.items()))
    return per


if __name__ == "__main__":
    src, sortie = sys.argv[1], sys.argv[2]
    p = int(sys.argv[3]) if len(sys.argv) > 3 else None
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    patcher(rom, periode=p)
    rom.saveToFile(sortie)
    manque = os.path.getsize(src) - os.path.getsize(sortie)
    if manque > 0:
        with open(sortie, "ab") as f:
            f.write(b"\xff" * manque)
    print(f"ecrit : {sortie} ({os.path.getsize(sortie):,} o)")
