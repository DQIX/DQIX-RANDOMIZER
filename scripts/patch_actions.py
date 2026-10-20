#!/usr/bin/env python3
"""Des SORTS et des TECHNIQUES tires au hasard pour les monstres, A CHAQUE
COMBAT (ZER-56 sorts, ZER-57 techniques).

CE QUE LE JEU FAIT (research §92-94).

  * Au chargement d'une zone, 0x020A8FE0 copie dans le tas les fiches
    `mon_moddata` des especes de la zone. Au DEBUT DE CHAQUE COMBAT,
    l'overlay 0 (0x02165A54..0x02165BAC) reecrit la copie de combat
    (`mon_btldata`, 0x84 o par espece presente) depuis ces fiches, dont
    LES SIX ACTIONS : `bl memcpy` en 0x02165AEC (r0 = copie+0x18,
    r1 = fiche+0x32, r2 = 12). Un tirage pose la vaut pour ce combat.
  * LES CONDITIONS SONT DANS LE JEU : chaque action porte un type de cible
    dont le gestionnaire la refuse s'il n'y a pas de cible utile (soin :
    un allie sous 50 % ; Rappel : un allie mort ; Kamikaze : lanceur sous
    50 %...). Le choix d'emplacement (0x0208A380) passe alors a un autre.
  * LA MISE EN SCENE d'une action vient du `.bact` du modele du monstre,
    sinon de `data/bin/actdef.nsarc/default.bact` (un cas generique par
    liste d'actions `op01 [...]`), sinon d'un repli sans texte ni animation.
    Les sorts ont une mise en scene generique a part. Une technique sans cas
    ne montre donc rien : on l'ajoute a un cas generique de default.bact --
    le « coup » (action 934) si elle vise l'adversaire, l'aura de Tension
    (161) sinon. Mesure en jeu : texte, animation, degats. Le cas propre du
    monstre reste prioritaire (champigoule : son Haleine fraiche).
    default.bact ne supporte que ~660 commandes (740 : le combat gele) : on
    ALLONGE des listes existantes, sans ajouter une seule commande. Les
    attaques qui ne tiennent plus dans le « coup » vont, par famille, aux
    cas 944 (coup simple), 945 (nuage sur la cible) et 921 (intimidation),
    vus en jeu ; trois autres cas font geler le combat (research §94.6).

CE QUE FAIT CE PATCH.

  * A LA CONSTRUCTION, dans `mon_btldata`, deux octets a zero dans les
    438 fiches d'origine (bourrage de fin) recoivent les masques des
    emplacements a tirer : `+0x82` les sorts, `+0x83` les techniques.
    Zero pour les boss et le prologue. Par sorte d'action, un mode :
      - `remplacer` : les emplacements qui en portent une d'origine ;
      - `ajouter`   : pareil, et une espece qui n'en a pas en recoit une, sur
                      UN emplacement (un doublon de l'Attaque, voir
                      `emplacement_ajoute`), l'action d'origine y est ecrite ;
      - `tous`      : les six emplacements (ROM d'essai uniquement).
  * EN COMBAT, DEUX SITES. Juste apres la construction de la copie de
    combat (0x02165A30), on tire pour TOUTES les especes presentes : le blob
    fait apparaitre des especes hors de la table de zone, que l'overlay 0
    ne reecrit pas depuis mon_moddata (§94.4). Puis a la copie des actions
    de mon_moddata (0x02165AEC, especes de la zone seulement), qui ecrase le
    premier tirage, on retire. Dans les deux cas le masque est lu dans la
    copie de combat (+0x82).
  * La greffe fait la copie, tire un sort ou une technique pour chaque
    emplacement marque -- UNE table de 1 024 bits porte les deux pools
    (sorts 0x09..0x3E sauf 0x1D, techniques >= 0x3F), UNE routine les tire
    (ZER-93 : le pool des sorts devient editable, « Creer sa ROM ») -- et
    fixe les PM : max(PM d'origine, 3 x cout de l'action tiree la plus chere),
    plafond 255 ; « tous les PM » (Explosion magique...) ne compte pas.

UNE ESPECE, UN TIRAGE : la copie de combat a une fiche par ESPECE presente.

OU VIT LE CODE : DANS L'OVERLAY 0, sans place libre. Trois blocs qui
recopient des champs de bits un a un sont reecrits a l'identique, plus
courts ; la greffe loge dans la place gagnee :

    0x02165AB0  52 instr.  -> 20 (champs de fiche+0x0C) + la table de bits
    0x021556D4  50 instr.  -> 15 + la greffe (tirage, PM)
    0x021557C0  53 instr.  -> 19 + la routine de tirage (8 o libres)

`verifier_equivalence()` prouve les trois reecritures par emulation.
"""
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OVL = 0
MEMCPY = 0x02001A40
RAND_BELOW = 0x02032380          # r0 = [0, r0[   (patch_butin)
BASE_ACTIONS = 0x020797EC        # rend la base des actions (0x02108E10)
ACTION = 0x02079E3C              # (base, id) -> fiche d'action, cout en +8

# bloc 1 : la copie des actions au debut du combat
BLOC = 0x02165AB0
SUITE = 0x02165B80
TABLE = 0x02165B00               # 128 o : un bit par identifiant d'action
# bloc 2 : champs de bits de [r4+0x138] vers le tampon r5
B2, B2_SUITE = 0x021556D4, 0x0215579C
GREFFE = 0x02155710
# bloc 3 : champs de bits de [r6+0x138] vers le tampon r5
B3, B3_SUITE = 0x021557C0, 0x02155894
TIRAGES = 0x0215580C

SORT_PREMIER, SORT_DERNIER = 0x09, 0x3E
SORTS_EXCLUS = (0x1D,)           # le seul trou de la plage
# Bornes de la routine de tirage (le minimum rejete est borne >> 4)
BORNE_SORTS, BORNE_TECH = SORT_DERNIER + 1, 0x3F0
assert BORNE_SORTS >> 4 <= SORT_PREMIER and BORNE_TECH >> 4 == BORNE_SORTS
# Doublons de sorts propres aux monstres (research §92.2)
SORTS_MONSTRES = (0xF6, 0xF7, 0x12A) + tuple(range(0x1C7, 0x1D5))
FACTEUR_PM = 3
ATTAQUE = 0x0001

MOD = "/data/prm/mon_moddata.nat"
BTL = "/data/prm/mon_btldata.nat"
ACTDEF = "data/bin/actdef.nsarc"
ENTETE, MOD_TAILLE, BTL_TAILLE = 4, 64, 132
MOD_ACTIONS, MOD_IA = 0x32, 0x0C
BTL_ACTIONS = 0x18
# LES MASQUES VIVENT DANS mon_btldata, +0x82 (sorts) et +0x83 (techniques) :
# deux octets a zero dans les 438 fiches (bourrage de fin). La copie de combat
# (0x84 o) existe pour TOUTES les especes presentes, alors que la fiche
# mon_moddata n'est recopiee que pour celles de la table de zone -- or le
# blob tire des especes hors de cette table (mesure du 26/09, §94.4).
BTL_MASQUE, BTL_MASQUE_T = 0x82, 0x83
# second site : juste apres la construction de la copie de combat
SITE2 = 0x02165A30
ORIGINE_SITE2 = bytes.fromhex("6fb5faeb")      # bl 0x02012FF4
APRES_SITE2 = 0x02012FF4
CAS_COUP, CAS_AURA = 934, 161    # cas generiques de default.bact
# Les attaques qui ne tiennent plus dans les listes du 934 (des attaques de
# monstres ordinaires, sans nom) vont, par famille, a trois autres cas vus en
# jeu le 26/09 (piste A, research §94.6) : 944 un coup simple, 945 un nuage
# violet sur la cible (jets, crachats), 921 ecran sombre et « ! » au-dessus
# du monstre (intimidations). Les renforts vont a l'aura : leur cas propre
# (242) gele le combat quand personne ne vient (mesure).
CAS_COUP2, CAS_NUAGE, CAS_CRI = 944, 945, 921
NUAGES = (0x143, 0x144, 0x147, 0x14C, 0x219, 0x23C)  # sable, vomi, encre...
CRIS = (0x220, 0x23B, 0x23E)            # yeux malefiques, grimace, cri

