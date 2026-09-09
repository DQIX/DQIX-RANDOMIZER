#!/usr/bin/env python3
"""De la place de code qui ne repose sur AUCUN pari : on la demande au jeu.

TROIS EMPLACEMENTS ESSAYES AVANT, ET LEURS ECHECS -- c'est ce qui justifie ce
detour, qui serait sinon disproportionne.

1. LES BOURRAGES A ZERO de l'ARM9. Le canari du projet prouve qu'une region
   n'est pas ECRITE par le jeu ; il ne dit rien sur le fait qu'elle soit LUE, et
   une plage de zeros peut parfaitement etre une table que le moteur consulte.
   Mesure : une seule greffe posee a 0x020E7100, en simple passe-plat, casse les
   textures de toutes les cartes sans monstres (`work/dq9_D.nds` contre
   `work/dq9_B.nds`, identiques a cette greffe pres).

2. LA QUEUE DE L'ITCM. 3 456 octets a 0x01FFF280 que rien ne declare -- ni les
   donnees du bloc d'autoload, ni son BSS. L'espace est reel, mais y acceder
   demande d'agrandir le bloc, et crt0 refuse cette restructuration : la ROM se
   bloque au demarrage. Verifie en isolant le contenu du mecanisme
   (`work/dq9_F.nds` : meme agrandissement rempli de zeros, aucune redirection,
   bloque aussi). Module conserve pour memoire : `scripts/patch_itcm.py`.

3. LE CODE MORT. `0x02002CB8`, 1 888 octets, muet sur DEUX sessions de
   surveillance d'execution avec temoin positif valide (`Allocate` a 5 692 puis
   1 754). Ecrit par-dessus : la ROM se bloque au demarrage (`work/dq9_G.nds`).
   Il etait donc appele -- pendant l'amorcage, ou par une table construite a
   l'execution, la reserve exacte que le 33 avait formulee. **La surveillance
   d'execution ne suffit pas non plus.**

CE QU'ON FAIT A LA PLACE. On demande la memoire a `SafeAllocator::Allocate`.
L'allocateur du jeu GARANTIT que le bloc est libre : plus de canari, plus de
surveillance, plus de « probablement ». Le code du chargeur vit dans un fichier
ajoute a la ROM, lu dans ce bloc a chaque montage.

LES QUATRE PRIMITIVES, toutes identifiees par desassemblage :

    0x02032554(tas, taille)            SafeAllocator::Allocate
    0x020750A8(chemin, tampon, &taille) lecture d'un fichier NitroFS
    0x020C8300(adresse, taille)        DC_FlushRange   (vide le cache de donnees)
    0x020C833C(adresse, taille)        IC_InvalidateRange

Les deux dernieres sont indispensables : on ecrit le code par le cache de
donnees, et le prefetch d'instructions ne le verrait pas.

UN SEUL RELAIS, PAS SIX. L'adresse du bloc change a chaque montage, donc les
sites d'appel ne peuvent pas y brancher en dur. Un relais par site couterait
48 octets d'espace possede, qu'on n'a pas. Mais les six sites peuvent partager
LE MEME relais : `lr` vaut « site + 4 » a l'entree, donc le blob identifie son
appelant par comparaison. Le routage coute une vingtaine d'instructions DANS le
blob, ou la place est gratuite, et le relais tombe a huit octets :

    relais:  ldr pc, [pc, #-4]      ; saute a l'adresse du mot suivant
             .word 0                ; rempli par l'amorce a chaque montage

FORMAT DU BLOB. Un en-tete d'un mot -- le deplacement du routeur -- puis le
code. L'amorce n'a donc qu'un mot a lire pour savoir ou brancher, et le blob
reste reassemblable sans toucher a l'amorce.

CE QUI RESTE A FAIRE ET N'EST PAS ECRIT ICI : le blob lui-meme (le chargeur, ses
six greffes et le routeur), assemble pour une adresse de base nulle et donc
entierement relatif, ce qui suppose de remplacer chaque `bl cible` absolu par
`ldr ip, [pc, #x] ; mov lr, pc ; bx ip`. Le blob a 1 680 octets devant lui : ce
cout est indolore, contrairement a tout ce qu'on a essaye jusqu'ici.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import capstone
import ndspy.code
import ndspy.codeCompression as cc

import patch_blob
from patch_hasard import (assembler, bl, BASE_ARM9,
                          ZONE_LIBRE, GREFFE_A2, GREFFE_B, TAILLE_TIREUR,
                          GREFFE_C, MODE_RENDRE, COMPRESSED_END, OVL)

# --- les primitives du jeu ---
ALLOUE = 0x02032554               # SafeAllocator::Allocate(tas, taille)
LIT_FICHIER = 0x020750A8          # (chemin, tampon, &taille) -> pointeur
DC_FLUSH = 0x020C8300             # (adresse, taille)
IC_INVALIDE = 0x020C833C          # (adresse, taille)
PRECHARGEUR = 0x021A28A8          # ce que le site qu'on remplace appelait

NOM_BLOB = "dq9rand.bin"          # le fichier qu'on ajoute a la ROM
TAILLE_BLOB = 4096                # la plage de code a synchroniser
# LE TAMPON N'EST PAS LA DESTINATION, c'est le plan de travail du systeme de
# fichiers -- et la VALEUR DE RETOUR pointe sur le contenu lu. L'appelant du jeu
# le montre : `bl 0x20750A8` puis `movs r4, r0`, et c'est r4 qui porte les
# donnees (0x0209A410). Avoir cru que r1 etait la destination a produit un abort
# a `0xFFFF0108` : `ldr r1, [r5]` lisait le tampon au lieu du blob, et on sautait
# dans le vide (lr = 34793DFE).
# QUATRE KIO, ET NON SEIZE. Ce tampon est pris SUR LE TAS DES MODELES, un frame
# heap : rien ne le rend avant le demontage de la carte. Mesure sur le terrain,
# avec la table source enfin batie : le tas y est plein a 188 180 sur 188 832 --
# 652 octets libres -- parce que la reserve de 32 Kio que la borne garde pour le
# chargement a la demande etait amputee de moitie par ce seul tampon. Le blob
# fait 900 octets et le systeme de fichiers travaille par secteurs : 4 Kio
# suffisent, et rendent 12 Kio au chargement a la demande.
TAILLE_TAMPON = 0x1000            # 4 Kio de plan de travail pour le FS

# `0x113C` n'est pas un immediat ARM encodable, d'ou les deux additions.
CTX_TAS_MODELES_HAUT = 0x1100
CTX_TAS_MODELES_BAS = 0x3C


def relais(adr):
    """Huit octets : saute a l'adresse contenue dans le mot suivant.

    `pc` vaut « ici + 8 » a l'execution, donc `[pc, #-4]` designe le mot place
    immediatement apres l'instruction. Le mot vaut zero jusqu'a ce que l'amorce
    le remplisse ; un site appele avant le premier montage sauterait donc a
    l'adresse 0 -- cas impossible en pratique, le chargeur n'etant sollicite que
    par l'apparition, qui suit toujours un montage.
    """
    # Le mot est DECLARE comme litteral, pas ajoute a la main : `assembler()`
    # verifie que tout acces pc-relatif tombe dans le pool, et il a raison de le
    # faire -- deux pannes couteuses du projet viennent d'un deplacement ecrit a
    # la main (58, 61). Un pool d'un mot le place exactement a `adr + 4`, donc
    # `{L0}` vaut -4.
    return assembler([
        "ldr pc, [pc, #{L0}]",
    ], adr, litteraux=(0,))


def amorce(adr, chemin_litteral):
    """Alloue, lit le blob, synchronise les caches, installe, et enchaine.

    Entree  r0 = le contexte de terrain, r5 = la taille du tas des modeles --
            ceux que le montage tient au site `0x021A30FC bl PRECHARGEUR`.
    Tourne a CHAQUE montage.

    ELLE PRESERVE CE QUE LA SUITE ATTEND : le talon de source, dans le blob, lit
    `r0` (le contexte) et `r5` (la taille du tas, pour decider si la carte porte
    des monstres). D'ou le `push {r0, r4, r5, lr}` : EMPILER r0 plutot que le
    recopier dans r4 economise le `mov r4, r0` de l'entree ET les deux `mov r0,
    r4` des sorties -- douze octets, sur un budget de 124.

    L'INSTALLATEUR REND L'ADRESSE DU TALON DANS r1 : le site reste accroche a
    l'amorce pour toujours, et elle ne peut pas connaitre a la construction une
    adresse qui change a chaque montage. `r1` plutot que `r0` pour que le `pop`
    de restitution serve aussi de dernier mot avant le saut.

    Sur echec -- allocation refusee, fichier absent -- on enchaine directement
    sur le prechargeur PAR UN BRANCHEMENT RELATIF : `PRECHARGEUR` est dans la
    portee des 32 Mio, donc il ne coute pas de litteral. Le jeu se comporte
    alors exactement comme sans chargeur.
    """
    return assembler([
        "push {r0, r4, r5, lr}",            # r4 : l'alignement de la pile
        # 1. allouer sur le tas des modeles, ou la borne a laisse 50 a 92 Ko
        "add r0, r0, #%d" % CTX_TAS_MODELES_HAUT,
        "add r0, r0, #%d" % CTX_TAS_MODELES_BAS,
        "mov r1, #%d" % TAILLE_TAMPON,
        "bl #%d" % ALLOUE,
        "movs r5, r0",                      # le plan de travail
        "beq #{@sortie}",
        # 2. lire le fichier : r1 est le PLAN DE TRAVAIL, et c'est la valeur de
        #    retour qui pointe sur le contenu (cf. 0x0209A410)
        "ldr r0, [pc, #{L0}]",              # le chemin
        "mov r1, r5",
        "mov r2, #0",                       # la taille ne nous sert pas
        "bl #%d" % LIT_FICHIER,
        "movs r5, r0",                      # LA VALEUR DE RETOUR est le blob
        "beq #{@sortie}",
        # 3. synchroniser : on a ecrit du CODE par le cache de donnees, et le
        #    prefetch d'instructions ne le verrait pas. Les deux primitives sont
        #    des feuilles qui ecrasent r0 et r1, d'ou les deux rechargements.
        "mov r0, r5",
        "mov r1, #%d" % TAILLE_BLOB,
        "bl #%d" % DC_FLUSH,
        "mov r0, r5",
        "mov r1, #%d" % TAILLE_BLOB,
        "bl #%d" % IC_INVALIDE,
        # 4. installer, puis enchainer sur le talon que l'installateur rend
        "ldr r1, [r5]",                     # en-tete : son deplacement
        "add r1, r1, r5",
        "mov r0, r5",                       # la base, en argument
        "mov lr, pc",
        "bx r1",
        "pop {r0, r4, r5, lr}",             # contexte et taille du tas restitues
        "bx r1",                            # il batira la table puis prechargera
        "sortie:",
        "pop {r0, r4, r5, lr}",
        "b #%d" % PRECHARGEUR,
    ], adr, litteraux=(chemin_litteral,))


# --- la disposition finale de l'espace POSSEDE ---
#
# Le demenagement du portier, de l'emprunt et du talon de source dans le blob
# libere tout le reste : la region du tireur, ROT_B, ROT_C, GREFFE_C2. Il ne
# reste dans l'ARM9 que ce qui doit y etre.
#
#   zone +0x00       bitmap des especes autorisees        48 o
#   zone +0x30       greffe A2, INTACTE                  144 o
#   0x02073FEC       le tireur, deux instructions          8 o
#   0x02073FF4       L'AMORCE                            116 o  -> 124 sur 132
#   0x020F1CB8       le miroir du compte de la table source  16 o
#   0x020F1CC8       la chaine du chemin du fichier          16 o
#
# LA GREFFE A2 RESTE ENTIERE. Elle avait ete degraissee de 144 a 92 octets pour
# loger l'amorce juste derriere elle, dans la zone -- une greffe que le joueur
# avait validee en jeu, modifiee sans etre retestee seule. L'amorce vit
# desormais dans la fonction du tireur, dont la greffe B ne garde que huit
# octets : 124 restent libres, et l'amorce degraissee en fait 116.
AMORCE = GREFFE_B + 8             # derriere le tireur, dans sa propre fonction

# LE TALON DE DEMONTAGE, et pourquoi il est indispensable.
#
# Le blob vit dans le tas des modeles, qui meurt avec la carte. A l'entree en
# combat le contexte de terrain est demonte -- mesure sur la savestate du
# joueur : `ctx+0x113C` et `ctx+0x1244` valent tous deux zero -- et la memoire du
# blob est aussitot reprise. Les douze sites gardent pourtant leur `bl` : le
# premier rappele saute dans des donnees, et le jeu part au vecteur d'exception
# (`PC = 0xFFFF0108`, `lr = 0235ACDC`, le mot qui precede n'etant plus une
# instruction). C'est l'ecran noir, une entree en combat sur deux ou trois.
#
# Le demontage du tas des modeles se lit en clair dans l'overlay 17 :
#
#   021A31A4  add r0, r6, #0x13c ; add r0, r0, #0x1000 ; bl 0x20328c4
#   021A31B8  ... bl 0x2032740      (vider)
#   021A31C4  ... bl 0x203248c      (detruire)
#
# On accroche le premier appel : le blob y est encore vivant, c'est le dernier
# instant ou il peut se retirer. Le talon ne connait du blob qu'un mot fixe dans
# l'ARM9, ecrit par l'installateur -- il n'a donc rien a savoir de l'allocation.
DEMONTAGE = 0x021A31AC            # bl EST_VALIDE, en tete du demontage
EST_VALIDE = 0x020328C4           # ce que ce site appelait
TALON_DEMONTAGE = ZONE_LIBRE + 0xC0   # derriere le bitmap et la greffe A2
BLOB_BASE = patch_blob.BLOB_BASE
# LES SEIZE PREMIERS OCTETS DE `GREFFE_C` RESTENT A SRC. Le talon de source y
# recopie son compte (`SRC_MIROIR`, patch_blob) pour que `talon_borne`, qui vit
# dans l'ARM9, puisse savoir si la carte porte des monstres. La chaine se pose
# donc derriere : 16 octets de miroir, 16 de chemin, sur les 40 du morceau.
CHEMIN_ADR = GREFFE_C + 0x10
SITE_MONTAGE = 0x021A30FC         # bl PRECHARGEUR, dans le montage

ATTENDU_OVL = {SITE_MONTAGE: "bl #0x21a28a8", DEMONTAGE: "bl #0x20328c4"}


def tireur(adr):
    """Le tireur de terrain, en deux instructions.

    La greffe A2 sait deja tirer une espece valide dans le bitmap des 256 et la
    RENDRE quand le bit 15 de r1 est arme. Le tireur n'a donc plus qu'a l'appeler
    dans ce mode : chaque apparition demande une espece neuve tiree dans tout le
    bestiaire, au lieu d'une des especes deja chargees.
    """
    return assembler([
        "mov r1, #%d" % MODE_RENDRE,
        "b #%d" % GREFFE_A2,
    ], adr)


def talon_demontage(adr):
    """Retire le blob avant que son tas meure, puis enchaine.

    Entree  r0 = `ctx+0x113C`, l'allocateur du tas des modeles -- l'argument que
            le site preparait deja pour `EST_VALIDE`. On le preserve, ainsi que
            `lr`, et on finit par un branchement relatif sur l'appel d'origine :
            le site se comporte exactement comme avant, avec un detour.

    Si `BLOB_BASE` est nul -- amorce en echec, ou desinstallation deja faite --
    le talon ne fait rien du tout. C'est le cas normal sur une carte ou l'amorce
    n'a pas pu allouer, et le jeu s'y comporte comme le vanilla.
    """
    return assembler([
        "push {r0, lr}",
        "ldr r0, [pc, #{L0}]",              # BLOB_BASE
        "ldr r0, [r0]",
        "cmp r0, #0",
        "ldrne ip, [r0, #4]",               # l'en-tete : le desinstalleur
        "addne ip, ip, r0",
        "movne lr, pc",
        "bxne ip",
        "pop {r0, lr}",
        "b #%d" % EST_VALIDE,
    ], adr, litteraux=(BLOB_BASE,))


def ajouter_fichier(rom, contenu):
    """Ajoute un fichier a NitroFS et rend son chemin.

    L'IDENTIFIANT D'UN FICHIER EST IMPLICITE : il decoule de l'ordre des noms
    dans l'arborescence, pas d'un champ. Ajouter un nom dans `data/prm` lui donne
    donc l'identifiant SUIVANT DE CE DOSSIER -- celui d'un fichier existant -- et
    decale tout ce qui suit. Faute payee : le jeu lisait une archive GPC2 de
    52 320 octets au lieu du blob, et l'amorce sautait dans le vide (abort a
    `0xFFFF0108`, lr = 34793DFE).

    Il faut donc ajouter le nom dans le dossier qui porte les DERNIERS
    identifiants, pour que le notre soit le dernier et corresponde a la donnee
    ajoutee en fin de `rom.files`.
    """
    def parcours(dossier, chemin=""):
        out = [(dossier.firstID + i, chemin, dossier)
               for i in range(len(dossier.files))]
        for nom, sd in dossier.folders:
            out += parcours(sd, (chemin + "/" + nom) if chemin else nom)
        return out

    tout = parcours(rom.filenames)
    if not tout:
        raise SystemExit("arborescence NitroFS vide")
    _, chemin, dossier = max(tout, key=lambda t: t[0])
    dossier.files.append(NOM_BLOB)
    complet = (chemin + "/" + NOM_BLOB) if chemin else NOM_BLOB
    vu = rom.filenames.idOf(complet)
    if vu is None:
        raise SystemExit(f"{complet} : le nom n'a pas pris")
    # ON INSERE, on n'ajoute pas. La ROM porte des fichiers SANS NOM en fin de
    # table -- l'identifiant que le nom vient de recevoir n'est donc pas
    # forcement le dernier. Inserer decale la suite, ce qui est exactement la
    # semantique de NitroFS quand un nom s'ajoute dans l'arborescence.
    rom.files.insert(vu, contenu)
    if bytes(rom.files[vu]) != bytes(contenu):
        raise SystemExit("l'insertion n'a pas mis le contenu au bon identifiant")
    return complet


def patcher(rom, bavard=True, plafond=None, etapes=4):
    """Pose l'amorce, la chaine, le tireur, et ajoute le fichier du blob.

    A appeler APRES patch_hasard (qui pose le bitmap et la greffe A2) et
    patch_place (qui borne la confiscation). Remplace entierement patch_portier
    et patch_chargeur : tout ce qu'ils posaient vit desormais dans le blob.
    """
    arm9 = bytearray(cc.decompress(bytes(rom.arm9)))
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)

    if plafond is None:
        plafond = patch_blob.PLAFOND
    # Les mots d'origine des douze sites, lus dans l'overlay : c'est ce que le
    # desinstalleur y remettra.
    ovl_lecture = rom.loadArm9Overlays()[OVL]
    base_ovl = ovl_lecture.ramAddress
    brut = bytes(ovl_lecture.data)
    originaux = {}
    for site in patch_blob.SITES_PATCHES:
        # LE TREIZIEME SITE VIT DANS L'ARM9, pas dans l'overlay : c'est le `bl`
        # du lecteur de fichier, par lequel passe le bloc du modele. On lit donc
        # chaque mot d'origine dans le module qui le porte.
        if base_ovl <= site < base_ovl + len(brut):
            originaux[site] = struct.unpack_from("<I", brut, site - base_ovl)[0]
        else:
            originaux[site] = struct.unpack_from("<I", arm9, site - BASE_ARM9)[0]
    # LA LISTE DES ESPECES TIRABLES, la meme que le bitmap : c'est elle que le
    # blob fera batir en noeuds de comportement au montage.
    from patch_hasard import especes_tirables
    blob, etiq = patch_blob.construire(plafond, originaux=originaux,
                                       especes=especes_tirables())
    if len(blob) > TAILLE_BLOB:
        raise SystemExit(f"blob de {len(blob)} o : l'amorce n'en alloue que "
                         f"{TAILLE_BLOB}")

    # --- le fichier d'abord : son chemin depend du dossier qui porte les
    # --- derniers identifiants, donc on ne le connait qu'apres l'avoir ajoute
    chemin_txt = ajouter_fichier(rom, blob)

    # --- la chaine du chemin, dans la place que SRC a liberee ---
    chemin = chemin_txt.encode("ascii") + b"\x00"
    o = CHEMIN_ADR - BASE_ARM9
    if any(arm9[o:o + len(chemin)]):
        raise SystemExit(f"{CHEMIN_ADR:#010x} n'est pas libre pour la chaine")
    arm9[o:o + len(chemin)] = chemin

    # --- le tireur ET l'amorce, dans la fonction du tireur ---
    #
    # L'ORDRE EST IMPOSE : on efface la fonction entiere, puis on pose le tireur
    # a son entree -- c'est l'adresse que le jeu appelle, elle ne peut pas
    # bouger -- et l'amorce derriere lui. Ecrire le tireur apres l'amorce
    # l'effacerait, puisque l'effacement porte sur les 132 octets.
    t = tireur(GREFFE_B)
    code = amorce(AMORCE, CHEMIN_ADR)
    if len(t) + len(code) > TAILLE_TIREUR:
        raise SystemExit(f"tireur {len(t)} o + amorce {len(code)} o : la "
                         f"fonction n'en tient que {TAILLE_TIREUR}")
    if AMORCE != GREFFE_B + len(t):
        raise SystemExit(f"le tireur fait {len(t)} o, l'amorce est posee a "
                         f"+{AMORCE - GREFFE_B}")
    o = GREFFE_B - BASE_ARM9
    arm9[o:o + TAILLE_TIREUR] = bytes(TAILLE_TIREUR)
    arm9[o:o + len(t)] = t
    arm9[o + len(t):o + len(t) + len(code)] = code

    # --- le talon de demontage, dans le bourrage que la zone garde encore ---
    td = talon_demontage(TALON_DEMONTAGE)
    o = TALON_DEMONTAGE - BASE_ARM9
    if any(arm9[o:o + len(td)]):
        raise SystemExit(f"{TALON_DEMONTAGE:#010x} n'est pas libre pour le "
                         f"talon de demontage ({len(td)} o)")
    arm9[o:o + len(td)] = td

    struct.pack_into("<I", arm9, COMPRESSED_END, 0)
    rom.arm9 = bytes(arm9)

    # --- l'accroche, dans l'overlay 17 ---
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
    data[SITE_MONTAGE - base:SITE_MONTAGE - base + 4] = bl(SITE_MONTAGE, AMORCE)
    data[DEMONTAGE - base:DEMONTAGE - base + 4] = bl(DEMONTAGE, TALON_DEMONTAGE)
    o17.data = bytes(data)
    o17.compressed = False
    o17.compressedSize = len(data)
    rom.files[o17.fileID] = bytes(data)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)

    # LES AUTRES SITES NE SONT PAS PATCHES ICI : c'est l'installateur du blob qui
    # les reecrit a l'execution, puisque leurs cibles n'ont pas d'adresse fixe.
    # La ROM garde donc ses douze appels d'origine, et un jeu sans le fichier --
    # ou dont l'allocation echoue -- se comporte exactement comme le vanilla.
    #
    # ET LE FICHIER N'EST AJOUTE QU'UNE FOIS. Il l'etait deux : une deuxieme
    # entree `dq9rand.bin` dans le meme dossier, qui redecalait tous les
    # identifiants suivants et faisait lire au jeu un fichier decale d'un rang.
    # Reliquat d'une reecriture par substitution de texte.

    if bavard:
        print(f"  amorce   : {len(code)} o a {AMORCE:#010x} "
              f"(fonction du tireur : {len(t) + len(code)} sur {TAILLE_TIREUR})")
        print(f"  chaine   : {chemin_txt!r} a {CHEMIN_ADR:#010x}")
        print(f"  demontage: {len(td)} o a {TALON_DEMONTAGE:#010x}, accroche a "
              f"{DEMONTAGE:#010x}")
        print(f"  tireur   : {len(t)} o a {GREFFE_B:#010x}, tire dans le bitmap")
        print(f"  blob     : {len(blob)} o dans {chemin_txt}, {len(etiq)} etiquettes, "
              f"12 sites reecrits a l'execution")
    return len(blob)
