#!/usr/bin/env python3
"""v14 : tirage des especes AU CHARGEMENT DE LA ZONE, et non a la construction.

LE VERROU (docs/FORMAT.md 24). Une espece ne peut apparaitre que si son modele
est precharge, et la liste de prechargement ne compte que 12 emplacements dans la
structure de carte, avec 2 octets de marge avant la structure suivante. Aucune
modification de donnees ne franchit ce plafond : v13 s'arrete a 8 especes figees
par zone.

LE CONTOURNEMENT. On ne touche plus au nombre d'emplacements, on change ce qu'on
y met -- et on le change A CHAQUE CHARGEMENT DE ZONE. Deux greffes :

  A. le parseur d'`encmons` remplit la liste avec des especes TIREES AU HASARD
     parmi les 260 especes de terrain, au lieu de celles du fichier ;
  B. le tireur de terrain rend une espece prise dans cette meme liste, au lieu
     de la table ponderee du groupe.

B garantit l'invariant sans rien partager : au moment du tirage les deux
structures sont baties depuis longtemps, donc l'ordre de parsage des deux
fichiers n'entre pas en jeu. C'etait le seul point fragile du montage.

CE QUE LE DESASSEMBLAGE A DONNE, ET QUI SIMPLIFIE TOUT :

  0x02032380  rand_below(max) -> u32 dans [0, max[   le generateur du jeu
  0x02109BC8  global : [[global]] = liste de prechargement
              ids en u16 a +0x00, nombre en u16 a +0x18
  0x0209C09C  AddSpecies(liste, id), plafond 12, appelee 2x par le parseur
              d'encmons (ARM9) et 4x par l'overlay 17 (especes en dur)
  0x02073FEC  ChooseFieldMonsterId(groupe) -> id sur 12 bits, ou -1
              32 instructions : la version de remplacement en fait 13

On ne patche que les 2 appels ARM9 vers AddSpecies : les 4 de l'overlay 17
ajoutent des especes scenaristiques qui doivent rester.

OU LOGE LE CODE. 280 octets a zero a 0x020E7268, verifies en jeu : 0 ecriture et
toujours a zero apres 70 s incluant un chargement de zone (scripts/lua/
sonde_trou.lua). On y met un bitmap de 64 octets -- un bit par identifiant,
0 a 511 -- puis la greffe A. La greffe B tient dans le corps du tireur.

LES BOSS. Ils sont simplement absents du bitmap : l'exclusion est totale et ne
coute pas une instruction.

Usage: python scripts/patch_hasard.py <rom.nds> <sortie.nds>
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capstone
import keystone

from monstres_nommes import MONSTRES

# LE PLAFOND DE TAILLE D'UN MODELE. 32 Kio tant que le prechargeur devait en
# tenir cinq a onze d'un coup ; l'eviction ayant supprime cette contrainte, on le
# porte au-dessus du plus gros modele du jeu (42 408 octets) pour n'ecarter plus
# personne.
PLAFOND_MODELE = 48 * 1024
ROM_ATTENDUE = ("Dragon Quest IX - Sentinels of the Starry Skies "
                "(Europe) (En,Fr,De,Es,It).nds")
import ndspy.code
import ndspy.codeCompression as cc
import ndspy.rom
from agrandir_zones import construire_pool

BASE_ARM9 = 0x02000000
ZONE_LIBRE = 0x020E7268          # 280 octets de bourrage verifies
TAILLE_LIBRE = 280

# LE PLAN MEMOIRE, ET POURQUOI IL EST SI SERRE.
#
# Tout le code ajoute doit tenir dans du bourrage existant : l'image ARM9
# n'offre que 529 octets a zero en tout (six regions), et l'overlay 17 aucune --
# ses deux « trous » de 48 octets sont en realite des enregistrements de 0x34
# presque vides dans une table que le jeu lit. Les trois candidats retenus ici
# ont passe le test du canari : motif ecrit en RAM, releve intact apres huit
# marches et deux chargements de carte complets (scripts/lua/canari.lua).
#
#   zone +0x000  48 o  bitmap des especes autorisees, UN bit par espece
#   zone +0x030 144 o  greffe A2 (tirage et validation)
#   zone +0x0C0  32 o  greffe C, dernier morceau
#   zone +0x0E0  48 o  rotation, morceau D (boucle de tirage)
#   zone +0x110   4 o  compteur de cadence de la rotation
#   0x02073FEC   68 o  greffe B (tireur de terrain)
#   0x02074030   64 o  rotation, morceau A     (queue morte du tireur)
#   0x020F1CB8   40 o  greffe C, morceau 1
#   0x020E7C78   40 o  greffe C, morceau 2
#   0x020E8888   40 o  greffe C, morceau 3
#   0x020F1D2C   52 o  rotation, morceau C
#   0x020F1E40   72 o  rotation, morceau B
#
# BITMAP DES ESPECES AUTORISEES, UN SEUL BIT PAR ESPECE.
#
# ELLE A PORTE DEUX BITS -- une classe de taille -- tant que la greffe A2
# facturait un budget. Le budget est mort (58) : ce qui protegeait des monstres
# invisibles, c'est la greffe B, qui ne tire que parmi les modeles charges. Un
# bit suffit donc, et les 48 octets ainsi liberes sont exactement les douze mots
# qui manquaient pour ecrire la liste EN PLACE (60).
#
# Le vrai plafond n'est pas le nombre de modeles mais leur POIDS : le tas des
# modeles fait 187 440 octets mesures, et un modele de terrain coute de 5 508 a
# 61 368 octets (docs/FORMAT.md 47). Filtrer par taille maximale ecartait 158
# especes sur 260 ; un budget cumule les rend toutes atteignables, au prix de
# zones qui portent parfois dix especes au lieu de douze.
#
#   classe 0 : espece interdite (boss, sans modele, ou modele > 32 Kio)
#   classe 1 : <= 12 Kio     cout 6 unites de 2 Kio
#   classe 2 : <= 20 Kio     cout 10
#   classe 3 : <= 32 Kio     cout 16
#
# ELLE NE COUVRE PLUS 512 IDENTIFIANTS MAIS 384. Le plus grand identifiant de
# terrain vaut 334 ; passer de 512 a 384 fait tomber la table de 128 a 96
# octets et libere les 32 octets ou loge le dernier morceau de la greffe C.
# 384 reste un immediat ARM encodable, 336 ne l'est pas.
TABLE_CLASSES = ZONE_LIBRE       # 48 octets
BORNE = 384                      # identifiants balayes : 0 a 383
BORNES_CLASSES = (12288, 20480, 32768)
C_ZONE = ZONE_LIBRE + 0xC0       # 32 o : greffe C, dernier morceau
ROT_D = ZONE_LIBRE + 0xE0        # 48 o : rotation, boucle de tirage
COMPTEUR = ZONE_LIBRE + 0x110     # 4 octets : cadence de la rotation
CARTE_MOT = ZONE_LIBRE + 0x114    # 4 octets : la derniere carte vue
# LE BUDGET A DISPARU, ET LA MESURE L'A VOULU.
#
# Il existait pour eviter les monstres invisibles : une espece dont le modele ne
# tenait pas dans le tas restait dans la liste, le tireur la rendait quand meme,
# et l'apparition creait un acteur sans modele. La greffe B lisant desormais les
# modeles CHARGES, le cas ne peut plus se produire.
#
# Et il ne protegeait de rien : mesure de controle sur v34 -- douze especes dans
# la liste, quatre modeles charges, 126 984 octets encore libres sur les 187 392
# du tas. Ce qui bride reellement, c'est le portier : le conteneur ne porte que
# 150 des 256 especes. La greffe A2 verifie donc l'appartenance au conteneur a
# la place, et les deux mots liberes dans la rotation servent a un garde-fou.
GREFFE_A2 = ZONE_LIBRE + 0x30    # 144 octets
TAILLE_A2 = 144
# MODE DE LA GREFFE A2. Le parseur d'encmons l'appelle a la place de
# `AddSpecies` avec r1 = identifiant lu dans le fichier, toujours inferieur a
# 512 : le bit 15 est donc libre pour porter un mode. Mis a 1, la greffe REND
# l'espece dans r0 au lieu de l'ajouter -- ce dont la rotation a besoin pour
# ecrire la liste en place.
MODE_RENDRE = 0x8000

# LA TABLE DES EMPLACEMENTS DE MODELE, lue en dur plutot que par son accesseur.
# `0x0200F398` ne fait que rendre ce pointeur (`ldr r0, [pc]`), et `GetSlot`
# (`0x0200FD80`) que `[table + 8 + i*4]` apres bornage. Les greffes lisent donc
# directement, ce qui economise un appel et un registre.
TABLE_EMPL = 0x020F33D8 + 8      # entree 0
EMPL_MODELES = 7                 # les modeles de monstre de terrain : 7 a 18
EMPL_ACTEURS = 0x70              # les acteurs : 0x70 + 12 * variante

RAND = 0x02032380                # rand_below(max)
ADD_ESPECE = 0x0209C09C          # AddSpecies(liste, id), plafond 12
APPELS_ADD = (0x0209BFD8, 0x0209BFF0)
MODULE_PARAMS = 0xBBC - 0x1C     # nitrocode 0xDEC00621 moins 0x1C
COMPRESSED_END = MODULE_PARAMS + 0x14
ESSAIS = 24                      # tentatives de tirage avant repli
CHERCHE_CONTENEUR = 0x0206F500   # Lookup(conteneur, espece) -> enreg. ou 0

# --- les regions de code, et ce que chacune accueille ---
GREFFE_B = 0x02073FEC            # 68 o : le tireur de terrain, reecrit
TAILLE_TIREUR = 132              # taille de la fonction d'origine (symboles)
ROT_A = 0x02074030               # 64 o : queue morte de la meme fonction
ROT_B = 0x020F1E40               # 72 o
ROT_C = 0x020F1D2C               # 52 o
GREFFE_C = 0x020F1CB8            # 40 o + 40 o + 40 o + 32 o, en quatre morceaux
GREFFE_C2 = 0x020E7C78
GREFFE_C3 = 0x020E8888
# ROT_E occupe la queue libre du morceau C : celui-ci n'utilise que 24 de ses
# 52 octets, et la fin du compteur ne tenait plus dans le morceau A.
ROT_E = ROT_C + 24
PLACES = {GREFFE_B: 68, ROT_A: 64, ROT_B: 72, ROT_C: 24, ROT_D: 48, ROT_E: 28,
          GREFFE_C: 40, GREFFE_C2: 40, GREFFE_C3: 40, C_ZONE: 32}

# LES DEUX CONTENEURS, ET IL FAUT LES DEUX. Le prechargement (0x021A29A4) comme
# l'apparition (0x021A2180) exigent l'espece dans `carte+0x2F8` ET dans
# `carte+0x304`. Le premier porte en outre le code de modele du fichier a
# charger (`ldr r2, [r0, #4]` en 0x021A29B4) : on ne peut pas le contourner.
#
# Les deux constructeurs ont la meme forme : un tampon local de 0x18 octets, un
# `bl CopyList`, puis la construction. Meme paire de patches pour chacun.
PATCHES_C = (
    # (bl CopyList, add r1 sp #off, decalage du tampon local)
    (0x021B52C4, 0x021B52E0, 0x18),     # conteneur carte+0x2F8
    (0x021B53C8, 0x021B53DC, 0x10),     # conteneur carte+0x304
)
MONTAGE = 0x021A2FA0             # le montage complet des monstres d'une carte
GET_CTX = 0x0218B5B0             # GetFieldCtx() = [0x021D82E4]
CARTE = 0x02027CC0               # rend la structure de carte
ACCROCHE = 0x020733F0            # `movs r7, r0`, dans le tic de terrain
ATTENDU_ACCROCHE = "movs r7, r0"
# LA CADENCE SE COMPTE EN APPELS DU TIC D'APPARITION, PAS EN IMAGES.
# Le tic n'est appele que lorsque la carte manque de symboles : mesure sur la
# sauvegarde du joueur, 600 appels en une minute de marche, puis plus rien des
# que la carte est repeuplee. A 1 024 la rotation ne partait donc qu'une fois.
# A 256 le joueur constate une micro-saccade « toutes les 10 secondes environ » :
# le montage demonte et recharge une dizaine de modeles d'un coup, et ce cout est
# fixe -- seule la cadence se regle. 512 la ramene a une vingtaine de secondes.
PERIODE = 512
# TROIS CHOSES VALAIENT 12 ET N'AVAIENT AUCUNE RAISON DE RESTER LIEES :
#   EMPLACEMENTS   les 12 emplacements de modele de la table (limite du moteur)
#                  et les 12 emplacements d'acteur d'une variante de carte
#   TIRAGES        le nombre d'especes que la rotation tire -- reglable
EMPLACEMENTS = 12
TIRAGES = 12
OVL = 17

INTERDITES = ("movw", "movt", "sdiv", "udiv", "blx")

# Les instructions attendues aux points de greffe. On refuse de patcher si la
# ROM ne les presente pas : mieux vaut ne rien produire qu'une ROM muette.
ATTENDU = {
    0x0209BFD8: "bl #0x209c09c",
    0x0209BFF0: "bl #0x209c09c",
    GREFFE_B: "push {r3, r4, r5, lr}",
}


def assembler(lignes, adr, litteraux=(), etiquettes_out=None):
    """Assemble une liste d'instructions et place les litteraux a la suite.

    ETIQUETTES. Une ligne de la forme `"nom:"` ne produit pas d'instruction :
    elle nomme l'adresse courante, et `{@nom}` la restitue partout ailleurs.
    C'est indispensable, pas confortable : la version precedente exigeait des
    index d'instruction comptes a la main (`adr + 4 * 21`), et une greffe dont
    le branchement tombe une instruction a cote est parfaitement assemblable.
    Faute payee sur la greffe A2.

    `{Lj}` dans une instruction est remplace par le deplacement pc-relatif du
    litteral j. Keystone ne construit pas de pool de litteraux, et surtout il
    emet MOVW/MOVT sans prevenir pour les immediats non encodables -- or ces
    instructions n'existent pas sur l'ARM9 du DS. D'ou la relecture systematique
    du code produit, plus bas.
    """
    etiquettes, instructions = {}, []
    for l in lignes:
        if l.endswith(":") and " " not in l.strip():
            etiquettes[l[:-1].strip()] = adr + 4 * len(instructions)
        else:
            instructions.append(l)
    n = len(instructions)
    rendu = []
    for i, l in enumerate(instructions):
        # `{@@nom}` : le DEPLACEMENT pc-relatif jusqu'a l'etiquette, c'est-a-dire
        # `(ici + 8) - nom`. C'est ce qu'il faut pour atteindre une donnee placee
        # dans le meme bloc quand celui-ci est RELOGEABLE -- procede que la greffe
        # A2 utilise deja pour son bitmap (`sub r6, pc, #ecart`).
        #
        # POURQUOI L'ASSEMBLEUR LE CALCULE ET PAS NOUS. Un deplacement ecrit a la
        # main est la premiere cause de panne du projet : un litteral lu quatre
        # octets trop loin (58) et une sortie commune decalee d'une instruction
        # (61). La regle est donc absolue -- jamais d'adresse ni de deplacement
        # a la main, toujours une etiquette.
        # `{@@H:nom}` et `{@@L:nom}` : LA MEME CHOSE EN DEUX TEMPS, et c'est ce
        # qui la rend sure. Un `sub rX, pc, #d` exige que `d` soit un immediat
        # ARM -- huit bits tournes d'un rang pair -- et un blob qui grandit finit
        # toujours par produire un `d` qui ne l'est pas : 1 048 puis 1 044 ont
        # fait echouer deux assemblages. En decoupant en `d & 0xFF00` puis
        # `d & 0xFF`, les deux moities sont encodables par construction, quelle
        # que soit la taille du bloc. Le couple doit rester sur deux lignes
        # consecutives : la seconde retrouve le `d` de la premiere en ajoutant 4
        # a la sienne.
        for nom, cible in etiquettes.items():
            d = adr + 4 * i + 8 - cible
            if "{@@H:%s}" % nom in l:
                if not 0 <= d < 0x10000:
                    raise SystemExit(f"deplacement {d} hors de portee pour {nom}")
                l = l.replace("{@@H:%s}" % nom, str(d & 0xFF00))
            if "{@@L:%s}" % nom in l:
                # Le `d` de la PREMIERE ligne vaut celui d'ici MOINS quatre :
                # le deplacement croit avec l'adresse de l'instruction. L'avoir
                # pris a `+4` retranchait huit octets de trop, et le noeud
                # tombait avant le pool.
                l = l.replace("{@@L:%s}" % nom, str((d - 4) & 0xFF))
            l = l.replace("{@@%s}" % nom, str(d))
        for nom, cible in etiquettes.items():
            l = l.replace("{@%s}" % nom, str(cible))
        for j in range(len(litteraux)):
            l = l.replace("{L%d}" % j, str(4 * (n - i - 2) + 4 * j))
        # « {r4, r5} » est une liste de registres, pas un marqueur : on ne
        # cherche que les deux prefixes reellement utilises.
        if "{@" in l or "{L" in l:
            raise SystemExit(f"marqueur non resolu dans {l!r}")
        rendu.append(l)
    # Rendre la position des etiquettes : indispensable pour un bloc RELOGEABLE,
    # ou l'on doit ecrire des donnees (table de sites, mots de commande) a des
    # deplacements que seul l'assemblage connait.
    if etiquettes_out is not None:
        etiquettes_out.update(etiquettes)
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_ARM)
    try:
        code, _ = ks.asm(chr(10).join(rendu), adr)
    except keystone.KsError as e:
        # KEYSTONE NE DIT PAS QUELLE LIGNE. On la retrouve en les reprenant une
        # par une, APRES substitution -- c'est justement une substitution qui
        # rend une ligne invalide : un `sub rX, pc, #d` dont le deplacement a
        # cesse d'etre un immediat ARM encodable quand le bloc a grandi.
        for i, l in enumerate(rendu):
            try:
                ks.asm(l, adr + 4 * i)
            except keystone.KsError:
                raise SystemExit(f"ligne {i} inassemblable : {l!r} "
                                 f"(source : {instructions[i]!r})") from e
        raise SystemExit(f"assemblage refuse sans ligne fautive : {e}") from e
    code = bytes(code)
    if len(code) != 4 * n:
        raise SystemExit(f"assemblage inattendu : {len(code)} o pour {n} lignes")
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    pool = range(adr + 4 * n, adr + 4 * n + 4 * len(litteraux))
    for ins in md.disasm(code, adr):
        if ins.mnemonic.lower() in INTERDITES:
            raise SystemExit(f"{ins.mnemonic} {ins.op_str} : hors ARMv5TE")
        # TOUT ACCES PC-RELATIF DOIT TOMBER DANS LE POOL DE LITTERAUX.
        # Une greffe qui lit un mot voisin au lieu du sien produit une adresse
        # parfaitement valide en apparence et une exception de donnees au
        # premier appel -- faute payee une fois, sur la greffe B.
        if ins.mnemonic.lower().startswith("ldr") and "[pc, #" in ins.op_str:
            vise = ins.address + 8 + int(ins.op_str.split("[pc, #")[1].rstrip("]"), 0)
            if vise not in pool:
                raise SystemExit(
                    f"{ins.address:#010x} {ins.mnemonic} {ins.op_str} vise "
                    f"{vise:#010x}, hors du pool "
                    f"[{adr + 4 * n:#010x}, {adr + 4 * n + 4 * len(litteraux):#010x})")
    return code + b"".join(struct.pack("<I", v) for v in litteraux)


def greffe_a2(adr):
    """Tire une espece au hasard, la valide, et l'ajoute -- ou la rend.

    Entree  r0 = liste de prechargement, r1 = identifiant lu dans le fichier,
            dont le bit 15 (MODE_RENDRE) demande de RENDRE l'espece dans r0 au
            lieu de l'ajouter a la liste. Le parseur d'encmons passe toujours un
            identifiant inferieur a 512, donc ce bit est libre.

    UN SEUL FILTRE DEPUIS LA TABLE SOURCE. La validation d'appartenance au
    conteneur a disparu, et avec elle une douzaine d'instructions : le portier
    consulte desormais la table source des 438 especes (68), donc il TROUVE
    toujours l'espece, et toujours avec un vrai code de modele. Verifier ce que
    le conteneur de la zone en pense n'a plus de sens, et le test du code
    (`ldr r0,[r0,#4]` / `ldrb r0,[r0,#5]`) non plus.

    Les 64 octets ainsi rendus vont a l'amorce du chargeur -- la seule place
    possedee, c'est-a-dire jouee des heures, qui restait a prendre.

    CE QUE DISAIT L'ANCIENNE VERSION, conserve parce que la raison vaut encore
    si l'on revenait en arriere :

    Le bitmap ecarte les boss, les especes sans modele de terrain et celles dont
    le modele depasse 32 Kio. Puis, SI le conteneur connait l'espece, on verifie
    son enregistrement : certains portent en +0x04 un pointeur qui ne designe pas
    une chaine (18 sur 150, mesure), et le prechargeur les passe pourtant a
    `sprintf("%s_f.mon")`. Tous les codes valides font cinq caracteres, d'ou le
    zero attendu en +0x05.

    Mais on ACCEPTE l'espece que le conteneur ignore : au chargement d'une zone
    il porte encore celui de la zone precedente, et refuser ce qu'il ignore
    rejetait presque tout -- le joueur voyait zero monstre, puis un seul (60).
    """
    ecart = (adr + 3 * 4 + 8) - TABLE_CLASSES
    return assembler([
        "push {r4, r5, r6, r7, r8, lr}",
        "mov r4, r0",                       # la liste
        "ands r8, r1, #%d" % MODE_RENDRE,   # le mode, a l'abri des appels
        "sub r6, pc, #%d" % ecart,          # le bitmap
        # LE COMPTEUR NE PEUT PAS VIVRE DANS ip : `rand_below` l'ecrase, et la
        # boucle part a l'infini -- ecran noir a la transition, mesure faite.
        "mov r5, #%d" % ESSAIS,
        "essai:",
        "mov r0, #%d" % BORNE,
        "bl #%d" % RAND,
        "mov r7, r0",                       # l'espece tiree
        "mov r1, r0, lsr #3",               # 8 especes par octet
        "ldrb r1, [r6, r1]",
        "and r2, r0, #7",
        "mov r1, r1, lsr r2",
        "tst r1, #1",
        "beq #{@suivant}",                  # espece interdite
        "bl #%d" % CARTE,
        "cmp r0, #0",
        "beq #{@retenue}",                  # pas de carte : accepter sans test
        "add r0, r0, #0x2f8",               # le conteneur
        "mov r1, r7",
        "bl #%d" % CHERCHE_CONTENEUR,
        "cmp r0, #0",
        "beq #{@retenue}",                  # inconnu du conteneur : on accepte
        "ldr r0, [r0, #4]",                 # le code de modele
        "ldrb r0, [r0, #5]",                # son zero terminal
        "cmp r0, #0",
        "beq #{@retenue}",                  # code valide
        "suivant:",
        "subs r5, r5, #1",
        "bne #{@essai}",
        # dernier recours si les essais sont epuises : on tombe dans retenue
        "retenue:",
        "cmp r8, #0",
        "movne r0, r7",                     # mode rendu : l'espece dans r0
        "popne {r4, r5, r6, r7, r8, pc}",
        "mov r1, r7",
        "mov r0, r4",
        "pop {r4, r5, r6, r7, r8, lr}",
        "b #%d" % ADD_ESPECE,
    ], adr)


def tailles_par_code():
    """Rend {identifiant: taille du modele de terrain}, par le CODE du modele.

    POURQUOI PAS `work/tailles_modeles.txt`. Ce releve indexe par identifiant et
    il est incomplet : 400 entrees pour 441 monstres. Les manquants n'etaient
    pas sans modele -- `squelette` en a un de 14 880 octets, `dragon vert` de
    25 348 -- ils etaient simplement absents du fichier, et le bitmap les
    ecartait en silence. Vingt-trois noms du bestiaire sur 256 y passaient.

    On repart donc de la table de noms, qui donne le CODE du modele de chaque
    espece, et on mesure l'archive. Les variantes de couleur partagent le
    maillage de la premiere : `z000b` n'est pas un membre d'`enemy.gp2`, c'est
    `z000a` qui porte les deux. D'ou le repli sur la variante `a`.
    """
    import monnames
    import tailles_modeles
    par_code = tailles_modeles.mesurer()
    noms = monnames.charger(ROM_ATTENDUE, "fr")
    out = {}
    for i in range(BORNE):
        try:
            f = noms[i]
        except (KeyError, IndexError):
            continue
        if not (isinstance(f, dict) and f.get("modele")):
            continue
        code = f["modele"]
        n = par_code.get(code)
        if n is None and code[-1:].isalpha() and code[-1] != "a":
            n = par_code.get(code[:-1] + "a")
        if n:
            out[i] = n
    return out


def especes_tirables():
    """Rend la liste des identifiants que le tirage peut sortir.

    C'est exactement ce que `construire_bitmap` retient, mais sous forme de
    liste : le blob en a besoin pour faire batir un noeud de comportement par
    espece au montage. Le bitmap et cette liste doivent rester d'accord, d'ou le
    meme code de decision -- on relit le bitmap plutot que de le refaire.
    """
    from agrandir_zones import construire_pool
    terrain, hors = construire_pool(
        "Dragon Quest IX - Sentinels of the Starry Skies "
        "(Europe) (En,Fr,De,Es,It).nds")
    tailles = tailles_par_code()
    try:
        import monnames
        noms = monnames.charger(ROM_ATTENDUE, "fr")
    except Exception:
        noms = None
    table, _ = construire_bitmap(terrain, tailles, hors=hors, noms=noms)
    return [i for i in range(BORNE) if table[i >> 3] & (1 << (i & 7))]


def construire_bitmap(terrain, tailles, hors=(), noms=None, plafond=PLAFOND_MODELE):
    """Rend les 48 octets du bitmap, un bit par espece, identifiants 0 a 383.

    Une espece est autorisee si elle a un nom, un modele de terrain qui tient
    dans `plafond`, et si elle n'est pas dans la liste des boss.

    DEUX CHANGEMENTS PAR RAPPORT AU PREMIER CRITERE, tous deux demandes par la
    mesure et non par gout :

    **On part des monstres, pas des boss.** Le bestiaire numerote ses monstres
    de 1 a 256 et met les boss au-dela : c'est un critere du jeu, pas un
    jugement. Voir `scripts/monstres_nommes.py`.

    **Le hors-terrain entre aussi.** Une espece qui ne rode pas en vanilla mais
    qui possede un modele de terrain peut parfaitement roder : c'est tout
    l'objet du randomizer. La liste blanche suffit a ecarter les variantes
    internes, qui n'y figurent pas.

    Le plafond de taille, lui, n'a plus la meme raison d'etre : il datait du
    temps ou le prechargeur devait tenir cinq a onze modeles a la fois. Avec
    l'eviction on n'en garde plus que quelques-uns, et le plus gros modele du
    jeu (42 408 octets) passe sans peine.
    """
    t = bytearray(BORNE // 8)
    compte = [0, 0]
    # ON PART DU BESTIAIRE, PAS DE CE QUI RODE EN VANILLA. Balayer
    # `terrain | hors` laissait dehors les especes qui n'apparaissent ni comme
    # symbole ni dans un combat scripte -- `luna-tique` par exemple, qui a
    # pourtant un modele de 17 596 octets. La liste blanche des 256 est la seule
    # source qui vaille : tout ce qui y figure doit pouvoir sortir.
    for i in sorted(MONSTRES):
        if i >= BORNE:
            continue
        if noms is not None:
            # `monnames.charger` rend une LISTE indexee par identifiant, pas un
            # dictionnaire : `.get` n'existe pas et le test tombait toujours a
            # faux, ce qui vidait le bitmap de ses 253 especes.
            try:
                f = noms[i]
            except (KeyError, IndexError):
                f = None
            if not (isinstance(f, dict) and f.get("nom")):
                continue                # sans nom : une variante interne
        n = tailles.get(i, 0)
        if n and n <= plafond:
            t[i >> 3] |= 1 << (i & 7)
            compte[1] += 1
        else:
            compte[0] += 1
    return t, compte


def greffe_b(adr):
    """Le tireur de terrain : d'abord les modeles CHARGES, sinon la liste.

    Entree  r0 = groupe (ignore). Sortie  r0 = identifiant, ou -1.

    PREMIER CHOIX : LES MODELES CHARGES, ce qui supprime les monstres invisibles.
    L'ancienne version tirait dans la liste de prechargement -- une liste
    d'INTENTIONS. Quand le budget du tas ou le portier du conteneur ecartait une
    espece, elle y restait, le tireur la rendait quand meme, et l'apparition
    creait un acteur sans modele : le monstre invisible que le joueur trouvait
    « par chance en marchant dessus » (docs/FORMAT.md 36).

    On lit donc les emplacements 7 a 18 de la table des modeles, ceux que
    `FindLoadedModel` (0x021A2738) parcourt lui-meme, avec l'espece en
    `fiche+0x02`. Une espece qui en sort a forcement son modele en memoire.

    ET UN REPLI, SANS QUOI LE JEU DEVIENT MUET. Rendre -1 quand aucun modele
    n'est charge ferme une boucle : le jeu ne demande plus de monstre, donc rien
    ne declenche de rechargement, donc aucun modele ne revient. Mesure sur la
    sauvegarde du joueur -- dix modeles apres un chargement de zone, puis zero
    apres une minute de marche, et plus rien ensuite. Symptome rapporte : « plus
    aucun monstre ». Dans ce cas on retombe donc sur la liste, au prix d'un
    monstre parfois invisible -- ce que le joueur avait juge acceptable sur v29.

    On s'arrete au premier emplacement vide : le prechargeur les remplit dans
    l'ordre. Un trou eventuel ne fait que reduire le choix, jamais planter.
    """
    return assembler([
        "push {r4, r5, lr}",
        "ldr r4, [pc, #{L0}]",              # table + 8 + 7*4
        "mov r5, #0",
        # compter les emplacements pleins, au plus douze
        "boucle:",
        "ldr r0, [r4, r5, lsl #2]",
        "cmp r0, #0",
        "addne r5, r5, #1",
        "cmpne r5, #%d" % EMPLACEMENTS,
        "bne #{@boucle}",
        "cmp r5, #0",
        "beq #{@repli}",                    # aucun modele : la liste
        "mov r0, r5",
        "bl #%d" % RAND,                    # r0 dans [0, nombre[
        "ldr r0, [r4, r0, lsl #2]",
        "ldrsh r0, [r0, #2]",               # l'espece de la fiche
        "pop {r4, r5, pc}",
        "repli:",
        "bl #%d" % CARTE,
        "cmp r0, #0",
        "beq #{@vide}",
        "add r4, r0, #0x44",                # la liste de prechargement
        "ldrh r0, [r4, #0x18]",
        "cmp r0, #0",
        "beq #{@vide}",
        "bl #%d" % RAND,
        "mov r0, r0, lsl #1",
        "ldrh r0, [r4, r0]",
        "pop {r4, r5, pc}",
        "vide:",
        "mvn r0, #0",
        "pop {r4, r5, pc}",
    ], adr, litteraux=(TABLE_EMPL + 4 * EMPL_MODELES,))


def bl(depuis, vers):
    d = (vers - (depuis + 8)) >> 2
    return struct.pack("<I", 0xEB000000 | (d & 0xFFFFFF))


def charger_tailles():
    """Rend {identifiant: taille du .cchr decompresse}, mesuree sur l'archive.

    Voir `scripts/tailles_modeles.py`. Le tas des modeles d'une carte ne tient
    qu'un budget limite, et les modeles vont de 5,5 a 61 Kio : ecarter les plus
    gros permet de tenir plus d'especes par zone pour le meme budget.
    """
    t = {}
    try:
        for ligne in open("work/tailles_modeles.txt", encoding="utf-8"):
            if ligne.startswith("#"):
                continue
            champs = ligne.split("	")
            t[int(champs[0])] = int(champs[2])
    except OSError:
        pass
    return t


def patcher(rom, bavard=True, taille_max=0):
    arm9 = bytearray(cc.decompress(bytes(rom.arm9)))
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)

    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_ARM)
    for adr, attendu in ATTENDU.items():
        o = adr - BASE_ARM9
        ins = next(md.disasm(bytes(arm9[o:o + 4]), adr), None)
        lu = f"{ins.mnemonic} {ins.op_str}" if ins else "?"
        if lu != attendu:
            raise SystemExit(f"a {adr:#010x} : attendu {attendu!r}, lu {lu!r}")

    # la zone d'accueil doit etre vierge, sinon on ecrase quelque chose
    o = ZONE_LIBRE - BASE_ARM9
    if any(arm9[o:o + TAILLE_LIBRE]):
        raise SystemExit(f"la zone {ZONE_LIBRE:#010x} n'est pas vide")

    # --- la table des classes de taille, et la greffe A2 ---
    terrain, boss = construire_pool(
        "Dragon Quest IX - Sentinels of the Starry Skies "
        "(Europe) (En,Fr,De,Es,It).nds")
    tailles = tailles_par_code()
    if not tailles:
        raise SystemExit("aucun modele mesure : `enemy.gp2` est-il extrait "
                         "dans work/extracted ?")
    try:
        import monnames
        noms = monnames.charger(
            "Dragon Quest IX - Sentinels of the Starry Skies "
            "(Europe) (En,Fr,De,Es,It).nds", "fr")
    except Exception:
        noms = None
    table, compte = construire_bitmap(terrain, tailles, hors=boss, noms=noms,
                                      plafond=taille_max or PLAFOND_MODELE)
    arm9[o:o + BORNE // 8] = table

    a2 = greffe_a2(GREFFE_A2)
    if len(a2) > TAILLE_A2:
        raise SystemExit(f"greffe A2 trop grosse : {len(a2)} o pour {TAILLE_A2}")
    arm9[GREFFE_A2 - BASE_ARM9:GREFFE_A2 - BASE_ARM9 + len(a2)] = a2
    for adr in APPELS_ADD:
        arm9[adr - BASE_ARM9:adr - BASE_ARM9 + 4] = bl(adr, GREFFE_A2)

    b = greffe_b(GREFFE_B)
    if len(b) > TAILLE_TIREUR:
        raise SystemExit(f"greffe B : {len(b)} o pour {TAILLE_TIREUR}")
    o = GREFFE_B - BASE_ARM9
    # ON EFFACE TOUTE LA FONCTION D'ORIGINE, pas seulement ce qu'on ecrase.
    # `ChooseFieldMonsterId` fait 132 octets (base de symboles communautaire) et
    # la greffe n'en occupe que 68 : le reste est du code mort qu'un `bl` externe
    # ne peut pas atteindre -- rien ne branche au milieu d'une fonction -- et que
    # la rotation vient occuper. Mais elle refuse une region non vierge, a juste
    # titre : on la met donc a zero ici.
    arm9[o:o + TAILLE_TIREUR] = bytes(TAILLE_TIREUR)
    arm9[o:o + len(b)] = b

    struct.pack_into("<I", arm9, COMPRESSED_END, 0)
    rom.arm9 = bytes(arm9)

    if bavard:
        print(f"  arm9     : stocke en clair, {len(arm9):,} o")
        print(f"  bitmap   : {compte[1]} especes autorisees, {compte[0]} "
              f"ecartees (sans modele ou > {(taille_max or PLAFOND_MODELE)//1024} Kio) ; "
              f"{len(MONSTRES)} identifiants de monstres au bestiaire")
        print(f"  greffe A2: {len(a2)} o a {GREFFE_A2:#010x}, {ESSAIS} essais, "
              f"appartenance au conteneur verifiee")
        print(f"  greffe B : {len(b)} o a {GREFFE_B:#010x}, tire dans les modeles charges")
    return compte[1]