# Poids des six emplacements par type d'IA (table 0x020E8CBA, research §93.1).
POIDS = {0: (43, 42, 43, 43, 42, 43), 1: (68, 58, 48, 38, 27, 17),
         2: (210, 29, 10, 4, 2, 1), 4: (70, 70, 70, 16, 15, 15)}
UNIFORME = POIDS[0]
MODES = ("remplacer", "ajouter", "tous")

# Empreintes des blocs d'origine (vanilla) : on ne reecrit que ce qu'on connait.
ORIGINE = bytes.fromhex(
    "0cc096e5103094e50cc5a0e12ccfa0e11830c3e30ccfa0e1ac3d83e1103084e5"
    "0cc096e5e030c3e38ccea0e1accea0e18ccea0e12c3c83e1103084e5d36ffaeb"
    "0c0096e5101094e5800ba0e1200da0e13f16c1e3000da0e1200381e1100084e5"
    "0c2096e5071cc0e3022aa0e1a22ea0e1822ea0e1a21a81e1101084e50c2096e5"
    "061bc1e30229a0e1222fa0e1022fa0e1a21981e1101084e50c2096e50e1ac1e3"
    "8227a0e1a22ea0e1822ea0e1221881e1101084e50c2096e50718c1e30226a0e1"
    "a22ea0e1822ea0e1a21681e1101084e5")
ORIGINE2 = bytes.fromhex(
    "381194e5b801d5e1b222d1e10310c0e3020fa0e1200fa0e1030000e2000081e1"
    "b801c5e1381194e5b801d5e1b222d1e13c10c0e3020da0e1200ea0e1000ea0e1"
    "200d81e1b801c5e1381194e5b801d5e1b222d1e1071dc0e3820ba0e1a00ea0e1"
    "800ea0e1a00b81e1b801c5e1381194e51c00d5e52120d1e50f10c0e30f0002e2"
    "000081e11c00c5e5381194e5ff0000e22420d1e5f010c0e3020ea0e1200c81e1"
    "1c00c5e5381194e5b801d5e1b222d1e10e1cc0e3020aa0e1a00ea0e1800ea0e1"
    "200a81e1b801c5e1")
ORIGINE3 = bytes.fromhex(
    "381196e5ba01d5e1b222d1e10310c0e3020fa0e1200fa0e1030000e2000081e1"
    "ba01c5e1381196e5ba01d5e1b222d1e1e030dde53c10c0e3020da0e1200ea0e1"
    "000ea0e1200d81e1ba01c5e1381196e5ba01d5e1b2c2d1e102298ae2071dc0e3"
    "8c0ba0e1a00ea0e1800ea0e1a00b81e1ba01c5e1380196e51dc0d5e52110d0e5"
    "0400a0e10f40cce30f1001e2011084e11d10c5e5384196e5ff1001e224c0d4e5"
    "f040c1e30c1ea0e1211c84e11d10c5e5384196e5ba11d5e1b2c2d4e10e4cc1e3"
    "0c1aa0e1a11ea0e1811ea0e1211a84e1ba11c5e1")


# --------------------------------------------------------------------------
# Les listes d'actions

def sorts():
    """Les identifiants de sorts tirables, dans l'ordre."""
    return [i for i in range(SORT_PREMIER, SORT_DERNIER + 1)
            if i not in SORTS_EXCLUS]


def sorts_tirables():
    """Le pool des sorts par defaut : toute la plage (alias de sorts(),
    que `patcher` masque par son argument du meme nom)."""
    return sorts()


def est_sort(action):
    return (SORT_PREMIER <= action <= SORT_DERNIER
            and action not in SORTS_EXCLUS) or action in SORTS_MONSTRES


def actions_rom(rom):
    """{identifiant: fiche de 60 o} des deux bases d'actions (actdt_a et
    actdt_b, membre anglais ; les champs sont les memes dans les 5 langues).
    La fiche est prise comme dans le fichier : +6 l'identifiant (10 bits),
    +10 le cout en PM, +11 le type d'action (4 bits bas : 9 contre
    l'adversaire, 0xA soi ou ses allies, 0xE soin)."""
    from gp2 import GP2
    out = {}
    for nom in ("actdt_b", "actdt_a"):
        data = bytes(rom.files[rom.filenames.idOf("data/prm/%s.gp2" % nom)])
        g = GP2(nom, data)
        ent = sorted(g.entrees, key=lambda e: e[1] & 0xFFFFFF)
        _h, o, t = ent[2]                    # 0 actdamage, 1 de, 2 en
        m = data[g.first_file * 4 + (o & 0xFFFFFF) * 4:][:t]
        n = struct.unpack_from("<H", m, 0)[0] & 0x3FF
        for i in range(n):
            r = m[2 + i * 60:2 + i * 60 + 60]
            out.setdefault(struct.unpack_from("<H", r, 6)[0] & 0x3FF, r)
    return out


# Retirees du pool par le joueur (28/09 et 11/10, campagne de test des vraies
# animations) : elles n'ont pas de sens pour un monstre ou ne peuvent rien
# contre l'equipe. Forces (enchantent l'arme d'un personnage), Fauche et
# Detectoc (volent / inspectent un objet), Sifflet, Vent contraire (ne contre
# que les souffles), Danse des soins, et la fusion en roi gluant.
SANS_SENS_POUR_UN_MONSTRE = (0xB1, 0xB2, 0xB3, 0xB4, 0xB5,    # forces
                             0xA5, 0xA6,                       # Fauche, Detectoc
                             0x93, 0x68, 0x6C,                 # Sifflet, Vent contraire, Danse des soins
                             0x153, 0x31A)                     # « Les gluants... ils se... »


def techniques(rom, mod=None):
    """Le pool des techniques : celles que portent les monstres du bestiaire
    et celles que les personnages apprennent (0x3F..0xC9). Ni sort, ni
    Attaque/Defense/Fuite, ni objet, ni action systeme (>= 900), et une fiche
    d'action qui dit contre qui elle va. Rend {cas generique: [actions]},
    le cas de default.bact qui met chaque technique en scene."""
    from monstres_nommes import MONSTRES
    if mod is None:
        mod = bytes(rom.files[rom.filenames.idOf(MOD.lstrip("/"))])
    fiches = actions_rom(rom)
    portees = set()
    for i in MONSTRES:
        portees.update(struct.unpack_from("<6H", mod, ENTETE + i * MOD_TAILLE
                                          + MOD_ACTIONS))
    exclus = (set(range(0x09, 0x3F)) | {0, 1, 2, 3, 0xE1, 0xEC, CAS_AURA}
              | set(SANS_SENS_POUR_UN_MONSTRE))
    pool = sorted(a for a in portees | set(range(0x3F, 0xCA))
                  if a not in exclus and not est_sort(a) and a < 900
                  and a in fiches and fiches[a][11] & 0xF in (0x9, 0xA, 0xE))
    # LA PLACE DANS default.bact EST COMPTEE (voir allonger_default) : au plus
    # quatre listes pour le « coup » 934, deux pour l'aura ; le reste des
    # attaques va au coup 944, les renforts a leur cas. Les actions qui ont un
    # nom (le message de combat le cite) passent d'abord, puis par numero.
    noms = noms_actions(rom)
    cle = lambda a: (a not in noms, a)
    adverse = sorted((a for a in pool if fiches[a][11] & 0xF == 0x9), key=cle)
    soi = sorted((a for a in pool if fiches[a][11] & 0xF != 0x9), key=cle)
    n = LISTES_COUP * LISTE_MAX - 1
    reste = adverse[n:]
    out = {CAS_COUP: sorted(adverse[:n]),
           CAS_COUP2: sorted(a for a in reste if a not in NUAGES + CRIS),
           CAS_NUAGE: sorted(a for a in reste if a in NUAGES),
           CAS_CRI: sorted(a for a in reste if a in CRIS),
           CAS_AURA: sorted(soi)}
    if (any(len(out[c]) > LISTE_MAX - 1 for c in (CAS_COUP2, CAS_NUAGE,
                                                   CAS_CRI))
            or len(soi) > LISTES_AURA * LISTE_MAX - 1):
        raise SystemExit("default.bact : plus de techniques que de place "
                         "(%s)" % {c: len(l) for c, l in out.items()})
    return out


