#!/usr/bin/env python3
"""Le chargeur, en code relogeable, dans un bloc que l'allocateur garantit libre.

POURQUOI CETTE FORME. Trois emplacements ont ete essayes et ont echoue, chacun
parce qu'il SUPPOSAIT une region libre au lieu de le faire garantir :

  - les bourrages a zero de l'ARM9 : une greffe posee a 0x020E7100, en simple
    passe-plat, casse les textures de toutes les cartes sans monstres ;
  - la queue de l'ITCM : l'espace existe, mais crt0 refuse la restructuration du
    bloc d'autoload qui y donne acces ;
  - le code mort : 0x02002CB8, muet sur deux sessions de surveillance avec temoin
    positif valide, bloque pourtant le demarrage quand on l'ecrase.

Ici `SafeAllocator::Allocate` rend le bloc : le jeu garantit qu'il est libre. Le
prix a payer est que l'adresse change a chaque montage, donc le code doit etre
RELOGEABLE et les sites d'appel reecrits a l'execution. Voir
`scripts/patch_amorce.py` pour l'amorce qui alloue, lit et passe la main.

CE QUE « RELOGEABLE » IMPOSE

Les branchements internes sont relatifs, donc justes quelle que soit l'adresse
reelle. Mais tout appel vers le JEU doit passer par un litteral :

    appel :         ldr ip, [pc, #{Lx}] ; mov lr, pc ; bx ip
    branchement :   ldr pc, [pc, #{Lx}]

`mov lr, pc` place l'adresse de l'instruction qui suit `bx ip`, `pc` valant
« ici + 8 ». Ce surcout de deux instructions par appel etait impensable a
vingt-quatre octets pres ; il est indolore dans un bloc de 1 024.

Et l'acces a nos propres donnees se fait par `sub rX, pc, #{@@etiquette}` --
procede que la greffe A2 utilise deja pour son bitmap. LE DEPLACEMENT EST
CALCULE PAR L'ASSEMBLEUR, jamais a la main : un litteral lu quatre octets trop
loin (58) et une sortie commune decalee d'une instruction (61) sont les deux
pannes les plus couteuses du projet.

DISPOSITION : LES DONNEES D'ABORD

    +0x00   en-tete : le deplacement de l'installateur
    +0x04   mots     DEMANDE / DEPART / BORNE
    +0x10   table    sept paires {site, deplacement de la cible}, puis un zero
    ...     installateur, les six greffes, le declencheur
    fin     le pool de litteraux

Les donnees precedent le code pour que tous les acces soient des deplacements
ARRIERE, seul sens que `sub rX, pc, #n` sait exprimer.

LES TROIS MOTS VIVENT DANS LE BLOB. Plus rien hors du blob ne les lit -- le
declencheur y est aussi, et le portier n'a plus de garde depuis que le
declencheur a quitte le portier (71). Les douze octets qu'ils occupaient dans
`GREFFE_C` sont donc rendus.

SEPT SITES, PAS SIX. Les six du prechargeur, plus l'appel au declencheur dans
`emprunt`. Ce septieme est un `mov r0, r0` dans la ROM : tant que l'installation
n'a pas eu lieu -- allocation refusee, fichier absent -- aucun chargement n'est
demande et le jeu se comporte comme sans chargeur. Degradation propre et
gratuite.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patch_hasard import assembler, GREFFE_C

# --- les fonctions du jeu que le blob rappelle, toutes par litteral ---
VIDE_EMPLACEMENTS = 0x021A27E8    # ClearAllMonsterModelSlots
ROLLBACK_VRAM = 0x0207DFA0        # SetFrmTexVramState : jette les textures
COMPTE_LISTE = 0x0209C0FC         # `ldrh r0, [r0, #0x18] ; bx lr`
GET_ESPECE = 0x0209C0B8           # GetSpecies(liste, i)
PRECHARGEUR = 0x021A28A8
GET_CTX_TERRAIN = 0x021D82E4      # [ce mot] = le contexte de terrain
DC_FLUSH = 0x020C8300
IC_INVALIDE = 0x020C833C

# --- les sites a reecrire a l'execution (overlay 17, sauf le dernier) ---
SITE_VIDE = 0x021A28CC
SITE_TABLEAU = 0x021A28E0         # dimensionnement du tableau de fiches
SITE_VRAM = 0x021A2900
SITE_DEPART = 0x021A295C          # `mov sb, #0`
SITE_ESPECE = 0x021A2974
SITE_BOUCLE = 0x021A2ACC          # borne de boucle
SITE_MODELE = 0x021A21F8          # bl FindLoadedModel, dans l'apparition
SITE_MONTAGE = 0x021A30FC         # bl PRECHARGEUR, dans le montage
TROUVE_MODELE = 0x021A2738        # FindLoadedModel(?, espece) -> fiche ou 0
CHARGE_SOURCE = 0x0206EFE8        # (contexte, tas) -> batit la table des 438
RAND = 0x02032380                 # rand_below(max)
TABLE_BASE = 0x020F33D8 + 8       # la table du gestionnaire, entree 0
TABLE_EMPL = TABLE_BASE + 4 * 7   # les emplacements de modele, entree 7
# LES ACTEURS VIVANTS, dans la meme table. Predicat mesure (50, revalide sur la
# savegarde du joueur) : `variante = [0x020FDD46] & 3`, puis douze entrees a
# partir de `0x70 + 12 * variante`. Une entree non nulle dont le short a `+2` est
# positif porte un monstre present sur la carte, et ce short est son espece.
#
#   acteurs 112:139 113:223 114:78 (puis -1)   modeles : 197,139,223,78
#
# Trois monstres vivants, quatre modeles charges : seul le 197 est liberable.
CARTE_VARIANTE = 0x020FDD46
ACTEURS_BASE = 0x70               # index de la premiere entree d'acteur
ACTEURS_N = 12
SEUIL_TERRAIN = 0x2C000           # au-dela, la carte porte des monstres
SITE_PORTIER1_SPAWN = 0x021A2164
SITE_PORTIER1_PRECH = 0x021A2988
SITE_PORTIER2_SPAWN = 0x021A2178
SITE_PORTIER2_RELU = 0x021A22F0
SITE_PORTIER2_PRECH = 0x021A299C
RECH_GENERIQUE = 0x0206F480       # BinarySearch(conteneur, cle, extracteur)
ALLOUE = 0x02032554               # SafeAllocator::Allocate(tas, taille)
LIBERE = 0x02032628               # SafeAllocator::Free(tas, pointeur)
#   Sur `EXPH` elle appelle `0x020AF788(tas, pointeur)` -- une liberation par
#   bloc. Sur `FRMH` elle passe la constante 3 a `0x020AF9FC` : une liberation
#   globale, qui rembobine tout. D'ou l'ExpHeap sur les seules cartes a monstres.
GESTIONNAIRE = 0x0200F398         # () -> le gestionnaire d'emplacements
VIDE_EMPLACEMENT = 0x0200FD58     # (gestionnaire, index) : met le pointeur a 0
SITE_MODELE_ALLOC = 0x02075678    # `bl Allocate` du lecteur de fichier
BATIR_NOEUDS = 0x0206EE90         # (conteneur, tas, donnees, taille, especes, n)
#   Analyse `data/prm/fld_mondata.bin` -- 441 enregistrements, un par espece --
#   et pousse dans le conteneur 2 un noeud de 0x14 octets pour CHAQUE espece du
#   tableau passe. C'est la fonction que le montage appelle avec la liste de
#   prechargement de la carte ; rien n'empeche de l'appeler avec une espece.
SITE_BATIR = 0x021B5400           # son appel, dans le montage de la carte
#   On s'y greffe pour capturer les donnees et leur taille : le fichier est deja
#   charge en memoire par le jeu, inutile de le relire.
CARTE_DEPUIS_C2 = 0x304           # le conteneur 2 est a carte+0x304
CARTE_TAS = 0x10                  # le tas ou le jeu alloue les noeuds
#   C'est par la que passe le bloc du modele -- 16 a 20 Ko -- et c'est le seul
#   endroit ou son adresse existe. La fiche n'en porte que la FIN (cf. 76.3).
DEBUT_SITES2 = 0x02075600         # le treizieme site vit dans l'ARM9, loin
PLAGE_SITES2 = 0x100              # des douze autres : deuxieme plage de cache
EXTRACTEUR = 0x0206EF50           # `ldrsh r0, [r0, #8]` : la cle d'un enreg.
SUIVANT = 0x10                    # champ suivant d'un noeud du conteneur 2
DEBUT_SITES = 0x021A2164          # la plus basse adresse patchee
PLAGE_SITES = 0x1000              # jusqu'a 0x021A2ACC, avec de la marge

# LES DOUZE SITES, dans l'ordre ou la table les portera. Liste nommee pour que
# l'appelant puisse en lire les mots d'origine dans l'overlay sans les redecrire.
SITES_PATCHES = (SITE_VIDE, SITE_TABLEAU, SITE_VRAM, SITE_DEPART, SITE_ESPECE,
                 SITE_BOUCLE, SITE_MODELE, SITE_PORTIER1_SPAWN,
                 SITE_PORTIER1_PRECH, SITE_PORTIER2_SPAWN, SITE_PORTIER2_RELU,
                 SITE_PORTIER2_PRECH, SITE_MODELE_ALLOC, SITE_BATIR)

EMPLACEMENTS = 12
PLAFOND = 5
BASE = 8                          # l'en-tete : installateur, puis desinstalleur

# LE MOT FIXE QUI PORTE LA BASE DU BLOB. Il vit dans l'ARM9, a une adresse qui ne
# bouge pas, parce que le talon de demontage doit pouvoir trouver le blob sans
# rien connaitre de l'allocation. L'installateur l'ecrit, le desinstalleur le
# remet a zero.
BLOB_BASE = GREFFE_C + 0x20
MOTS_N = 6                        # DEMANDE, DEPART, BORNE, DONNEES, TAILLE, ESPECE
OFF_DONNEES = 12                  # l'adresse de fld_mondata.bin, capturee
OFF_TAILLE = 16                   # sa taille
OFF_ESPECE = 20                   # le tableau d'une seule entree qu'on lui passe
MODELES_N = 8                     # un mot par emplacement de la rotation
DECALAGE_MODELES = 4 * MOTS_N     # `modeles` suit `mots` immediatement
# ON N'ADRESSE PAS `modeles` PAR `sub rX, pc, #{@@modeles}`. Le deplacement doit
# etre un immediat ARM encodable -- 8 bits tournes d'un rang pair -- et il ne
# l'est plus des que le blob grandit : 1048 octets a fait echouer l'assemblage.
# On part donc de la base de `mots`, que le code a deja en main, et on ajoute
# douze : une constante, jamais un deplacement.
TABLE_ENTREES = 18                # quatorze sites, le zero terminal, et de la marge
MOTS_PAR_ENTREE = 3               # {site, deplacement de la cible, mot d'origine}
SRC_N = 4                         # {compte, bloc, chaines, reserve} : 16 octets

# LE MIROIR DU COMPTE, A UNE ADRESSE FIXE. `talon_borne` (patch_place) vit dans
# l'ARM9 et doit savoir si la carte porte des monstres ; son critere est
# « la table source a-t-elle ete batie ». Mais la table vit desormais dans le
# blob, dont l'adresse change a chaque montage : le talon ne peut pas la lire.
# Le talon de source recopie donc son compte dans le premier mot de `GREFFE_C`,
# l'ancien emplacement de SRC, qui reste libre et fixe.
SRC_MIROIR = GREFFE_C
NOEUDS = 8                        # un noeud par monstre synthetique simultane
NOEUD_MOTS = 8                    # un noeud de conteneur 2 : 0x20 octets
NOEUD_N = NOEUDS * NOEUD_MOTS + 1 # les huit noeuds, puis le tour de rotation
# UN SEUL NOEUD NE SUFFISAIT PAS, et le relevé le montre sans appel : deux
# acteurs vivants pointaient sur la meme adresse, et le champ espece basculait
# de l'un a l'autre au gre des recherches. Il en faut un par monstre.
#
# ET IL DOIT ETRE COPIE D'UN VRAI. Un noeud natif porte huit mots de parametres
# de comportement -- `050B0093 003C0309 00371333 00000037 <suivant> 632600AA
# 003C1211 00C61CCC` -- que le jeu remplit par un chargement ASYNCHRONE, une
# requete par espece, au montage de la carte (`0x0206EE90`). On ne peut pas la
# declencher a l'apparition : elle n'aurait pas abouti. Un noeud a zero, lui,
# laisse le monstre immobile et sans reaction, puis fait tomber la machine a
# scripts sur un pointeur nul (`ldrh lr, [r2]` a `0x020B4B00`).
#
# On recopie donc les parametres d'une espece de la carte et on n'y change que
# l'espece elle-meme : le comportement est emprunte, mais il est VALIDE.

# L'EMPRUNT ET LE TALON DE SOURCE DEMENAGENT DANS LE BLOB, et c'est ce qui rend
# le cablage possible. Ils occupaient 156 des 116 octets d'espace possede encore
# disponibles, dispersés en trois et un morceaux ; l'amorce en demande 100 d'un
# tenant. En les mettant ici, la region du tireur (132 octets, dont 8 pour le
# tireur lui-meme) se libere et accueille l'amorce sans decoupage.
#
# Leurs sites sont donc reecrits a l'execution comme les autres. Et l'ordre est
# preserve : l'installateur, apres avoir patche les sites, ENCHAINE sur le talon
# de source, qui batit la table puis appelle le prechargeur -- exactement ce que
# faisait le talon quand il vivait dans l'ARM9.


def construire(plafond=PLAFOND, site_declencheur=0, originaux=None,
               especes=()):
    """Rend (octets du blob, deplacement de l'installateur).

    `site_declencheur` est l'adresse du `mov r0, r0` d'`emprunt` a transformer en
    `bl` vers le declencheur. Zero pour n'en pas poser.

    `originaux` donne, pour chaque site, le mot qu'il porte dans la ROM : c'est
    ce que le desinstalleur y remet quand la carte se demonte. Sans lui la table
    ne peut pas etre remplie, donc il est obligatoire.
    """
    if originaux is None:
        raise SystemExit("construire() exige les mots d'origine des douze sites")
    if not especes:
        raise SystemExit("construire() exige la liste des especes tirables")
    if len(especes) > 255:
        raise SystemExit(f"{len(especes)} especes : le compte doit tenir dans "
                         f"un immediat de huit bits")
    pool, index = [], {}

    def lit(v):
        if v not in index:
            index[v] = len(pool)
            pool.append(v)
        return "{L%d}" % index[v]

    def appel(cible):
        return ["ldr ip, [pc, #%s]" % lit(cible), "mov lr, pc", "bx ip"]

    def saut(cible):
        return ["ldr pc, [pc, #%s]" % lit(cible)]

    # --- les donnees, reservees par des instructions inoffensives jamais
    # --- executees, et reecrites apres l'assemblage
    lignes = ["mots:"] + ["mov r0, r0"] * MOTS_N
    lignes += ["modeles:"] + ["mov r0, r0"] * MODELES_N
    # La liste des especes tirables, en demi-mots : c'est le tableau que
    # `BATIR_NOEUDS` parcourt pour decider quels enregistrements de
    # `fld_mondata.bin` deviennent des noeuds.
    lignes += ["especes:"] + ["mov r0, r0"] * ((len(especes) + 1) // 2)
    lignes += ["talon_off:", "mov r0, r0"]      # le deplacement du talon de source
    lignes += ["src:"] + ["mov r0, r0"] * SRC_N
    lignes += ["noeud:"] + ["mov r0, r0"] * NOEUD_N
    lignes += ["table:"] + ["mov r0, r0"] * (MOTS_PAR_ENTREE * TABLE_ENTREES)

    # --- l'installateur : reecrit les sites, synchronise, rend le talon ---
    lignes += [
        "installateur:",
        "push {r4, r5, lr}",
        "mov r4, r0",                       # la base du blob
        "sub r5, pc, #{@@H:table}",
        "sub r5, r5, #{@@L:table}",
        "boucle:",
        "ldr r0, [r5], #4",                 # le site
        "cmp r0, #0",
        "beq #{@caches}",
        "ldr r1, [r5], #4",                 # le deplacement de la cible
        "add r5, r5, #4",                   # sauter le mot d'origine
        "add r1, r1, r4",                   # son adresse
        "sub r1, r1, r0",
        "sub r1, r1, #8",                   # deplacement relatif du bl
        "mov r1, r1, asr #2",
        "bic r1, r1, #0xff000000",          # garder les 24 bits utiles
        "orr r1, r1, #0xeb000000",          # encodage de BL
        "str r1, [r0]",
        "b #{@boucle}",
        "caches:",
        # On vient d'ecrire du CODE par le cache de donnees : le vider, puis
        # invalider le cache d'instructions, sinon le prefetch continue de servir
        # les anciens appels.
        "ldr r0, [pc, #%s]" % lit(DEBUT_SITES),
        "mov r1, #%d" % PLAGE_SITES,
    ] + appel(DC_FLUSH) + [
        "ldr r0, [pc, #%s]" % lit(DEBUT_SITES),
        "mov r1, #%d" % PLAGE_SITES,
    ] + appel(IC_INVALIDE) + [
        "ldr r0, [pc, #%s]" % lit(DEBUT_SITES2),
        "mov r1, #%d" % PLAGE_SITES2,
    ] + appel(DC_FLUSH) + [
        "ldr r0, [pc, #%s]" % lit(DEBUT_SITES2),
        "mov r1, #%d" % PLAGE_SITES2,
    ] + appel(IC_INVALIDE) + [
        # Rendre l'adresse du talon de source DANS r1, et non dans r0 : l'amorce
        # restitue son contexte par un `pop {r0, ...}` et saute par `bx r1`, ce
        # qui lui epargne le `mov r1, r0` -- quatre octets qu'elle n'a pas.
        # Le talon est APRES nous, donc son deplacement ne s'exprime pas par un
        # `sub pc` : on le lit dans un mot de donnees, ecrit apres l'assemblage.
        # NOTER LA BASE, a l'adresse fixe que le talon de demontage interroge.
        "ldr r0, [pc, #%s]" % lit(BLOB_BASE),
        "str r4, [r0]",
        "sub r1, pc, #{@@H:talon_off}",
        "sub r1, r1, #{@@L:talon_off}",
        "ldr r1, [r1]",
        "add r1, r1, r4",
        "pop {r4, r5, pc}",
    ]

    # --- le desinstalleur : rendre aux douze sites leur instruction d'origine ---
    #
    # POURQUOI IL EXISTE. Le blob vit dans le tas des modeles, cree et detruit
    # avec la carte. A l'entree en combat le contexte de terrain est demonte --
    # mesure sur la savestate du joueur : `ctx+0x113C` et `ctx+0x1244` valent
    # tous deux zero -- et la memoire du blob est reprise par d'autres donnees.
    # Les douze sites, eux, gardent leur `bl` : le suivant appele saute dans des
    # donnees. C'est l'abort a `0xFFFF0108` avec `lr = 0235ACDC`, et le mot qui
    # precede cette adresse n'etait plus une instruction.
    #
    # On rend donc les sites a leur etat d'origine AVANT que le tas meure, depuis
    # un talon accroche au demontage lui-meme. Le blob est encore vivant a cet
    # instant : c'est le dernier moment ou il peut se retirer proprement.
    lignes += [
        "desinstalleur:",
        "push {r4, r5, lr}",
        "sub r5, pc, #{@@H:table}",
        "sub r5, r5, #{@@L:table}",
        "boucle3:",
        "ldr r0, [r5], #4",                 # le site
        "cmp r0, #0",
        "beq #{@caches3}",
        "add r5, r5, #4",                   # sauter le deplacement de la cible
        "ldr r1, [r5], #4",                 # le mot d'origine
        "str r1, [r0]",
        "b #{@boucle3}",
        "caches3:",
        "ldr r0, [pc, #%s]" % lit(BLOB_BASE),
        "mov r1, #0",
        "str r1, [r0]",                     # plus de blob : le talon s'abstiendra
        "ldr r0, [pc, #%s]" % lit(DEBUT_SITES),
        "mov r1, #%d" % PLAGE_SITES,
    ] + appel(DC_FLUSH) + [
        "ldr r0, [pc, #%s]" % lit(DEBUT_SITES),
        "mov r1, #%d" % PLAGE_SITES,
    ] + appel(IC_INVALIDE) + [
        "ldr r0, [pc, #%s]" % lit(DEBUT_SITES2),
        "mov r1, #%d" % PLAGE_SITES2,
    ] + appel(DC_FLUSH) + [
        "ldr r0, [pc, #%s]" % lit(DEBUT_SITES2),
        "mov r1, #%d" % PLAGE_SITES2,
    ] + appel(IC_INVALIDE) + [
        "pop {r4, r5, pc}",
    ]

    # --- le talon de source : batit la table des 438, puis precharge ---
    lignes += [
        "talon_source:",
        "push {r0, lr}",                    # le contexte, a l'abri
        "sub r0, pc, #{@@H:src}",
        "sub r0, r0, #{@@L:src}",
        "mov r2, #0",
        "str r2, [r0]",                     # invalider TOUJOURS : le tas est neuf
        "ldr r0, [pc, #%s]" % lit(SRC_MIROIR),
        "str r2, [r0]",                     # et le miroir avec lui
        # DEUX TEMOINS, parce qu'un miroir a zero est ambigu : c'est aussi la
        # valeur d'origine de la ROM. Ils distinguent « jamais execute » de
        # « execute, table non batie » et donnent le chiffre qui a decide.
        "mov r1, #0xA5000000",
        "str r1, [r0, #4]",                 # temoin de passage
        "str r5, [r0, #8]",                 # la taille du tas, comparee au seuil
        # ON NE BATIT PAS LA TABLE SUR UNE CARTE SANS MONSTRES. Elle coute ~21 Ko
        # et le tas d'une ville n'en fait que 62 : les prendre affamait le tas des
        # requetes asynchrones, par lequel une ville charge PNJ, boutiques et
        # decors -- textures etirees, symptome rapporte quatre versions de suite.
        # `r5` porte la taille du tas : 62 280 en ville, 171 424 a l'eglise,
        # 188 384 sur le terrain. Le seuil est place entre les deux dernieres.
        "ldr r2, [pc, #%s]" % lit(SEUIL_TERRAIN),
        "cmp r5, r2",
        "blt #{@saute}",
        "ldr r1, [sp]",                     # le contexte
        "add r1, r1, #0x1100",
        "add r1, r1, #0x3c",                # r1 = ctx + 0x113C, le tas
        # R0 EST RECHARGE ICI, ET C'EST INDISPENSABLE. `CHARGE_SOURCE(contexte,
        # tas)` ecrit {compte, bloc, chaines} A L'ADRESSE QUE r0 DESIGNE. Le
        # `sub r0, pc, #{@@src}` du haut le portait bien, mais les ecritures du
        # miroir l'ont ecrase entre-temps : la table se batissait alors DANS le
        # miroir, dans l'ARM9, tandis que le `src` du blob restait vide -- donc
        # le portier ne connaissait aucune espece, rejetait chaque tirage, et le
        # tic reessayait sans fin (ecran noir a l'entree en combat, une fois sur
        # deux ou trois ; et les rares especes acceptees etant celles de la
        # carte, le premier monstre semblait correct quatre fois sur cinq).
        "sub r0, pc, #{@@H:src}",
        "sub r0, r0, #{@@L:src}",
    ] + appel(CHARGE_SOURCE) + [
        # le compte, recopie a l'adresse fixe que `talon_borne` sait lire
        "sub r0, pc, #{@@H:src}",
        "sub r0, r0, #{@@L:src}",
        "ldr r1, [r0]",
        "ldr r0, [pc, #%s]" % lit(SRC_MIROIR),
        "str r1, [r0]",
        "saute:",
        "pop {r0, lr}",
    ] + saut(PRECHARGEUR)

    # --- greffe A : init des mots de boucle, et saut du vidage ---
    lignes += [
        "greffe_a:",
        "sub r1, pc, #{@@H:mots}",
        "sub r1, r1, #{@@L:mots}",
        "ldr r2, [r1]",                     # DEMANDE
        "cmp r2, #0",
        "bxne lr",                          # mode demande : ne rien toucher
        "mov r2, #0",
        "str r2, [r1, #4]",                 # DEPART = 0
        "mov r2, #%d" % plafond,
        "str r2, [r1, #8]",                 # BORNE = plafond
    ] + saut(VIDE_EMPLACEMENTS)

    # --- greffe borne : min(compte reel, BORNE), pour les DEUX sites ---
    # Le prechargeur lit le compte a deux endroits : pour dimensionner son tableau
    # de fiches et pour borner sa boucle. Les faire diverger ecrit des fiches hors
    # du tableau -- 880 octets debordes en ville, 1 232 en mode demande. Une seule
    # fonction pour les deux, donc l'ecart ne peut plus exister.
    lignes += [
        "greffe_borne:",
        "sub r1, pc, #{@@H:mots}",
        "sub r1, r1, #{@@L:mots}",
        "ldr r1, [r1, #8]",                 # BORNE
        "ldrh r0, [r0, #0x18]",             # le compte reel de la liste
        "cmp r0, r1",
        "movgt r0, r1",
        "bx lr",
    ]

    # --- greffe C : saut du rollback du watermark VRAM en mode demande ---
    lignes += [
        "greffe_c:",
        "sub r1, pc, #{@@H:mots}",
        "sub r1, r1, #{@@L:mots}",
        "ldr r1, [r1]",
        "cmp r1, #0",
        "bxne lr",
    ] + saut(ROLLBACK_VRAM)

    # --- greffe D : l'index de depart de la boucle ---
    lignes += [
        "greffe_d:",
        "sub sb, pc, #{@@H:mots}",
        "sub sb, sb, #{@@L:mots}",
        "ldr sb, [sb, #4]",                 # DEPART
        "bx lr",
    ]

    # --- greffe E : rendre l'espece demandee ---
    lignes += [
        "greffe_e:",
        "sub r2, pc, #{@@H:mots}",
        "sub r2, r2, #{@@L:mots}",
        "ldr r2, [r2]",                     # DEMANDE
        "cmp r2, #0",
        "subne r0, r2, #1",
        "bxne lr",
    ] + saut(GET_ESPECE)

    # --- greffe donnees : capturer fld_mondata.bin au montage ---
    #
    # Le jeu le charge deja pour batir le conteneur 2 de la carte. On note son
    # adresse et sa taille au passage, puis on enchaine sur la fonction
    # d'origine par un branchement RELATIF : `lr` n'est pas touche, donc elle
    # rend directement a l'appelant et le montage ne voit rien.
    lignes += [
        "greffe_donnees:",
        # LE BON MOMENT, ET IL N'Y EN A QU'UN. Le montage vient de VIDER le
        # conteneur 2 (`0x0206EE70`) et s'apprete a le remplir avec les especes
        # de la carte. On s'intercale entre les deux : nos noeuds sont batis
        # avant les siens, donc ils survivent au vidage, et l'appel d'origine
        # ajoute les siens par-dessus.
        #
        # `r0` a `r3` portent deja tout ce qu'il faut -- conteneur, tas, donnees,
        # taille -- et les deux arguments de pile de l'appelant restent intacts
        # sous `sp`. On empile huit mots, ce qui garde la pile alignee sur huit
        # octets, on fait notre appel, on restitue, et on enchaine par un
        # branchement RELATIF : l'appelant ne voit rien passer.
        "push {r0, r1, r2, r3, r4, r5, r6, lr}",
        "sub r6, pc, #{@@H:mots}",
        "sub r6, r6, #{@@L:mots}",
        "str r2, [r6, #%d]" % OFF_DONNEES,
        "str r3, [r6, #%d]" % OFF_TAILLE,
        # RIEN SUR UNE CARTE SANS MONSTRES. Le miroir du compte est deja pose --
        # `talon_source` tourne au montage, bien avant ce site -- et il vaut zero
        # en ville : les noeuds y prendraient cinq kilo-octets pour personne.
        "ldr r4, [pc, #%s]" % lit(SRC_MIROIR),
        "ldr r4, [r4]",
        "cmp r4, #0",
        "beq #{@sans_noeuds}",
        "sub r4, pc, #{@@H:especes}",
        "sub r4, r4, #{@@L:especes}",
        "mov r5, #%d" % len(especes),
        "push {r4, r5}",                    # sp[0] = tableau, sp[1] = compte
    ] + appel(BATIR_NOEUDS) + [
        "add sp, sp, #8",
        "sans_noeuds:",
        "pop {r0, r1, r2, r3, r4, r5, r6, lr}",
        # PAR LE POOL, PAS PAR UN BRANCHEMENT ABSOLU. Le blob est assemble pour
        # la base 8 et execute vers 0x0235xxxx : un `b #adresse` y encode un
        # deplacement calcule sur la mauvaise origine et part n'importe ou. Tout
        # saut hors du blob passe donc par `saut()`, qui lit l'adresse dans le
        # pool de litteraux.
    ] + saut(BATIR_NOEUDS)

    # --- greffe modele : noter l'adresse du bloc que le chargement alloue ---
    #
    # LA FICHE NE PORTE PAS LA BASE DU BLOC, seulement sa fin (76.3). Sur le
    # frame heap la base se deduisait -- les allocations y sont contigues -- mais
    # cette egalite disparait en ExpHeap, c'est-a-dire exactement quand on en a
    # besoin pour rendre le bloc. On la capture donc a la source.
    #
    # On ne note que les gros blocs, et seulement en mode demande : le meme
    # lecteur de fichier sert a tout le jeu, et l'autre allocation d'une
    # apparition -- la table de fiches -- passe par un site different.
    lignes += [
        "greffe_modele:",
        "push {r4, lr}",
        "mov r4, r1",                       # la taille demandee
    ] + appel(ALLOUE) + [
        "cmp r4, #0x2000",
        "popls {r4, pc}",                   # trop petit : ce n'est pas un modele
        "sub r1, pc, #{@@H:mots}",
        "sub r1, r1, #{@@L:mots}",
        "ldr r2, [r1]",                     # DEMANDE
        "cmp r2, #0",
        "popeq {r4, pc}",                   # pas nous : ne rien noter
        "ldr r2, [r1, #4]",                 # DEPART
        "add r1, r1, #%d" % DECALAGE_MODELES,
        "str r0, [r1, r2, lsl #2]",
        "pop {r4, pc}",
    ]

    # --- le portier 1 : le conteneur de la carte, sinon la table source ---
    lignes += [
        "portier1:",
        "push {r4, lr}",
        "mov r4, r1",                       # l'espece
        "ldr r2, [pc, #%s]" % lit(EXTRACTEUR),
    ] + appel(RECH_GENERIQUE) + [
        "cmp r0, #0",
        "popne {r4, pc}",                   # deja present : rien a faire
        "sub r0, pc, #{@@H:src}",
        "sub r0, r0, #{@@L:src}",
        "mov r1, r4",
        "ldr r2, [pc, #%s]" % lit(EXTRACTEUR),
    ] + appel(RECH_GENERIQUE) + [
        "pop {r4, pc}",
    ]

    # --- le portier 2 : la liste chainee, sinon un noeud synthetique ---
    lignes += [
        "portier2:",
        "push {r4, r5, r6, r7, lr}",
        "mov r4, r1",                       # l'espece cherchee
        "mov r6, r0",                       # le conteneur, garde
        "ldr r5, [r0]",                     # la tete de liste, gardee pour copier
        "mov r0, r5",
        "b #{@verif2}",
        "boucle2:",
        "ldrsh r2, [r0]",
        "cmp r2, r4",
        "popeq {r4, r5, r6, r7, pc}",
        "ldr r0, [r0, #%d]" % SUIVANT,
        "verif2:",
        "cmp r0, #0",
        "bne #{@boucle2}",
        # ABSENTE DE LA LISTE : on copie un noeud voisin. C'est un SECOURS, et
        # il ne devrait plus servir, les noeuds des especes tirables etant batis
        # au montage (voir `greffe_donnees`). Le garder coute vingt instructions
        # et evite qu'une espece oubliee fasse tomber la machine a scripts.
        #
        # LES BATIR ICI NE MARCHAIT PAS. Appeler `0x0206EE90` pendant une
        # apparition laissait `[carte+0x304]` charge d'un mot d'instruction, et
        # la boucle de relecture abortait dessus : la fonction n'est pas
        # reentrante, et le montage l'appelle deja.
        "copie_noeud:",
        # --- absente de la liste : un noeud a nous, copie d'un vrai ---
        "sub r6, pc, #{@@H:noeud}", # la base du pool
        "sub r6, r6, #{@@L:noeud}",
        "ldr r2, [r6, #%d]" % (4 * NOEUDS * NOEUD_MOTS),   # le tour
        "add r3, r2, #1",
        "and r3, r3, #%d" % (NOEUDS - 1),
        "str r3, [r6, #%d]" % (4 * NOEUDS * NOEUD_MOTS),
        "add r6, r6, r2, lsl #%d" % (NOEUD_MOTS.bit_length() + 1),
        "cmp r5, #0",
        "beq #{@noeud_pret}",               # liste vide : on garde ce qu'il y a
        "mov r2, #0",
        "copie2:",
        "ldr r3, [r5, r2]",
        "str r3, [r6, r2]",
        "add r2, r2, #4",
        "cmp r2, #%d" % (4 * NOEUD_MOTS),
        "bne #{@copie2}",
        "noeud_pret:",
        "strh r4, [r6]",                    # l'espece demandee, elle, est juste
        "mov r1, #0",
        "str r1, [r6, #%d]" % SUIVANT,      # jamais chaine dans la liste
        "mov r0, r6",
        "pop {r4, r5, r6, r7, pc}",
    ]

    # --- le declencheur, en une seule piece ---
    lignes += [
        "declencheur:",
        "push {r4, r5, r6, r7, lr}",
        "sub r4, pc, #{@@H:mots}",
        "sub r4, r4, #{@@L:mots}",
        "add r2, r0, #1",
        "str r2, [r4]",                     # DEMANDE = espece + 1
        "ldr r0, [pc, #%s]" % lit(GET_CTX_TERRAIN),
        "ldr r6, [r0]",                     # le contexte de terrain
        "ldr r5, [r4, #4]",                 # le DEPART precedent : on repart de la
        # --- L'EVICTION, ET LE CHOIX DE LA VICTIME ---
        #
        # Sans eviction le tas se remplit et le quatrieme chargement echoue --
        # 21 776 octets par modele pour 94 Ko utiles (76.1). Mais evincer au tour
        # de role fige le jeu : un acteur vivant garde un pointeur sur son
        # modele, et le rendre le laisse lire dans une memoire reprise. Mesure
        # sur la savestate du joueur : abort sur `str r6, [r0, #4]` avec r0 nul,
        # a `0x020356E8`, dans la boucle de rendu d'un acteur -- un getter du
        # modele venait de rendre zero.
        #
        # ON CHERCHE DONC UNE VICTIME, au lieu de tourner. Un emplacement est
        # liberable s'il est vide, ou si aucun des douze acteurs de la carte ne
        # porte l'espece de son modele. Si les huit sont vivants, ON NE CHARGE
        # PAS : `emprunt` rendra une apparence empruntee, ce qui est le
        # comportement de P3 -- degrade, jamais faux.
        # DEUX PASSES, ET L'ORDRE EST TOUT. La premiere ne retient qu'un
        # emplacement OCCUPE dont aucun acteur ne porte l'espece : c'est le seul
        # choix qui rende de la memoire. La seconde se rabat sur un emplacement
        # vide.
        #
        # Une passe unique prenait le premier emplacement libre, ne liberait donc
        # rien, et le chargement echouait des que le tas etait plein -- ce qui
        # arrive avec six modeles pour huit emplacements. Le joueur voyait le
        # plafond rester a quatre alors que l'eviction fonctionnait : elle
        # s'appliquait juste au mauvais emplacement.
        "mov r7, #%d" % 8,
        "suivant:",
        "add r5, r5, #1",
        "and r5, r5, #7",
        "ldr r0, [pc, #%s]" % lit(TABLE_EMPL),
        "ldr r1, [r0, r5, lsl #2]",         # la fiche de cet emplacement
        "cmp r1, #0",
        "beq #{@essai_suivant}",            # vide : pas dans cette passe
        "ldrsh r0, [r1, #2]",               # l'espece que son modele porte
        "bl #{@utilisee}",
        "cmp r0, #0",
        "beq #{@prendre}",                  # occupe et mort : la bonne victime
        "essai_suivant:",
        "subs r7, r7, #1",
        "bne #{@suivant}",
        # seconde passe : faute de victime, un emplacement vide
        "mov r7, #%d" % 8,
        "suivant2:",
        "add r5, r5, #1",
        "and r5, r5, #7",
        "ldr r0, [pc, #%s]" % lit(TABLE_EMPL),
        "ldr r1, [r0, r5, lsl #2]",
        "cmp r1, #0",
        "beq #{@prendre}",
        "subs r7, r7, #1",
        "bne #{@suivant2}",
        "b #{@abandon}",                    # les huit sont vivants et pleins
        "prendre:",
        "str r5, [r4, #4]",                 # DEPART = l'emplacement choisi
        "add r2, r5, #1",
        "str r2, [r4, #8]",                 # BORNE = DEPART + 1 : un seul tour
        # L'ORDRE COMPTE : oublier l'adresse d'abord, liberer ensuite. Si la
        # liberation echouait, mieux vaut une fuite qu'un pointeur qu'on croit
        # encore valide -- c'est exactement ce qui a produit l'ecran noir du 75.
        "add r0, r4, #%d" % DECALAGE_MODELES,
        "ldr r1, [r0, r5, lsl #2]",
        "cmp r1, #0",
        "beq #{@charge}",
        "mov r2, #0",
        "str r2, [r0, r5, lsl #2]",
        "add r0, r6, #0x1100",
        "add r0, r0, #0x3c",                # l'allocateur du tas des modeles
    ] + appel(LIBERE) + appel(GESTIONNAIRE) + [
        "add r1, r5, #7",                   # les emplacements commencent a 7
    ] + appel(VIDE_EMPLACEMENT) + [
        "charge:",
        "mov r0, r6",
    ] + appel(PRECHARGEUR) + [
        "abandon:",
        "mov r2, #0",
        "str r2, [r4]",                     # DEMANDE = 0
        "pop {r4, r5, r6, r7, pc}",

        # --- l'espece de r0 est-elle portee par un acteur vivant ? ---
        #
        # N'ecrase que r0 a r3 : le declencheur garde r4 a r7 en travers de
        # l'appel, et `lr` lui appartient deja.
        "utilisee:",
        "ldr r1, [pc, #%s]" % lit(CARTE_VARIANTE),
        "ldrh r1, [r1]",
        "and r1, r1, #3",
        "add r1, r1, r1, lsl #1",           # trois fois la variante
        "mov r1, r1, lsl #2",               # douze fois : le pas d'un jeu
        "add r1, r1, #%d" % ACTEURS_BASE,
        "ldr r2, [pc, #%s]" % lit(TABLE_BASE),
        "add r1, r2, r1, lsl #2",           # la premiere entree d'acteur
        "mov r2, #%d" % ACTEURS_N,
        "boucle_act:",
        "ldr r3, [r1], #4",
        "cmp r3, #0",
        "beq #{@acteur_suivant}",
        "ldrsh r3, [r3, #2]",               # negatif : entree morte
        "cmp r3, r0",
        "moveq r0, #1",
        "bxeq lr",
        "acteur_suivant:",
        "subs r2, r2, #1",
        "bne #{@boucle_act}",
        "mov r0, #0",
        "bx lr",
    ]

    # --- l'emprunt : le vrai modele, sinon le chargement, sinon un emprunt ---
    lignes += [
        "emprunt:",
        "push {r4, r5, lr}",
        "mov r5, r1",                       # l'espece
    ] + appel(TROUVE_MODELE) + [
        "cmp r0, #0",
        "popne {r4, r5, pc}",               # le vrai modele est deja la
        "mov r0, r5",
        "bl #{@declencheur}",               # CHARGER le modele de l'espece
        "mov r1, r5",
    ] + appel(TROUVE_MODELE) + [
        "cmp r0, #0",
        "popne {r4, r5, pc}",               # charge : l'apparence est JUSTE
        "ldr r4, [pc, #%s]" % lit(TABLE_EMPL),
        "mov r5, #0",
        "compte:",
        "ldr r0, [r4, r5, lsl #2]",
        "cmp r0, #0",
        "addne r5, r5, #1",
        "cmpne r5, #%d" % EMPLACEMENTS,
        "bne #{@compte}",
        "movs r0, r5",
        "popeq {r4, r5, pc}",               # aucun modele : r0 vaut 0
    ] + appel(RAND) + [
        "ldr r0, [r4, r0, lsl #2]",
        "pop {r4, r5, pc}",
    ]

    etiq = {}
    code = assembler(lignes, BASE, litteraux=tuple(pool), etiquettes_out=etiq)

    # --- reecrire les donnees reservees ---
    octets = bytearray(code)
    def ecrire(offset, valeur):
        struct.pack_into("<I", octets, offset - BASE, valeur & 0xFFFFFFFF)

    for k in range(MOTS_N):
        ecrire(etiq["mots"] + 4 * k, 0)
    for k in range(MODELES_N):
        ecrire(etiq["modeles"] + 4 * k, 0)
    for k in range(0, len(especes), 2):
        bas = especes[k]
        haut = especes[k + 1] if k + 1 < len(especes) else 0
        ecrire(etiq["especes"] + 2 * k, bas | (haut << 16))
    for k in range(SRC_N):
        ecrire(etiq["src"] + 4 * k, 0)
    for k in range(NOEUD_N):
        ecrire(etiq["noeud"] + 4 * k, 0)
    ecrire(etiq["talon_off"], etiq["talon_source"])

    paires = [
        (SITE_VIDE, etiq["greffe_a"]),
        (SITE_TABLEAU, etiq["greffe_borne"]),
        (SITE_VRAM, etiq["greffe_c"]),
        (SITE_DEPART, etiq["greffe_d"]),
        (SITE_ESPECE, etiq["greffe_e"]),
        (SITE_BOUCLE, etiq["greffe_borne"]),
        (SITE_MODELE, etiq["emprunt"]),
        (SITE_PORTIER1_SPAWN, etiq["portier1"]),
        (SITE_PORTIER1_PRECH, etiq["portier1"]),
        (SITE_PORTIER2_SPAWN, etiq["portier2"]),
        (SITE_PORTIER2_RELU, etiq["portier2"]),
        (SITE_PORTIER2_PRECH, etiq["portier2"]),
        (SITE_MODELE_ALLOC, etiq["greffe_modele"]),
        (SITE_BATIR, etiq["greffe_donnees"]),
    ]
    if len(paires) >= TABLE_ENTREES:
        raise SystemExit(f"table : {len(paires)} entrees pour {TABLE_ENTREES - 1}")
    pas = 4 * MOTS_PAR_ENTREE
    for k, (site, cible) in enumerate(paires):
        if site not in originaux:
            raise SystemExit(f"le mot d'origine de {site:#010x} manque")
        ecrire(etiq["table"] + pas * k, site)
        ecrire(etiq["table"] + pas * k + 4, cible)
        ecrire(etiq["table"] + pas * k + 8, originaux[site])
    ecrire(etiq["table"] + pas * len(paires), 0)        # le zero terminal

    entete = struct.pack("<II", etiq["installateur"], etiq["desinstalleur"])
    return bytes(entete) + bytes(octets), etiq