def noms_actions(rom):
    """Identifiants qui ont un nom dans actname.nat (anglais)."""
    an = bytes(rom.files[rom.filenames.idOf("data/prm/actname.nat")])
    out = set()
    k = 0
    while 0xC + 8 * k + 8 <= 0x1554:
        i, no = struct.unpack_from("<II", an, 0xC + 8 * k)
        if no:
            out.add(i)
        k += 1
    return out


# LES APPELS DE RENFORT (« <monstre> demande du renfort. », message 0x37 de
# actmsg). Neuf actions. L'espece appelee vient d'une table de l'overlay 0
# (0x02182E6C : action -> espece) et doit deja etre chargee dans le combat
# (0x02162D88), sinon le jeu refuse l'action ; 0xF2 et 0x1DA n'y sont pas.
# Gardees dans le pool (decision du joueur, 26/09), mises en scene par
# l'aura ; le renfort aleatoire reste a faire (ZER-57).
MSG_RENFORT = 0x37


def message_action(fiche):
    """Numero du message de combat d'une action (actmsg_<lg>.nat) : octets
    35-36 de la fiche, bits 2 a 11 (research §94.5)."""
    return (struct.unpack_from("<H", fiche, 35)[0] >> 2) & 0x3FF


def table_bits(pool):
    t = bytearray(128)
    for a in pool:
        t[a >> 3] |= 1 << (a & 7)
    return bytes(t)


# --------------------------------------------------------------------------
# Le code

def _asm(lignes, adr, litteraux=()):
    from patch_hasard import assembler
    return assembler(lignes, adr, litteraux=litteraux)


def bloc1(pool):
    """0x02165AB0 : champs de bits a l'identique, appel de la greffe, table."""
    code = _asm([
        # r0, r1, r2 sont deja poses pour la copie des actions (0x02165A80..90)
        "bl #%d" % GREFFE,
        #   S = [fiche+0x0C], D = [copie+0x10]
        #   D[3:4]   = S[20:21]      D[5:7]   = S[0:2]    (le type d'IA)
        #   D[20:25] = S[3:8]        D[8:18]  = S[9:19]   (quatre champs contigus)
        "ldr ip, [r6, #0xc]",
        "ldr r3, [r4, #0x10]",
        "bic r3, r3, #0xf8",
        "bic r3, r3, #0x3f00000",
        "bic r3, r3, #0xff00",
        "bic r3, r3, #0x70000",
        "and r0, ip, #7",
        "orr r3, r3, r0, lsl #5",
        "lsl r0, ip, #10",
        "lsr r0, r0, #30",
        "orr r3, r3, r0, lsl #3",
        "lsl r0, ip, #23",
        "lsr r0, r0, #26",
        "orr r3, r3, r0, lsl #20",
        "lsr r0, ip, #9",
        "lsl r0, r0, #21",
        "orr r3, r3, r0, lsr #13",
        "str r3, [r4, #0x10]",
        "b #%d" % SUITE,
    ], BLOC)
    assert BLOC + len(code) == TABLE, hex(BLOC + len(code))
    out = code + table_bits(pool)
    assert len(out) == SUITE - BLOC
    return out


def _greffe_lignes():
    t_sort, t_tech = _adresses_tirages()
    return [
        "push {r4, r5, r6, r7, r8, lr}",
        "mov r5, r0",                       # copie+0x18 : les actions
        "ldrh r7, [r0, #%d]" % (BTL_MASQUE - 0x18),   # copie+0x82, +0x83
        "bl #%d" % MEMCPY,
        "mov r8, #0",                       # cout le plus cher tire
        "mov r6, r5",
        "boucle:",
        "tst r7, #0x100",                   # technique ?
        "bne #{@tech}",
        "tst r7, #1",                       # sort ?
        "beq #{@suivant}",
        "bl #%d" % t_sort,
        "b #{@pose}",
        "tech:",
        "bl #%d" % t_tech,
        "pose:",
        "mov r4, r0",
        "strh r4, [r6]",
        "bl #%d" % BASE_ACTIONS,
        "mov r1, r4",
        "bl #%d" % ACTION,
        "ldrb r0, [r0, #8]",                # cout en PM
        "cmp r0, #255",                     # « tous les PM » : ne compte pas
        "cmpne r0, r8",
        "movhi r8, r0",
        "suivant:",
        "add r6, r6, #2",
        "lsr r7, r7, #1",
        "sub r0, r6, r5",
        "cmp r0, #12",
        "blt #{@boucle}",
        "add r8, r8, r8, lsl #1",           # FACTEUR_PM = 3
        "cmp r8, #255",
        "movhi r8, #255",
        "ldrh r0, [r5, #%d]" % (0x5E - 0x18),
        "cmp r8, r0",
        "strhhi r8, [r5, #%d]" % (0x5E - 0x18),
        "pop {r4, r5, r6, r7, r8, pc}",
    ]


def _tirages_lignes():
    # UNE SEULE ROUTINE (ZER-93) : sorts et techniques sont dans la MEME
    # table de bits. r0 = la borne B ; on tire dans [0, B[, on rejette ce qui
    # est sous B >> 4, puis tout identifiant dont le bit est a 0. Sorts :
    # B = 0x3F (0..0x3E ; les bits 0..8 et 0x1D ne sont jamais poses) ;
    # techniques : B = 0x3F0, minimum 0x3F (les sorts ne sortent pas).
    return [
        "tire_sort:",
        "mov r0, #%d" % BORNE_SORTS,
        "b #{@tire}",
        "tire_tech:",
        "mov r0, #%d" % BORNE_TECH,
        "tire:",
        "push {r3, r4, r5, lr}",
        "mov r5, r0",
        "ldr r4, [pc, #{L0}]",
        "tt:",
        "mov r0, r5",
        "bl #%d" % RAND_BELOW,
        "cmp r0, r5, lsr #4",
        "blo #{@tt}",
        "ldrb r1, [r4, r0, lsr #3]",
        "and r2, r0, #7",
        "lsr r1, r1, r2",
        "tst r1, #1",
        "beq #{@tt}",
        "pop {r3, r4, r5, pc}",
        # SECOND SITE (0x02165A30, a la place de `bl 0x02012FF4`) : la copie
        # de combat vient d'etre construite pour toutes les especes
        # presentes ; on tire pour chacune (la copie sur elle-meme de la
        # greffe est sans effet), puis on rend la main a 0x02012FF4.
        "toutes:",
        "push {r4, r5, r6, lr}",
        "add r4, r5, #0x400",               # la table : [+0] nombre, [+4] fiches
        "ldr r6, [r4, #4]",
        "ldr r4, [r4]",
        "lsl r4, r4, #20",                  # nombre sur 12 bits, en haut
        "t2:",
        "subs r4, r4, #0x100000",
        "bmi #{@t2fin}",
        "add r0, r6, #0x18",
        "mov r1, r0",
        "mov r2, #12",
        "bl #%d" % GREFFE,
        "add r6, r6, #0x84",
        "b #{@t2}",
        "t2fin:",
        "pop {r4, r5, r6, lr}",
        "b #%d" % APRES_SITE2,
    ]


def _adresses_tirages():
    from patch_hasard import assembler
    etiq = {}
    assembler(_tirages_lignes(), TIRAGES, litteraux=(TABLE,),
              etiquettes_out=etiq)
    return etiq["tire_sort"], etiq["tire_tech"]


def adresse_toutes():
    from patch_hasard import assembler
    etiq = {}
    assembler(_tirages_lignes(), TIRAGES, litteraux=(TABLE,),
              etiquettes_out=etiq)
    return etiq["toutes"]


def bloc3():
    """0x021557C0 : [r5+0x1A] bits 0-11 <- [s+0x22] bits 0-11 ;
    [r5+0x1D] <- ([s+0x21] & 15) | ([s+0x24] & 15) << 4 ; s = [r6+0x138].
    Registres rendus comme l'original : r0 = r4 d'entree, r2 = sl+0x8000,
    r3 = [sp+0xE0], ip = [s+0x22], r4 = [r5+0x1A] final & ~0xE00.
    Puis les deux fonctions de tirage."""
    compact = _asm([
        "ldrb r3, [sp, #0xe0]",
        "add r2, sl, #0x8000",
        "mov r0, r4",
        "ldr r4, [r6, #0x138]",
        "ldrb r1, [r4, #0x21]",
        "ldrb ip, [r4, #0x24]",
        "and r1, r1, #0xf",
        "and ip, ip, #0xf",
        "orr r1, r1, ip, lsl #4",
        "strb r1, [r5, #0x1d]",
        "ldrh ip, [r4, #0x22]",
        "ldrh r1, [r5, #0x1a]",
        "lsr r1, r1, #12",
        "lsl r1, r1, #12",
        "lsl r4, ip, #20",
        "orr r1, r1, r4, lsr #20",
        "strh r1, [r5, #0x1a]",
        "bic r4, r1, #0xe00",
        "b #%d" % B3_SUITE,
    ], B3)
    assert B3 + len(compact) == TIRAGES
    tir = _asm(_tirages_lignes(), TIRAGES, litteraux=(TABLE,))
    out = compact + tir
    if len(out) > B3_SUITE - B3:
        raise SystemExit("bloc 3 : %d o pour %d" % (len(out), B3_SUITE - B3))
    return out + bytes(B3_SUITE - B3 - len(out))


def blocs(pool):
    g = _asm(_greffe_lignes(), GREFFE)
    compact2 = bloc2_compact()
    b2 = compact2 + g
    if len(b2) > B2_SUITE - B2:
        raise SystemExit("bloc 2 : %d o pour %d" % (len(b2), B2_SUITE - B2))
    b2 += bytes(B2_SUITE - B2 - len(b2))
    site2 = _asm(["bl #%d" % adresse_toutes()], SITE2)
    return [(BLOC, ORIGINE, bloc1(pool)), (B2, ORIGINE2, b2),
            (B3, ORIGINE3, bloc3()), (SITE2, ORIGINE_SITE2, site2)]


def bloc2_compact():
    code = _asm([
        "ldr r1, [r4, #0x138]",
        "ldrh r0, [r5, #0x18]",
        "ldrh r2, [r1, #0x22]",
        "lsr r0, r0, #12",
        "lsl r0, r0, #12",
        "lsl r2, r2, #20",
        "orr r0, r0, r2, lsr #20",
        "strh r0, [r5, #0x18]",
        "ldrb r0, [r1, #0x21]",
        "ldrb r2, [r1, #0x24]",
        "and r0, r0, #0xf",
        "and r2, r2, #0xf",
        "orr r0, r0, r2, lsl #4",
        "strb r0, [r5, #0x1c]",
        "b #%d" % B2_SUITE,
    ], B2)
    assert B2 + len(code) == GREFFE
    return code


# --------------------------------------------------------------------------
# default.bact

def _bact_lire(d):
    """Commandes d'un .bact : u16 op, u8 n, u8 types (2 bits par argument) ;
    si n > 4, un mot 0xFFFFFFtt porte les types des arguments 4..7."""
    h = struct.unpack_from("<4I", d, 0)
    p, out = 0x10, []
    for _ in range(h[0]):
        op, n, _ty = struct.unpack_from("<HBB", d, p)
        q = p + 4 + (4 if n > 4 else 0)
        args = list(struct.unpack_from("<%dI" % n, d, q))
        q += 4 * n
        out.append((p, op, args, q - p))
        p = q
    return h, out


def _op01(ids):
    n = len(ids)
    out = struct.pack("<HBB", 1, n, 0x55 & ((1 << (2 * min(n, 4))) - 1))
    if n > 4:
        out += struct.pack("<I", 0xFFFFFF00
                           | (0x55 & ((1 << (2 * min(n - 4, 4))) - 1)))
    return out + b"".join(struct.pack("<I", x) for x in ids)


LISTE_MAX = 40                  # 40 par liste : mesure ; 50 fait geler
LISTES_COUP, LISTES_AURA = 4, 2  # 650 commandes en tout (662 passent)
COMMANDES_MAX = 662             # mesure : 662 passent, 740 font geler


def allonger_default(d, ajouts):
    """Rattache des actions aux cas generiques de default.bact :
    {cas: [actions]}. La liste `op01 [cas]` d'origine est allongee jusqu'a
    LISTE_MAX actions ; au-dela, le cas est DUPLIQUE a la fin du fichier
    (meme corps, nouvelle liste), par paquets de LISTE_MAX. Mesures en jeu :
    une liste de 50 fait geler le combat, deux de 40 passent ; ~660
    commandes passent, 740 font geler."""
    ajouts = {c: [a for a in l if a != c] for c, l in ajouts.items()}
    tete = {c: l[:LISTE_MAX - 1] for c, l in ajouts.items()}
    reste = {c: l[LISTE_MAX - 1:] for c, l in ajouts.items()}
    d = _allonger(d, tete)
    h, cmds = _bact_lire(d)
    fin = cmds[-1][0] + cmds[-1][3]
    out = bytearray(d[:fin])
    ncmd = h[0]
    for c, l in reste.items():
        if not l:
            continue
        k = [i for i, x in enumerate(cmds) if x[1] == 1 and x[2][0] == c][0]
        m = k + 1
        while cmds[m][1] != 2:
            m += 1
        corps = b"".join(d[p:p + t] for p, _o, _a, t in cmds[k + 1:m + 1])
        for g in range(0, len(l), LISTE_MAX):
            out += _op01(l[g:g + LISTE_MAX]) + corps
            ncmd += 1 + (m - k)
    out += d[fin:h[1]]
    pool = len(out)
    out += d[h[1]:]
    struct.pack_into("<I", out, 0, ncmd)
    struct.pack_into("<I", out, 4, pool)
    h2, c2 = _bact_lire(bytes(out))
    assert c2[-1][0] + c2[-1][3] == pool - 4
    return bytes(out)


def _allonger(d, ajouts):
    """Allonge les listes `op01 [cas]` existantes, sans ajouter de commande."""
    h, cmds = _bact_lire(d)
    vus = set()
    out = bytearray(d[:0x10])
    for p, op, args, t in cmds:
        brut = d[p:p + t]
        if op == 1 and len(args) == 1 and args[0] in ajouts:
            brut = _op01(args + ajouts[args[0]])
            vus.add(args[0])
        out += brut
    if vus != set(ajouts):
        raise SystemExit("default.bact : cas introuvables %s"
                         % sorted(set(ajouts) - vus))
    fin = cmds[-1][0] + cmds[-1][3]
    out += d[fin:h[1]]                       # le mot de fin
    pool = len(out)
    out += d[h[1]:]
    struct.pack_into("<I", out, 4, pool)
    h2, c2 = _bact_lire(bytes(out))
    assert h2[0] == h[0] and c2[-1][0] + c2[-1][3] == pool - 4
    return bytes(out)


def actions_default(d):
    """Toutes les actions qui ont un cas dans default.bact."""
    _h, cmds = _bact_lire(d)
    return {a for _p, op, args, _t in cmds if op == 1 for a in args}


# --------------------------------------------------------------------------
# Les masques

def emplacement_ajoute(actions, ia, pris=()):
    """Mode `ajouter` : l'emplacement qui recoit l'action d'une espece qui
    n'en a pas. Le jeu a SIX emplacements fixes (table de poids par type
    d'IA) : on ne peut pas en ajouter un septieme, on en prend un qui fait
    doublon -- l'Attaque d'abord -- et, parmi eux, celui dont le poids est le
    plus proche d'un sixieme (43/256). Rend None s'il n'y en a pas."""
    poids = POIDS.get(ia, UNIFORME)
    compte = {a: actions.count(a) for a in actions}
    for filtre in (lambda a: a == ATTAQUE and compte[a] > 1,
                   lambda a: compte[a] > 1):
        cands = [i for i, a in enumerate(actions) if filtre(a) and i not in pris]
        if cands:
            return min(cands, key=lambda i: (abs(poids[i] - 43), poids[i], -i))
    return None


def eligibles(mod):
    """Index des fiches qui peuvent recevoir des actions : le bestiaire, sans
    boss ni combat du prologue."""
    from monstres_nommes import MONSTRES
    PROLOGUE = (290, 292)
    out = []
    for i in range(struct.unpack_from("<I", mod, 0)[0]):
        ident = struct.unpack_from("<H", mod, ENTETE + i * MOD_TAILLE)[0]
        if i in MONSTRES and ident not in PROLOGUE:
            out.append(i)
    return out


def marquer(mod, btl, sorts_mode, tech_mode, pool, rng):
    """Pose les masques (et, en mode `ajouter`, l'action d'origine de l'espece
    qui n'en avait pas). Rend un bilan."""
    for m in (sorts_mode, tech_mode):
        if m is not None and m not in MODES:
            raise ValueError(m)
    pool_set = set(pool)
    bilan = {"a_sorts": 0, "sorts_ajoutes": 0, "a_techniques": 0,
             "techniques_ajoutees": 0, "sans_place": 0}
    for i in eligibles(mod):
        om = ENTETE + i * MOD_TAILLE
        ob = ENTETE + i * BTL_TAILLE
        if btl[ob + BTL_MASQUE] or btl[ob + BTL_MASQUE_T]:
            raise SystemExit("mon_btldata : fiche %d, +0x82 n'est pas a zero" % i)
        actions = list(struct.unpack_from("<6H", mod, om + MOD_ACTIONS))
        ia = struct.unpack_from("<I", mod, om + MOD_IA)[0] & 7
        ms = sum(1 << k for k, a in enumerate(actions) if est_sort(a))
        mt = sum(1 << k for k, a in enumerate(actions) if a in pool_set)
        bilan["a_sorts"] += bool(ms)
        bilan["a_techniques"] += bool(mt)
        if sorts_mode is None:
            ms = 0
        if tech_mode is None:
            mt = 0
        if sorts_mode == "tous":
            ms, mt = 0x3F, 0
        if tech_mode == "tous":
            ms, mt = 0, 0x3F
        pris = {k for k in range(6) if (ms | mt) >> k & 1}
        for mode, masque, choix, cle in (
                (sorts_mode, ms, sorts(), "sorts_ajoutes"),
                (tech_mode, mt, list(pool), "techniques_ajoutees")):
            if mode == "ajouter" and not masque:
                k = emplacement_ajoute(actions, ia, pris)
                if k is None:
                    bilan["sans_place"] += 1
                    continue
                actions[k] = rng.choice(choix)
                pris.add(k)
                bilan[cle] += 1
                if cle == "sorts_ajoutes":
                    ms = 1 << k
                else:
                    mt = 1 << k
        if actions != list(struct.unpack_from("<6H", mod, om + MOD_ACTIONS)):
            struct.pack_into("<6H", mod, om + MOD_ACTIONS, *actions)
            struct.pack_into("<6H", btl, ob + BTL_ACTIONS, *actions)
        btl[ob + BTL_MASQUE] = ms
        btl[ob + BTL_MASQUE_T] = mt
    return bilan


def _fid(rom, chemin):
    return rom.filenames.idOf(chemin.lstrip("/"))


# --------------------------------------------------------------------------

def poser_code(rom, pool_sorts, cas, animations=True, bavard=True,
               techs_table=()):
    """Pose les blocs de l'overlay 0, la table de tirage = `pool_sorts` +
    les techniques de `cas` ({cas generique: [ids]}, vide : aucune), et la
    mise en scene des techniques : les vraies animations (variantes rnd/)
    ou, sans elles, les cas generiques allonges de default.bact. Ne touche
    ni aux actions ni aux masques. Rend un bilan. `techs_table` : des
    techniques mises dans la table SANS mise en scene (config sans
    emplacement de technique : elles ne sont jamais tirees).

    LA REPARTITION EN VARIANTES NE DEPEND QUE DU POOL (ZER-93) : la meme
    config donne la meme ROM, quelle que soit la graine qui l'a tiree."""
    import ndspy.code
    import ndspy.narc
    techs = sorted(a for l in cas.values() for a in l)
    if techs and techs_table:
        raise ValueError("techs_table : seulement sans mise en scene")
    if any(not est_sort(a) or a in SORTS_MONSTRES for a in pool_sorts):
        raise ValueError("pool des sorts : %s" % sorted(pool_sorts))
    if any(a < BORNE_SORTS or a >= BORNE_TECH for a in techs + list(techs_table)):
        raise ValueError("pool des techniques hors de [0x3F, 0x3F0[")
    ovl = rom.loadArm9Overlays()
    o = ovl[OVL]
    d = bytearray(o.data)
    for adr, avant, apres in blocs(sorted(set(pool_sorts) | set(techs)
                                          | set(techs_table))):
        i = adr - o.ramAddress
        if bytes(d[i:i + len(avant)]) != avant:
            raise SystemExit("overlay 0 : bloc 0x%08X inattendu (deja "
                             "patche ?)" % adr)
        assert len(apres) == len(avant)
        d[i:i + len(avant)] = apres
    o.data = bytes(d)
    rom.files[o.fileID] = o.save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)
    bilan = {}
    if techs and animations:
        # LES VRAIES ANIMATIONS (patch_animations) : le combat lit une
        # variante rnd/aNN.nsarc a la place d'actdef.nsarc ; default.bact
        # d'origine reste intact (il sert de base aux variantes). Chaque
        # variante porte sa table de tirage : les sorts y sont aussi.
        import patch_animations
        import zlib
        bilan["variantes"] = patch_animations.patcher(
            rom, cas, seed="pool-%08x" % zlib.crc32(table_bits(techs)),
            bavard=bavard, sorts=pool_sorts)
    elif techs:
        fa = rom.filenames.idOf(ACTDEF)
        narc = ndspy.narc.NARC(rom.files[fa])
        narc.files[0] = allonger_default(bytes(narc.files[0]), cas)
        bilan["commandes"] = struct.unpack_from("<I", narc.files[0], 0)[0]
        if bilan["commandes"] > COMMANDES_MAX:
            raise SystemExit("default.bact : %d commandes, le combat gele "
                             "au-dela de ~%d" % (bilan["commandes"],
                                                 COMMANDES_MAX))
        rom.files[fa] = narc.save()
    return bilan


def patcher(rom, sorts=None, techniques_mode=None, seed=0, bavard=True,
            mode=None, animations=False):
    """Pose les trois blocs de l'overlay 0, marque `mon_moddata` et, pour les
    techniques, allonge les deux cas generiques de default.bact.
    `sorts`, `techniques_mode` : None, `remplacer`, `ajouter` ou `tous`.
    (`mode` : ancien nom de `sorts`.) Rend le bilan."""
    if mode is not None:
        sorts = mode
    if sorts is None and techniques_mode is None:
        raise ValueError("ni sorts ni techniques")
    fm, fb = _fid(rom, MOD), _fid(rom, BTL)
    mod, btl = bytearray(rom.files[fm]), bytearray(rom.files[fb])
    cas = techniques(rom, bytes(mod))
    pool = sorted(a for l in cas.values() for a in l) if techniques_mode else []
    bilan = poser_code(rom, sorts_tirables(), cas if techniques_mode else {},
                       animations=animations, bavard=bavard)
    bilan.update(marquer(mod, btl, sorts, techniques_mode, pool,
                         random.Random("actions-%s" % seed)))
    rom.files[fm], rom.files[fb] = bytes(mod), bytes(btl)
    bilan["pool"] = len(pool)
    if bavard:
        if sorts:
            print("  sorts [%s] : tires a chaque combat parmi %d ; %d especes "
                  "a sorts%s" % (sorts, len(globals()["sorts"]()),
                                 bilan["a_sorts"],
                                 ", %d en recoivent un" % bilan["sorts_ajoutes"]
                                 if sorts == "ajouter" else ""))
        if techniques_mode:
            print("  techniques [%s] : tirees a chaque combat parmi %d (%d "
                  "pour soi) ; %d especes a techniques%s"
                  % (techniques_mode, len(pool), len(cas[CAS_AURA]),
                                    bilan["a_techniques"],
                                    ", %d en recoivent une"
                                    % bilan["techniques_ajoutees"]
                                    if techniques_mode == "ajouter" else ""))
            if not animations:
                print("  default.bact : %s (listes de %d au plus, %d "
                      "commandes)" % (", ".join("cas %d += %d" % (c, len(l))
                                                for c, l in cas.items()),
                                      LISTE_MAX, bilan["commandes"]))
        if bilan["sans_place"]:
            print("  %d ajout(s) sans place (six actions differentes)"
                  % bilan["sans_place"])
        print("  PM : max(origine, %d x cout de l'action tiree la plus chere),"
              " plafond 255 ; boss et prologue exclus" % FACTEUR_PM)
    return bilan


def lire(rom):
    """Ce que la ROM porte, pour « Creer sa ROM » (config_actions) :
    {"actions": [6 ids] par fiche (mon_moddata), "masques": [(sorts,
    techniques)] par fiche (mon_btldata +0x82/+0x83), "code": la greffe est
    posee, "sorts" / "techniques": les identifiants de la table de tirage
    (vides sans greffe)}."""
    mod = bytes(rom.files[_fid(rom, MOD)])
    btl = bytes(rom.files[_fid(rom, BTL)])
    n = struct.unpack_from("<I", mod, 0)[0]
    out = {"actions": [list(struct.unpack_from(
               "<6H", mod, ENTETE + i * MOD_TAILLE + MOD_ACTIONS))
               for i in range(n)],
           "masques": [(btl[ENTETE + i * BTL_TAILLE + BTL_MASQUE],
                        btl[ENTETE + i * BTL_TAILLE + BTL_MASQUE_T])
                       for i in range(n)],
           "code": False, "sorts": [], "techniques": []}
    o = rom.loadArm9Overlays()[OVL]
    i = BLOC - o.ramAddress
    if bytes(o.data[i:i + len(ORIGINE)]) == ORIGINE:
        return out
    t = TABLE - o.ramAddress
    table = bytes(o.data[t:t + 128])
    pool = [a for a in range(0x400) if table[a >> 3] >> (a & 7) & 1]
    for adr, _avant, apres in blocs(pool):
        j = adr - o.ramAddress
        if bytes(o.data[j:j + len(apres)]) != apres:
            raise AssertionError("overlay 0 : bloc 0x%08X inattendu" % adr)
    out.update(code=True, sorts=[a for a in pool if a < BORNE_SORTS],
               techniques=[a for a in pool if a >= BORNE_SORTS])
    return out


def retirer(rom, vanilla=None):
    """Defait `poser_code` : les blocs de l'overlay 0 reprennent leurs
    octets d'origine, les variantes (ou default.bact allonge) s'en vont.
    Un fichier dont le CONTENU redevient celui de `vanilla` reprend ses
    OCTETS (la recompression ne les rend pas). Les masques et les actions
    ne bougent pas."""
    import ndspy.code
    import ndspy.codeCompression as cc
    import patch_animations
    lu = lire(rom)
    if not lu["code"]:
        return
    if patch_animations.present(rom):
        patch_animations.retirer(rom)
    elif lu["techniques"]:
        import ndspy.narc
        fa = rom.filenames.idOf(ACTDEF)
        n = struct.unpack_from("<I", ndspy.narc.NARC(
            bytes(rom.files[fa])).files[0], 0)[0]
        if n != patch_animations.COMMANDES_ORIGINE:     # default.bact allonge
            if vanilla is None:
                raise SystemExit("default.bact allonge : la ROM d'origine "
                                 "est necessaire pour le rendre")
            rom.files[fa] = bytes(vanilla.files[fa])
    ovl = rom.loadArm9Overlays()
    o = ovl[OVL]
    d = bytearray(o.data)
    for adr, avant, apres in blocs(lu["sorts"] + lu["techniques"]):
        i = adr - o.ramAddress
        assert bytes(d[i:i + len(apres)]) == apres
        d[i:i + len(avant)] = avant
    o.data = bytes(d)
    rom.files[o.fileID] = o.save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)
    if vanilla is None:
        return
    ovl = rom.loadArm9Overlays()
    van = vanilla.loadArm9Overlays()
    for k in (OVL, 17):
        if bytes(ovl[k].data) == bytes(van[k].data):
            rom.files[van[k].fileID] = bytes(vanilla.files[van[k].fileID])
            ovl[k] = van[k]
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)
    a, b = (bytearray(cc.decompress(bytes(x.arm9))) for x in (rom, vanilla))
    for x in (a, b):                     # le pied de compression
        struct.pack_into("<I", x, patch_animations.COMPRESSED_END, 0)
    if a == b:
        rom.arm9 = bytes(vanilla.arm9)


def verifier(rom):
    """Relit la ROM : les trois blocs sont les notres, les masques ne visent
    que des especes eligibles et, hors `tous`, que des emplacements du bon
    genre ; la table et default.bact portent le pool. Rend (mode des sorts,
    mode des techniques), chacun None, `remplacer`, `ajouter` ou `tous`."""
    import ndspy.narc
    mod = bytes(rom.files[_fid(rom, MOD)])
    o = rom.loadArm9Overlays()[OVL]
    t = TABLE - o.ramAddress
    table = bytes(o.data[t:t + 128])
    pool = [a for a in range(0x400) if table[a >> 3] >> (a & 7) & 1]
    for adr, _avant, apres in blocs(pool):
        i = adr - o.ramAddress
        if bytes(o.data[i:i + len(apres)]) != apres:
            raise AssertionError("overlay 0 : bloc 0x%08X inattendu" % adr)
    pool_set = {a for a in pool if a >= BORNE_SORTS}     # les techniques
    import patch_animations
    if patch_animations.present(rom):
        # vraies animations : la table de tirage est celle de la variante du
        # combat ; la table posee ici (pool complet) = l'union des variantes
        patch_animations.verifier(rom, set(pool))
    elif pool_set:
        cas = actions_default(bytes(ndspy.narc.NARC(
            rom.files[rom.filenames.idOf(ACTDEF)]).files[0]))
        if not pool_set <= cas:
            raise AssertionError("default.bact : techniques sans mise en scene")
    from rom_vanilla import chemin_vanilla
    import ndspy.rom
    vmod = bytes(ndspy.rom.NintendoDSRom.fromFile(chemin_vanilla()).files[
        _fid(rom, MOD)])
    elig = set(eligibles(mod))
    modes = []
    btl = bytes(rom.files[_fid(rom, BTL)])
    for off, genre in ((BTL_MASQUE, est_sort), (BTL_MASQUE_T, pool_set.__contains__)):
        vus, tous, ajoute = False, True, False
        for k in range(struct.unpack_from("<I", mod, 0)[0]):
            om = ENTETE + k * MOD_TAILLE
            m = btl[ENTETE + k * BTL_TAILLE + off]
            if m and k not in elig:
                raise AssertionError("fiche %d (boss ou prologue) marquee" % k)
            if k not in elig:
                continue
            vus |= bool(m)
            tous &= m == 0x3F
            acts = struct.unpack_from("<6H", mod, om + MOD_ACTIONS)
            if m and m != 0x3F:
                for b in range(6):
                    if m >> b & 1 and not genre(acts[b]):
                        raise AssertionError("fiche %d : emplacement %d marque "
                                             "sans action du bon genre" % (k, b))
            va = struct.unpack_from("<6H", vmod, om + MOD_ACTIONS)
            if m and not any(genre(a) for a in va):
                ajoute = True
        modes.append(None if not vus else "tous" if tous
                     else "ajouter" if ajoute else "remplacer")
    return tuple(modes)


# --------------------------------------------------------------------------
# Preuves par emulation

def _uc():
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
    mu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    mu.mem_map(0x02000000, 0x400000)
    return mu


def _regs():
    from unicorn import arm_const as A
    return [getattr(A, "UC_ARM_REG_R%d" % i) for i in range(13)] + [
        A.UC_ARM_REG_SP]


def _equivalence_bloc(adr_orig, orig, neuf, suite, vivants, essais, rng):
    """Emule `orig` et `neuf` a `adr_orig` jusqu'a `suite` avec les memes
    registres et la meme memoire au hasard : meme memoire, memes registres
    vivants (index 0..12, 13 = sp)."""
    R = _regs()
    for e in range(essais):
        regs = [rng.getrandbits(32) for _ in range(13)]
        # r4, r5, r6, sl (r10) et sp pointent vers des zones distinctes
        regs[4], regs[5], regs[6], regs[10] = (0x02300000, 0x02301000,
                                               0x02302000, 0x02303000)
        sp = 0x023F0000
        zones = {a: bytes(rng.getrandbits(8) for _ in range(0x200))
                 for a in (0x02300000, 0x02301000, 0x02302000, 0x02304000,
                           0x02305000, sp)}
        etats = []
        for code in (orig, neuf):
            mu = _uc()
            mu.mem_write(adr_orig, code)
            for a, z in zones.items():
                mu.mem_write(a, z)
            # [r4+0x138] et [r6+0x138] -> deux structures a part
            mu.mem_write(0x02300000 + 0x138, struct.pack("<I", 0x02304000))
            mu.mem_write(0x02302000 + 0x138, struct.pack("<I", 0x02305000))
            for i, v in enumerate(regs):
                mu.reg_write(R[i], v)
            mu.reg_write(R[13], sp)
            mu.emu_start(adr_orig, suite, count=400)
            mem = b"".join(bytes(mu.mem_read(a, 0x200)) for a in sorted(zones))
            etats.append((mem, [mu.reg_read(R[i]) for i in vivants]))
        assert etats[0][0] == etats[1][0], ("memoire", e)
        assert etats[0][1] == etats[1][1], ("registres", e, etats[0][1],
                                            etats[1][1])


def verifier_equivalence(essais=1500):
    """Les blocs 2 et 3 reecrits = l'original ; le bloc 1 + la greffe :
    memes champs de bits, tirages dans les listes aux emplacements marques,
    PM selon la regle, pile et registres preserves."""
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1,
                                   UC_ARM_REG_R2, UC_ARM_REG_R4,
                                   UC_ARM_REG_R6, UC_ARM_REG_SP,
                                   UC_ARM_REG_PC, UC_ARM_REG_LR)
    rng = random.Random(57)
    pool = sorted(rng.sample(range(0x3F, 0x380), 150))
    # un pool de sorts reduit : le tirage ne rend que ceux de la table
    pool_s = sorted(rng.sample(sorts(), 20))
    bl = blocs(pool_s + pool)
    # blocs 2 et 3 : aucun registre vivant apres le bloc 2 ; apres le bloc 3,
    # r0, r2, r3, r4 et ip (r12) le sont (r1 est reecrit juste apres).
    _equivalence_bloc(B2, ORIGINE2, bl[1][2][:len(bloc2_compact())] +
                      bytes(len(ORIGINE2) - len(bloc2_compact())),
                      B2_SUITE, (), essais, rng)
    b3c = bl[2][2][:TIRAGES - B3]
    _equivalence_bloc(B3, ORIGINE3, b3c + bytes(len(ORIGINE3) - len(b3c)),
                      B3_SUITE, (0, 2, 3, 4, 12, 13), essais, rng)

    COPIE, FICHE, PILE = 0x02300000, 0x02310000, 0x023F0000
    BASE, FICHES_ACT = 0x02108E10, 0x02320000
    couts = {a: rng.choice([0, 1, 2, 3, 5, 8, 16, 24, 28, 90, 255])
             for a in range(0x400)}
    table, table_s = set(pool), set(pool_s)

    def lance(apres, copie, s, acts, masque, masque_t, tirages):
        mu = _uc()
        if apres:
            for adr, _a, code in bl:
                mu.mem_write(adr, code)
        else:
            mu.mem_write(BLOC, ORIGINE)
        mu.mem_write(COPIE, copie)
        mu.mem_write(FICHE + 0x0C, struct.pack("<I", s))
        mu.mem_write(FICHE + 0x32, struct.pack("<6H", *acts))
        mu.mem_write(COPIE + BTL_MASQUE, bytes([masque, masque_t]))
        for a in range(0x400):
            mu.mem_write(FICHES_ACT + 60 * a + 8, bytes([couts[a]]))
        mu.reg_write(UC_ARM_REG_R4, COPIE)
        mu.reg_write(UC_ARM_REG_R6, FICHE)
        mu.reg_write(UC_ARM_REG_R0, COPIE + 0x18)
        mu.reg_write(UC_ARM_REG_R1, FICHE + 0x32)
        mu.reg_write(UC_ARM_REG_R2, 12)
        mu.reg_write(UC_ARM_REG_SP, PILE)
        file_t = list(tirages)

        def retour(uc):
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

        def crochet(uc, adr, taille, _):
            if adr == MEMCPY:
                r0, r1, r2 = (uc.reg_read(r) for r in
                              (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
                uc.mem_write(r0, bytes(uc.mem_read(r1, r2)))
                retour(uc)
            elif adr == RAND_BELOW:
                n = uc.reg_read(UC_ARM_REG_R0)
                k = file_t.pop(0) % n
                uc.reg_write(UC_ARM_REG_R0, k)
                retour(uc)
            elif adr == BASE_ACTIONS:
                uc.reg_write(UC_ARM_REG_R0, BASE)
                retour(uc)
            elif adr == ACTION:
                assert uc.reg_read(UC_ARM_REG_R0) == BASE
                a = uc.reg_read(UC_ARM_REG_R1)
                uc.reg_write(UC_ARM_REG_R0, FICHES_ACT + 60 * a)
                retour(uc)
        mu.hook_add(UC_HOOK_CODE, crochet)
        mu.emu_start(BLOC, SUITE, count=200000)
        assert mu.reg_read(UC_ARM_REG_SP) == PILE
        assert mu.reg_read(UC_ARM_REG_R4) == COPIE
        assert mu.reg_read(UC_ARM_REG_R6) == FICHE
        return bytes(mu.mem_read(COPIE, 0x84))

    for e in range(essais):
        copie = bytearray(rng.getrandbits(8) for _ in range(0x84))
        pm0 = rng.choice([0, 3, 12, 40, 200, 255, rng.randrange(0x10000)])
        struct.pack_into("<H", copie, 0x5E, pm0)
        copie = bytes(copie)
        s = rng.getrandbits(32)
        acts = [rng.randrange(0x400) for _ in range(6)]
        ms = rng.choice([0, 0x3F, rng.randrange(64)])
        mt = rng.choice([0, 0x3F, rng.randrange(64)])
        # tirages : pour les sorts, parfois le trou 0x1D ; pour les
        # techniques, des identifiants hors table avant d'en trouver un
        tirages = [rng.randrange(0x400) for _ in range(20000)]
        ref = lance(False, copie, s, acts, 0, 0, [])
        neuf = lance(True, copie, s, acts, ms, mt, tirages)
        for o in range(0x84):
            if not (0x18 <= o < 0x24 or o in (0x5E, 0x5F, 0x82, 0x83)):
                assert neuf[o] == ref[o], (e, hex(o))
        file_t = list(tirages)
        attendu, cmax = [], 0
        for k in range(6):
            if mt >> k & 1:
                while True:
                    a = file_t.pop(0) % BORNE_TECH
                    if a >= BORNE_SORTS and a in table:
                        break
            elif ms >> k & 1:
                while True:
                    a = file_t.pop(0) % BORNE_SORTS
                    if a in table_s:
                        break
            else:
                attendu.append(acts[k])
                continue
            attendu.append(a)
            if couts[a] != 255:
                cmax = max(cmax, couts[a])
        tires = list(struct.unpack_from("<6H", neuf, 0x18))
        assert tires == attendu, (e, tires, attendu)
        pm = struct.unpack_from("<H", neuf, 0x5E)[0]
        assert pm == max(pm0, min(255, FACTEUR_PM * cmax)), (e, pm, pm0, cmax)
        assert list(struct.unpack_from("<6H", ref, 0x18)) == acts

    # SECOND SITE : une table de N copies de combat, chacune tiree selon ses
    # masques, puis retour par 0x02012FF4 avec les registres du site.
    from unicorn.arm_const import UC_ARM_REG_R5, UC_ARM_REG_R7
    BASE_T, FICHES_T = 0x02330000, 0x02340000
    for e in range(essais // 5):
        n = rng.randrange(0, 7)
        fiches = []
        for k in range(n):
            f = bytearray(rng.getrandbits(8) for _ in range(0x84))
            f[0x82] = rng.choice([0, 0x3F, rng.randrange(64)])
            f[0x83] = rng.choice([0, rng.randrange(64)])
            fiches.append(bytes(f))
        mu = _uc()
        for adr, _a, code in bl:
            mu.mem_write(adr, code)
        mu.mem_write(BASE_T + 0x400, struct.pack(
            "<II", (rng.getrandbits(20) << 12) | n, FICHES_T))
        for k, f in enumerate(fiches):
            mu.mem_write(FICHES_T + 0x84 * k, f)
        for a in range(0x400):
            mu.mem_write(FICHES_ACT + 60 * a + 8, bytes([couts[a]]))
        mu.reg_write(UC_ARM_REG_R5, BASE_T)
        mu.reg_write(UC_ARM_REG_R4, 0x1234)
        mu.reg_write(UC_ARM_REG_R6, 0x5678)
        mu.reg_write(UC_ARM_REG_R7, 0x9ABC)
        mu.reg_write(UC_ARM_REG_SP, PILE)
        mu.reg_write(UC_ARM_REG_LR, 0)
        tirages = [rng.randrange(0x400) for _ in range(40000)]
        file_t = list(tirages)
        vu = []

        def crochet2(uc, adr, taille, _):
            if adr == MEMCPY:
                r0, r1, r2 = (uc.reg_read(r) for r in
                              (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
                assert r0 == r1 and r2 == 12
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            elif adr == RAND_BELOW:
                uc.reg_write(UC_ARM_REG_R0, file_t.pop(0) % uc.reg_read(UC_ARM_REG_R0))
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            elif adr == BASE_ACTIONS:
                uc.reg_write(UC_ARM_REG_R0, BASE)
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            elif adr == ACTION:
                uc.reg_write(UC_ARM_REG_R0, FICHES_ACT + 60 * uc.reg_read(UC_ARM_REG_R1))
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            elif adr == APRES_SITE2:
                vu.append((uc.reg_read(UC_ARM_REG_LR), uc.reg_read(UC_ARM_REG_SP),
                           [uc.reg_read(r) for r in (UC_ARM_REG_R4, UC_ARM_REG_R5,
                                                     UC_ARM_REG_R6, UC_ARM_REG_R7)]))
                uc.emu_stop()
        mu.hook_add(UC_HOOK_CODE, crochet2)
        mu.emu_start(SITE2, SITE2 + 4, count=400000)
        assert vu and vu[0][0] == SITE2 + 4 and vu[0][1] == PILE, vu
        assert vu[0][2] == [0x1234, BASE_T, 0x5678, 0x9ABC], vu
        # rejouer les tirages
        for k, f in enumerate(fiches):
            neuf = bytes(mu.mem_read(FICHES_T + 0x84 * k, 0x84))
            ms, mt = f[0x82], f[0x83]
            acts = struct.unpack_from("<6H", f, 0x18)
            cmax = 0
            # comparaison : hors actions et PM, rien ne bouge ; les
            # emplacements non marques gardent leur action ; les marques
            # portent un sort ou une technique de la table
            for o in range(0x84):
                if not (0x18 <= o < 0x24 or o in (0x5E, 0x5F)):
                    assert neuf[o] == f[o], (e, k, hex(o))
            tires = struct.unpack_from("<6H", neuf, 0x18)
            for j in range(6):
                if mt >> j & 1:
                    assert tires[j] in table, (e, k, j, tires[j])
                elif ms >> j & 1:
                    assert tires[j] in table_s, (e, k, j, tires[j])
                else:
                    assert tires[j] == acts[j]
                if (ms | mt) >> j & 1 and couts[tires[j]] != 255:
                    cmax = max(cmax, couts[tires[j]])
            pm0 = struct.unpack_from("<H", f, 0x5E)[0]
            assert struct.unpack_from("<H", neuf, 0x5E)[0] == max(
                pm0, min(255, FACTEUR_PM * cmax)), (e, k)
    return essais


if __name__ == "__main__":
    import ndspy.rom
    if len(sys.argv) == 2 and sys.argv[1] == "--emuler":
        print("equivalence : %d essais, ok" % verifier_equivalence())
        sys.exit(0)
    if len(sys.argv) < 4:
        sys.exit("usage: patch_actions.py <rom.nds> <sortie.nds> "
                 "<sorts:-|remplacer|ajouter|tous> [techniques:-|remplacer|"
                 "ajouter|tous] [graine]\n       patch_actions.py --emuler")
    r = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    arg = lambda i: (None if len(sys.argv) <= i or sys.argv[i] == "-"
                     else sys.argv[i])
    patcher(r, arg(3), arg(4), arg(5) or 0)
    print("relu : sorts %s, techniques %s" % verifier(r))
    r.saveToFile(sys.argv[2])
    # comme randomizer.py : le bourrage 0xFF de fin de cartouche est rendu
    manque = os.path.getsize(sys.argv[1]) - os.path.getsize(sys.argv[2])
    if manque > 0:
        with open(sys.argv[2], "ab") as f:
            f.write(bytes([0xFF]) * manque)
    print("ecrit :", sys.argv[2], "(%d o)" % os.path.getsize(sys.argv[2]))
