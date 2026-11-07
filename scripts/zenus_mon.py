"""Zenus, boss a part : son modele de combat sous le code `z060c`, celui de
l'espece 900 (index 437 de mon_btldata, 32 000 PV, sans nom), le
« Sacksquatch » inutilise du jeu. Aucune table de rencontres ni de combat
scripte ne cite l'espece 900, et `z060c` n'est utilise que par elle : Zenus
n'y remplace personne (ZER-116, 30/10).

Le .mon est bati sur le gabarit d'Aquila (b300a.mon) :
    z060c.bact                    celui d'Aquila
    z060c.cchr (LZ10, NARC)       run, stand, z060c.bcfg (Aquila), z060c.nsbmd
    z060c.cmot (LZ10, NARC)       attack1a, damage, death, magic, z060c.bcfg (Aquila)
z060c.nsbmd = s060.nsbmd (statue doree des cinematiques, lue dans la ROM) dont
les deux textures 128x128 en 16 couleurs recoivent le repeint
(data/zenus/tex_*.bin) EN PLACE ; les animations = data/zenus/anims/.

Usage : python scripts/zenus_mon.py <rom entree> <rom sortie>
        La sortie garde la taille de l'entree (bourrage 0xFF) : les
        sauvegardes et savestates du joueur restent valables.
"""
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ndspy.fnt
import ndspy.lz10
import ndspy.narc
import ndspy.rom

import gp2_ecrire
import nitro3d as N
import patch_kits_animes as K

CODE = "z060c"
INDEX = 437                      # espece 900 dans mon_btldata
MON_BTLDATA = "data/prm/mon_btldata.nat"
ANIMS_CMOT = ("attack1a", "damage", "death", "magic", "skill1", "skill2")
# Les animations (data/zenus/anims, choix du joueur du 06/11 : attaque A, marche
# combinee A, sorts / 2e competence / coup recu / mort imites du Titan de Heroes V)


def donnee(nom):
    """Un fichier de data/zenus/ : a cote des scripts, ou dans l'exe (PyInstaller)."""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "data", "zenus", nom), "rb") as f:
        return f.read()


def noms_narc(n):
    out = []

    def parcourir(f, p=""):
        for x in f.files:
            out.append(p + x)
        for x, s in f.folders:
            parcourir(s, p + x + "/")
    parcourir(n.filenames)
    return out
# Le mouvement que joue Zenus (op03 [7, ...]) dans le cas de chaque action ; corps_cas les
# ramene tous a attack1a (mouvements universels). Sorts : la capacite speciale du Titan
# (magic) ; competences : son attaque a distance (magic2). L'attaque simple (0x01) garde
# le bloc op10 d'Aquila, attack1a.
# v13 (joueur, 06/11 au soir) : le sort bleu et Megaleration reprennent l'ancien sort (magic) ;
# skill1 = capacite speciale du Titan, skill2 = son attaque a distance.
MOUVEMENTS = {0x21F: b"skill1", 0x39E: b"skill1", 0x386: b"skill1",
              0x3AE: b"magic", 0x2C: b"magic",
              0x219: b"skill2", 0x23F: b"skill2", 0xBD: b"skill2", 0x1F6: b"skill2",
              # 06/11 soir (le joueur juge) : Colere des dieux et Desastre = capacite speciale du Titan (il leve les bras,
              # invoque) ; Vague de panique et Hypnoeil = son attaque a distance, comme Perturbonde et le charme
              # (une onde, un regard) ; Megakill = l'ancien sort, comme le sort bleu.
              0x22C: b"skill1", 0x22A: b"skill1", 0x230: b"skill2", 0x233: b"skill2", 0x1A: b"magic"}


def narc_lu(data):
    if data[:4] != b"NARC":
        data = ndspy.lz10.decompress(data)
    n = ndspy.narc.NARC(data)
    return dict(zip(noms_narc(n), n.files))


def narc_ecrit(fichiers):
    """NARC a une racine, noms tries comme ceux du jeu."""
    noms = sorted(fichiers)
    racine = ndspy.fnt.Folder(files=noms)
    out = bytearray(ndspy.narc.NARC.fromFilesAndNames(
        [fichiers[n] for n in noms], racine).save())
    # EN-TETE DU JEU : ndspy ecrit `ff fe 01 00`, le jeu `fe ff 00 01` (BOM
    # 0xFFFE, version 1.0). Avec celui de ndspy, ouvrir z060c dans la
    # visionneuse GELAIT, meme pour le .mon d'origine reecrit (30/10).
    out[4:8] = b"\xfe\xff\x00\x01"
    return bytes(out)


S060 = "data/chara_sub/s060.chr"


def s060(rom):
    """Les membres de la statue doree du jeu (s060.chr), lus dans la ROM."""
    return narc_lu(bytes(rom.getFileByName(S060)))


def nsbmd_repeint(rom):
    d = bytearray(s060(rom)["s060.nsbmd"])
    t0 = N.blocs(bytes(d), b"BMD0")[b"TEX0"]
    texs, pals, ctx = N.textures(bytes(d), t0)
    for t in texs:
        assert t["format"] == 3 and not t["transparent0"], t
        brut = donnee("tex_%s.bin" % t["nom"])
        n = t["largeur"] * t["hauteur"] // 2
        assert len(brut) == n + 32, (t["nom"], len(brut))
        a = ctx["tex_data"] + t["offset"]
        d[a:a + n] = brut[:n]
        p = ctx["pal_data"] + pals[t["nom"] + "_pl"]
        d[p:p + 32] = brut[n:]
    return bytes(d)


def agrandir(nsbmd, k):
    """Le modele entier x k : MDL0, info du modele +0x1C pos_scale (fx32) et
    +0x20 son inverse, +0x38/+0x3C l'echelle de la boite englobante et son
    inverse (31/10). Nokturnus : boite 52 x 40 de haut ; Zenus (s060) 32 x 30."""
    if k == 1.0:
        return nsbmd
    d = bytearray(nsbmd)
    m0 = N.blocs(bytes(d), b"BMD0")[b"MDL0"]
    for _nom, e in N.dico(bytes(d), m0 + 8):
        mod = m0 + N.u32(e, 0)
        for o, f in ((0x1C, k), (0x20, 1 / k), (0x38, k), (0x3C, 1 / k)):
            v = struct.unpack_from("<i", d, mod + o)[0]
            struct.pack_into("<i", d, mod + o, round(v * f))
    return bytes(d)


def nsbca_echelle(d, k):
    """L'animation avec une echelle constante k sur son noeud RACINE : tout le modele
    grandit depuis son origine, aux pieds (joueur, 05/11 : la taille de Nokturnus ;
    `agrandir` n'y change rien en combat, research §113.4). Le corps de la racine,
    recopie a la fin du fichier avec les trois paires (s, 1/s), remplace l'ancien dans la
    table des noeuds ; les pistes T et R ne bougent pas : leurs offsets sont absolus.
    NNS : 1 identite, 2 T nul, 4 T de base, 8/0x10/0x20 T constants, 0x40 R nul, 0x80 R de
    base, 0x100 R constant, 0x200 S nul, 0x800/0x1000/0x2000 S constants."""
    if k == 1.0:
        return d
    j = d.find(b"J\0AC")
    assert d[:4] == b"BCA0" and j > 0
    p = j + struct.unpack_from("<H", d, j + 0x14)[0]
    info = struct.unpack_from("<I", d, p)[0]
    fl = info & 0xFFFFFF
    assert fl & 0x400 == 0 and (fl & 1 or fl & 0x200), "racine deja mise a l'echelle : %#x" % fl
    if fl & 1:
        corps, fl = b"", 2 | 0x40
    else:
        n = 0
        if not fl & (2 | 4):
            n += sum(4 if fl & c else 8 for c in (8, 0x10, 0x20))
        if not fl & (0x40 | 0x80):
            n += 4 if fl & 0x100 else 8
        corps = d[p + 4:p + 4 + n]
        fl &= ~0x200
    fl |= 0x800 | 0x1000 | 0x2000
    s = round(k * 4096)
    inv = round(4096 / k)
    out = bytearray(d)
    out += bytes(-len(out) % 4)
    neuf = len(out) - j
    assert neuf < 0x10000
    out += struct.pack("<I", fl | (info & 0xFF000000)) + corps + struct.pack("<ii", s, inv) * 3
    struct.pack_into("<H", out, j + 0x14, neuf)
    bloc = struct.unpack_from("<I", out, 0x10)[0]    # JNT0 : le seul bloc
    assert out[bloc:bloc + 4] == b"JNT0"
    struct.pack_into("<I", out, bloc + 4, len(out) - bloc)
    struct.pack_into("<I", out, 8, len(out))
    return bytes(out)


# Echelle en combat (joueur, 31/10 et 05/11 : « regarde la taille de Nokturnus ») :
# mesuree a l'image, Nokturnus fait 1,45 fois Zenus debout dans le meme combat.
# MESURE (06/11, banc gA22/gA23) : cette echelle, posee dans CHAQUE animation, fait GONFLER Zenus ~10 images quand une
# animation d'action finit et que le jeu repasse en garde (+16 % de pixels a 1,4, +4 % a 1,0) : le « petit bond » vu
# par le joueur apres l'attaque simple et le coup recu.
# 1,2 depuis le 06/11 (joueur, v23 : « parfait pour la taille ») : gonflement deux fois plus petit qu'a 1,4.
ECHELLE_COMBAT = float(os.environ.get("ECHELLE_COMBAT", "1.2"))


# Le kit de Zenus (joueur, 31/10 : « des techniques deja presentes dans le
# jeu, ou qui correspondent au personnage ; 2 ou 3 attaques par tour ; la
# pluie benefique pour un soin complet une fois par combat »). Techniques
# de boss, toutes a 0 PM ; Soins complets (version monstre, 24 PM) avec
# l'ANIMATION de la Pluie benefique (0xBC), dans son seul .bact. Zenus n'a
# que 24 PM : un soin par combat. Messages de combat (actmsg fr) :
#   0x21F « declenche un eclair apocalyptique ! »   (boss de grotte, 338)
#   0x22D « ecrase X comme un insecte ! »           (511, Rhapthorne)
#   0x219 « vomit un nuage de lumiere eblouissante » (758)
#   0x1F6 le CHARME (patch_charme : « //Zenus// Obeis-moi, tu es ma
#         creation ! »), a la place de Souffle obscur 0x217 (joueur, 31/10),
#         avec l'animation des yeux qui brillent (0x220)
from patch_charme import ACTION as CHARME, NEANT, SOIN, TABLE, BLEU, DECUPLO
# la fiche de l'espece garde six actions ; la decision vient de la table (patch_charme)
KIT = (0x01, 0x219, 0x21F, 0x23F, 0xBD, BLEU)    # sans charme ni soin : jamais hors de la table
ASPECT_SOIN = 0xBC
# le cas du .bact pris chez une autre action (vraie animation du jeu) ; le
# NEANT (patch_charme) n'est pas dans le kit : la greffe le substitue sous
# 2 000 PV, il a son cas (les yeux qui brillent, comme le charme)
# NEANT : pas l'attaque simple (joueur, 05/11) ; Fatal (0x18), le sort de mort
ASPECT_NEANT = int(os.environ.get("NEANT_ASPECT", "0x18"), 0)
# CHARME : le squelette de Fatal, a cible unique, avec l'effet de la Confusion du jeu (joueur, 05/11 : il n'aime
# pas que le charme reprenne l'animation du neant). Le cas de Confusion (0x33) lui-meme vise un groupe de monstres :
# la camera montrait un mur vide (mesure a froid, 05/11), et il pese 49 commandes contre 37.
ASPECTS = {SOIN: ASPECT_SOIN, CHARME: ASPECT_NEANT, NEANT: ASPECT_NEANT, BLEU: DECUPLO}
HORS_KIT = tuple(sorted({a for a in TABLE if a not in KIT})) + (NEANT,)
SANS_CAS = ()
# BANC SEULEMENT : KIT_ESSAI=0x30,0x30,... remplace le kit (6 actions) ; une
# action sans cas donneur (un sort) garde la mise en scene generique
KIT_ESSAI = os.environ.get("KIT_ESSAI")
if KIT_ESSAI:
    KIT = tuple(int(x, 0) for x in KIT_ESSAI.split(","))
    assert len(KIT) == 6


# LE NEANT PIMPE (joueur, 05/11) : le sort de mort du jeu joue SON effet em0500 ; celui de Zenus
# joue une copie (zn0500), rouge sang et blanche au lieu de violette, flammes plus hautes. Le sort
# du jeu ne change pas. EFFET_ECHELLE : op75 [0, echelle, 0.3] du cas (1.2 d'origine).
EFFET_JEU, EFFET_ZENUS, EFFET_CHARME = "em0500", "zn0500", "em1020"
# Le sort bleu : le cas de Decuplo, son effet em1200 copie en zb1200, rouge et bleu echanges (joueur, 05/11).
EFFET_DECUPLO, EFFET_BLEU = "em1200", "zb1200"
ACTION_CONFUSION = 0x33
EFFET_ECHELLE = float(os.environ.get("NEANT_ECHELLE", "2.0"))


def cas_neant(dbd, cas, effet=EFFET_ZENUS, echelle=EFFET_ECHELLE, jeu=EFFET_JEU):
    """Le .bact donneur avec le chemin de l'effet renomme (meme longueur), et le cas avec les
    flammes agrandies (echelle None : inchangees)."""
    neuf = dbd.replace(("effect/%s.chr" % jeu).encode(), ("effect/%s.chr" % effet).encode())
    assert neuf != dbd
    f = None if echelle is None else struct.unpack("<I", struct.pack("<f", echelle))[0]
    out = []
    for o, op, args, t in cas:
        if op == 0x75 and echelle is not None:
            args = [args[0], f] + list(args[2:])
        out.append((o, op, args, t))
    return neuf, out


def _sang(c):
    """BGR555 violet -> rouge sang, le haut de l'echelle vers le blanc ; le blanc reste."""
    r, g, b = c & 31, (c >> 5) & 31, (c >> 10) & 31
    if g >= min(r, b) - 1 and max(r, b) - g < 3:
        return c
    v = max(r, b) / 31
    nr = min(31, round(31 * min(1.0, v * 1.5)))
    ng = round(31 * v ** 3)
    nb = round(31 * v ** 4)
    return (c & 0x8000) | nr | (ng << 5) | (nb << 10)


def _bleu(c):
    """BGR555 : rouge et bleu echanges (l'orange devient azur, le jaune cyan) ; le blanc et les gris restent."""
    r, g, b = c & 31, (c >> 5) & 31, (c >> 10) & 31
    return (c & 0x8000) | b | (g << 5) | (r << 10)


def effet_zenus(rom, effet=EFFET_ZENUS, couleur=None, jeu=EFFET_JEU):
    """Le fichier data/effect/<effet>.chr : celui du jeu aux noms changes et aux palettes refaites."""
    couleur = couleur or _sang
    a = narc_lu(bytes(rom.getFileByName("data/effect/%s.chr" % jeu)))
    v = bytearray(a[jeu + ".nsbmd"])
    t0 = N.blocs(bytes(v), b"BMD0")[b"TEX0"]
    _t, _p, ctx = N.textures(bytes(v), t0)
    for o in range(ctx["pal_data"], len(v) - 1, 2):
        struct.pack_into("<H", v, o, couleur(struct.unpack_from("<H", v, o)[0]))
    a[jeu + ".nsbmd"] = bytes(v)
    return narc_ecrit({k.replace(jeu, effet): d for k, d in a.items()})


def bact_zenus(bact, van=None):
    """Le .bact d'Aquila + le VRAI cas de chaque technique du kit (copie
    d'un donneur du jeu, patch_animations.corps_cas), Soins complets avec le
    cas de la Pluie benefique, le charme avec les yeux de 0x220 (ASPECTS).
    `van` : la ROM d'origine (les donneurs). Rend (octets, [(action, donneur)])."""
    import patch_animations as A
    from patch_kits_animes import construire_modele, cas_du_bact
    if van is None:
        from rom_vanilla import chemin_vanilla
        van = ndspy.rom.NintendoDSRom.fromFile(chemin_vanilla())
    don, perso = A.cas_donneurs(van), A.cas_personnages(van)
    deja = cas_du_bact(bact)
    reels, faits = [], []
    for a in KIT + HORS_KIT:
        source = ASPECTS.get(a, a)
        if a == 0x01 or (a in deja and a not in ASPECTS):
            continue
        c = A.meilleur_cas(don.get(source, [])) or A.meilleur_cas(perso.get(source, []))
        if not c and (KIT_ESSAI or a in SANS_CAS):
            continue
        if not c:
            raise SystemExit("Zenus : pas de cas pour l'action %#x" % source)
        nom, dbd, cas = c
        if a == NEANT:
            dbd, cas = cas_neant(dbd, cas)
        elif a == BLEU:
            dbd, cas = cas_neant(dbd, cas, EFFET_BLEU, None, EFFET_DECUPLO)
        elif a == CHARME:
            dbd, cas = cas_neant(dbd, cas, EFFET_CHARME, 1.2)
            # la seconde commande de l'effet de Confusion, juste apres op75
            _n, _d, conf = A.meilleur_cas(don.get(ACTION_CONFUSION, [])) or A.meilleur_cas(perso[ACTION_CONFUSION])
            k = next(i for i, c in enumerate(cas) if c[1] == 0x75)
            cas = cas[:k + 1] + [next(c for c in conf if c[1] == 0x76)] + cas[k + 1:]
        reels.append((a, dbd, cas))
        faits.append((a, nom))
    neuf, _n = construire_modele(bact, reels)
    return pas_sonores(bloc_attaque(mouvements(neuf, MOUVEMENTS))), faits


# LE SON DES PAS (joueur, 06/11 : « le seul son a rajouter »). op46 [n] joue un bruitage de combat (overlay 0
# 0x0216BAC8 : n en u16) ; 25 est celui que le jeu pose au depart de l'avance des golems (golem, golem d'or, de
# pierre, geolem), des dragons, de Mortamor. Un son par appui de pied : bassin au plus bas aux images 10 et 21 de la
# marche de 22 images (final.MARCHE_IMAGES). +4 commandes (op1a [7, t] puis op46 [n], deux fois) apres l'op05 du
# bloc d'attaque. ZENUS_PAS_SON=0 : pas de son.
PAS_SON = int(os.environ.get("ZENUS_PAS_SON", "25"))
PAS_IMAGES = tuple(int(x) for x in os.environ.get("ZENUS_PAS", "10,21").split(","))


def _commande(op, args):
    """(op, [(type, valeur)]) -> octets d'une commande .bact (u16 op, u8 n, u8 types, arguments)."""
    assert len(args) <= 4
    ty = 0
    for i, (t, _v) in enumerate(args):
        ty |= t << (2 * i)
    out = struct.pack("<HBB", op, len(args), ty)
    for t, v in args:
        out += struct.pack("<f" if t == 2 else "<i", v)
    return out


def pas_sonores(bd, son=PAS_SON, images=PAS_IMAGES):
    """Le .bact avec, apres l'op05 du bloc op10, une attente et un op46 [son] par appui de pied."""
    import patch_animations as A
    if not son:
        return bd
    h, cc = A.lire_bact(bd)
    k5 = next(k for k, c in enumerate(cc) if c[1] == 0x10)
    k5 = next(k for k in range(k5, len(cc)) if cc[k][1] == 5)
    neuves = b"".join(_commande(0x1A, [(1, 7), (2, f / _N)]) + _commande(0x46, [(1, son)]) for f in images)
    fin5 = cc[k5][0] + cc[k5][3]
    fin = cc[-1][0] + cc[-1][3]
    corps = bd[0x10:fin5] + neuves + bd[fin5:fin]
    out = bytearray(bd[:0x10]) + corps
    out += b"\xff" * (-len(out) % 16)
    debut = len(out)
    out += bd[h[1]:h[1] + h[2]]
    out += b"\xff" * (-len(out) % 16)
    struct.pack_into("<4I", out, 0, h[0] + 2 * len(images), debut, h[2], h[3])
    h2, c2 = A.lire_bact(bytes(out))
    ops = [c[1] for c in c2]
    assert ops == [c[1] for c in cc[:k5 + 1]] + [0x1A, 0x46] * len(images) + [c[1] for c in cc[k5 + 1:]]
    return bytes(out)


# L'attaque simple (bloc op10, herite d'Aquila) : op05 [debut, fin, distance] = l'avance vers la cible,
# op06 [debut, fin] = le retour, en secondes (overlay 0 0x02169E80 / 0x02169FA4 : x 4096 ; un entier
# = des millisecondes). ZENUS_OP05="a,b,d" / ZENUS_OP06="a,b" les changent (meme nombre de commandes).
# MESURE (banc du 06/11) : ces temps sont des FRACTIONS de l'animation du lanceur (0 debut, 1 fin), pas des secondes.
# v20 : calees sur l'attack1a marchee de final.py (MARCHE_IMAGES de marche, puis le poing de 15 images, impact a
# sa 7e) : avance pendant la marche, coup a l'impact, retour 4 images apres le coup sur 3,5 images (Aquila : coup a
# 0,57, retour 0,76-0,91 de 23 images). Avant : Aquila, [0.26, 0.39, 0.2] / 0.57 / [0.76, 0.91].
_V20 = True
_W = int(os.environ.get("MARCHE_IMAGES", "22"))
_N = _W + 15 + int(os.environ.get("ATTAQUE_TENUE", "0"))   # final.ATTAQUE_TENUE : garde tenue apres le poing
OP05 = os.environ.get("ZENUS_OP05", "0,%.3f,0.2" % (_W / _N) if _V20 else "")
OP06 = os.environ.get("ZENUS_OP06", "%.3f,%.3f" % ((_W + 11) / _N, (_W + 14.5) / _N) if _V20 else "")
OP1A = os.environ.get("ZENUS_OP1A", "%.3f" % ((_W + 7) / _N) if _V20 else "")   # la 1re attente op1a [7, t] (le coup)


def bloc_attaque(bd, op05=OP05, op06=OP06, op1a=OP1A):
    import patch_animations as A
    if not op05 and not op06 and not op1a:
        return bd
    _h, cc = A.lire_bact(bd)
    out = bytearray(bd)
    dedans = False
    for p, op, args, _t in cc:
        if op == 0x10:
            dedans = True
        elif op in (1, 2, 0x11):
            dedans = False
        if not dedans or op not in (5, 6, 0x1A):
            continue
        if op == 0x1A:
            if len(args) != 2 or not op1a:
                continue
            neuf, op1a = op1a, None             # la premiere seulement
            _o, n, ty = struct.unpack_from("<HBB", bd, p)
            assert (ty >> 2) & 3 == 2, "op1a : attente non flottante"
            struct.pack_into("<f", out, p + 4 + 4, float(neuf))
            continue
        neuf = op05 if op == 5 else op06
        if not neuf:
            continue
        vals = [float(x) for x in neuf.split(",")]
        assert len(vals) == len(args), (op, args, vals)
        _o, n, ty = struct.unpack_from("<HBB", bd, p)
        assert all((ty >> (2 * i)) & 3 == 2 for i in range(n)), "op%02x : arguments non flottants" % op
        for i, v in enumerate(vals):
            struct.pack_into("<f", out, p + 4 + (4 if n > 4 else 0) + 4 * i, v)
    return bytes(out)


def mouvements(bd, table):
    """Le .bact ou, dans le cas de chaque action de `table`, op03 [7, ...] joue le
    mouvement donne (chaine ajoutee au pool) ; meme nombre de commandes."""
    import patch_animations as A
    h, cc = A.lire_bact(bd)
    pool = bytearray(bd[h[1]:h[1] + h[2]])
    nch, index = h[3], {}
    out = bytearray(bd[:cc[-1][0] + cc[-1][3]])
    cas, vus = None, set()
    for p, op, args, t in cc:
        if op == 1:
            cas = [a for a in args if a in table]
        elif op in (2, 0x10):
            cas = None
        if op == A.MOUVEMENT_OP and args and args[0] == A.LANCEUR and cas:
            s = table[cas[0]]
            if s not in index:
                index[s] = len(pool)
                pool.extend(s + b"\0")
                nch += 1
            struct.pack_into("<I", out, p + 4 + (4 if len(args) > 4 else 0) + 4, index[s])
            vus.update(cas)
    manque = {a for a in set(table) - vus if a in KIT + HORS_KIT}   # ZENUS_TABLE (banc) : seulement le kit present
    if manque:
        raise SystemExit("Zenus : pas de mouvement du lanceur dans les cas %s" % sorted(map(hex, manque)))
    out += b"\xff" * (-len(out) % 16)
    debut = len(out)
    out += pool
    out += b"\xff" * (-len(out) % 16)
    struct.pack_into("<4I", out, 0, h[0], debut, len(pool), nch)
    h2, c2 = A.lire_bact(bytes(out))
    assert h2[0] == h[0] and [c[1] for c in c2] == [c[1] for c in cc]
    return bytes(out)


FONDUS = dict((k, float(v)) for k, v in (x.split("=") for x in os.environ.get("ZENUS_FONDU", "").split(",") if x))


def bcfg(d, longueurs):
    """Le .bcfg (script Nitro) avec une entree 0x66 [nom, debut, fin, f] par animation de
    `longueurs` ({nom: images}), plages consecutives comme dans les fichiers du jeu (fin -
    debut + 1 = images) ; f gardee pour un nom deja la, prise a magic (ou 0.2) sinon."""
    import nitro_script as NS
    _h, ins = NS.lire(d)
    fl = lambda x: struct.unpack("<I", struct.pack("<f", float(x)))[0]
    vf = lambda v: struct.unpack("<f", struct.pack("<I", v))[0]
    k66 = [k for k, (op, _p) in enumerate(ins) if op == 0x66]
    anciens = {ins[k][1][0][1]: ins[k][1] for k in k66}
    defaut = anciens.get(b"magic", [None, None, None, (NS.ENTIER, fl(0.2))])[3]
    neufs, debut = [], 1
    force = dict((k, int(v)) for k, v in (x.split("=") for x in os.environ.get("ZENUS_LONGUEURS", "").split(",") if x))
    plages = dict((k, int(v)) for k, v in (x.split("=") for x in os.environ.get("ZENUS_PLAGES", "").split(",") if x))
    sans = set(os.environ.get("ZENUS_BCFG_SANS", "").split(",")) - {""}
    for nom, n in longueurs.items():
        if nom in sans:                        # BANC : ZENUS_BCFG_SANS=skill1,skill2
            continue
        n = force.get(nom, n)                  # BANC : ZENUS_LONGUEURS=attack1a=23
        f = anciens.get(nom.encode(), [None] * 3 + [defaut])[3]
        if nom in FONDUS:                      # BANC. 4e champ = VITESSE de lecture (images par tic a 60/s) ; 0 FIGE l'action
            f = (NS.FLOTTANT, fl(FONDUS[nom]))
        d0 = plages.get(nom, debut)            # BANC : ZENUS_PLAGES=attack1a=23
        # FLOTTANT (type 2), comme le jeu (octet de types 0xA8). Jusqu'a la v18, ENTIER (0x94) : le jeu lisait
        # ~1e9 images, et l'avance de l'attaque se faisait d'un coup (banc du 06/11, ZER-116).
        neufs.append((0x66, [(NS.CHAINE, nom.encode()), (NS.FLOTTANT, fl(d0)),
                             (NS.FLOTTANT, fl(d0 + n - 1)), f]))
        debut = max(debut, d0) + n
    ins = ins[:k66[0]] + neufs + ins[k66[-1] + 1:]
    assert ins[0][0] == 0x64
    ins[0] = (0x64, [(NS.ENTIER, len(neufs))])
    return NS.ecrire(ins)


def images(nsbca):
    j = nsbca.find(b"J\0AC")
    return struct.unpack_from("<H", nsbca, j + 4)[0]


def mon_zenus(aquila, rom, van=None):
    a = narc_lu(aquila)
    cchr_a = narc_lu(a["b300a.cchr"])
    cmot_a = narc_lu(a["b300a.cmot"])
    anim = lambda nom: nsbca_echelle(donnee("anims/%s.nsbca" % nom), ECHELLE_COMBAT)
    cchr = {"run.nsbca": anim("run"),
            "stand.nsbca": anim("stand"),      # il respire, plus de pose figee
            CODE + ".nsbmd": nsbmd_repeint(rom)}
    cmot_noms = ANIMS_CMOT
    cmot = {nom + ".nsbca": anim(nom) for nom in cmot_noms}
    if os.environ.get("ZENUS_BCFG") == "aquila":   # BANC : le .bcfg d'Aquila
        cchr[CODE + ".bcfg"] = cchr_a["b300a.bcfg"]
        cmot[CODE + ".bcfg"] = cmot_a["b300a.bcfg"]
    else:
        cchr[CODE + ".bcfg"] = bcfg(cchr_a["b300a.bcfg"],
                                    {n: images(cchr[n + ".nsbca"]) for n in ("stand", "run")})
        cmot[CODE + ".bcfg"] = bcfg(cmot_a["b300a.bcfg"],
                                    {n: images(cmot[n + ".nsbca"]) for n in cmot_noms})
        if os.environ.get("ZENUS_BCFG") == "cchr":     # BANC : la moitie cchr d'Aquila seulement
            cchr[CODE + ".bcfg"] = cchr_a["b300a.bcfg"]
        if os.environ.get("ZENUS_BCFG") == "cmot":     # BANC : la moitie cmot d'Aquila seulement
            cmot[CODE + ".bcfg"] = cmot_a["b300a.bcfg"]
    clair = sum(map(len, cchr.values())) + sum(map(len, cmot.values()))
    bact, _faits = bact_zenus(a["b300a.bact"], van)
    mon = narc_ecrit({CODE + ".bact": bact,
                      CODE + ".cchr": ndspy.lz10.compress(narc_ecrit(cchr)),
                      CODE + ".cmot": ndspy.lz10.compress(narc_ecrit(cmot))})
    return mon, clair


MON_DATA = "data/prm/mon_data.gp2"
NUMERO = 308
# le nom de l'espece 900 (vide dans les cinq langues) ; balises du jeu pour
# les accents (research §14). En anglais, la chaine vide de 437 est PARTAGEE
# par ~150 especes : on ajoute une chaine en fin de pool, sans rien ecraser.
NOMS = {"de": "Zenus", "en": "Zenus", "es": "Zenus", "fr": "Z<'e>nus",
        "it": "Zenus"}


def nommer(rom):
    import gp2
    import monnames
    fid = rom.filenames.idOf(MON_DATA)
    arc = bytes(rom.files[fid])
    g = gp2.GP2(MON_DATA, donnees=arc)
    neufs = {}
    for nom_membre in g.noms:
        lg = nom_membre[len("mon_data_"):-len(".nat")]
        d = bytearray(_membre(rom, nom_membre))
        nb = struct.unpack_from("<H", d, 0)[0] & 0xFFF
        base = monnames._base_pool(bytes(d), nb)
        off = len(d) - base
        d += NOMS[lg].encode("latin-1") + b"\0"
        # +0x02 = taille du pool / 16 (vanilla : en 8 784 o -> 549) : un nom
        # ajoute au-dela n'est pas lu (visionneuse : ligne vide). Pool
        # complete a un multiple de 16, borne mise a jour.
        d += b"\0" * (-(len(d) - base) % 16)
        struct.pack_into("<H", d, 2, (len(d) - base) // 16)
        p = 4 + INDEX * monnames.STRIDE
        struct.pack_into("<I", d, p + monnames.OFF_NOM, off)
        struct.pack_into("<I", d, p + monnames.OFF_PLURIEL, off)
        # +16 : son numero dans la liste. A 0, aucune victoire comptee (« Resultats du combat » restait a 0).
        # Nokturnus : 304, le gluant : 1. Le meme que mon_list +0x1A (combat_zenus.NUMERO).
        struct.pack_into("<H", d, p + 16, NUMERO)
        neufs[nom_membre] = bytes(d)
    rom.files[fid] = gp2_ecrire.reecrire(arc, neufs)


# Les deux textes de sa fiche (joueur, 05/11 : « le tout-puissant, broder autour »). mon_trv1 : sa facon de se battre ;
# mon_trv2 : qui il est. Membre par langue : u32 (nombre d'entrees, 12 bits ; taille du pool, 20 bits), puis des paires
# u32 (numero de la liste, offset dans le pool) triees par numero, puis le pool. Le dernier numero du jeu est 307 :
# l'entree de 308 va a la fin, le tri tient. Textes du jeu : 135 caracteres au plus.
DESCRIPTIONS = {
    "mon_trv1": {
        "fr": "Il charme vos compagnons<,> se soigne enti<`e>rement et finit par r<'e>duire l<1>un d<1>eux au n<'e>ant. "
              "Ne le sous-estimez pas<!>",
        "en": "Charms your companions<,> heals himself completely and may cast one of them into the void for good. "
              "Never underestimate him!",
        "de": "Bezaubert eure Gef<:a>hrten<,> heilt sich vollst<:a>ndig und schickt einen von ihnen f<:u>r immer ins "
              "Nichts. Untersch<:a>tzt ihn nicht!",
        "es": "Hechiza a tus compa<~n>eros<,> se cura por completo y puede enviar a uno de ellos a la nada para siempre. "
              "<^!>No lo subestimes!",
        "it": "Ammalia i tuoi compagni<,> si cura completamente e pu<`o> ridurne uno al nulla per sempre. "
              "Non sottovalutarlo!",
    },
    "mon_trv2": {
        "fr": "Le Tout-Puissant en personne<,> cr<'e>ateur du ciel et de la terre. Du haut de son tr<^o>ne<,> il attend "
              "celui qui osera le d<'e>fier.",
        "en": "The Almighty himself<,> creator of heaven and earth. From his celestial throne<,> he awaits whoever dares "
              "to challenge him.",
        "de": "Der Allm<:a>chtige pers<:o>nlich<,> Sch<:o>pfer von Himmel und Erde. Auf seinem Thron erwartet er jeden<,> "
              "der ihn herauszufordern wagt.",
        "es": "El Todopoderoso en persona<,> creador del cielo y de la tierra. Desde su trono celestial aguarda a quien "
              "se atreva a desafiarlo.",
        "it": "L<1>Onnipotente in persona<,> creatore del cielo e della terra. Dal suo trono celeste attende chi "
              "oser<`a> sfidarlo.",
    },
}


def decrire(rom):
    """Ajoute l'entree de NUMERO aux deux textes de fiche, dans les cinq langues."""
    for f, textes in DESCRIPTIONS.items():
        chemin = "data/prm/%s.gp2" % f
        fid = rom.filenames.idOf(chemin)
        arc = bytes(rom.files[fid])
        neufs = {}
        for lg, texte in textes.items():
            nom = "%s_%s.nat" % (f, lg)
            d = bytes(_membre_archive_de(rom, chemin, nom))
            h = struct.unpack_from("<I", d, 0)[0]
            n, taille = h & 0xFFF, h >> 12
            base = 4 + 8 * n
            assert len(d) == base + taille, (nom, len(d), base + taille)
            dernier = struct.unpack_from("<I", d, base - 8)[0]
            assert dernier < NUMERO, (nom, dernier)
            pool = d[base:] + texte.encode("latin-1") + b"\0"
            entrees = d[4:base] + struct.pack("<II", NUMERO, taille)
            neufs[nom] = struct.pack("<I", (n + 1) | (len(pool) << 12)) + entrees + pool
        rom.files[fid] = gp2_ecrire.reecrire(arc, neufs)


def _membre_archive_de(rom, chemin, nom):
    from objets import _membre_archive
    return _membre_archive(rom, chemin, nom)


def _membre(rom, nom):
    from objets import _membre_archive
    return _membre_archive(rom, MON_DATA, nom)


def poser(rom, van=None, bavard=True):
    """Le modele de combat, sa taille declaree, le son des pas, le nom et la fiche."""
    fid = rom.filenames.idOf(K.ENEMY)
    d = bytes(rom.files[fid])
    membres = K._membres(d)
    mon, clair = mon_zenus(membres["b300a.mon"], rom, van)
    rom.files[fid] = gp2_ecrire.reecrire_index(d, {CODE + ".mon": mon})
    # taille declaree du modele (research §108) : celle des fichiers clairs
    kb = math.ceil(clair / 1024)
    fb = rom.filenames.idOf(MON_BTLDATA)
    b = bytearray(rom.files[fb])
    p = 4 + INDEX * 132
    assert struct.unpack_from("<H", b, p)[0] & 0x7FFF == 900
    struct.pack_into("<H", b, p + 0x2A, kb)
    rom.files[fb] = bytes(b)
    if PAS_SON and os.environ.get("ZENUS_SON_TITAN", "1") != "0":
        import son_pas            # le pas du Titan, archive de sons propre a Zenus (son_pas.py)
        son_pas.poser(rom)
    nommer(rom)
    decrire(rom)
    if bavard:
        print("  %s.mon : %d -> %d o ; clair %d o, declare %d Ko" % (
            CODE, len(membres[CODE + ".mon"]), len(mon), clair, kb))
    return kb


def construire(entree, sortie):
    rom = ndspy.rom.NintendoDSRom.fromFile(entree)
    poser(rom)
    rom.saveToFile(sortie)
    n, cible = os.path.getsize(sortie), os.path.getsize(entree)
    if n > cible:
        raise SystemExit("ROM plus grande que l'entree (%d > %d)" % (n, cible))
    with open(sortie, "ab") as fo:
        fo.write(b"\xff" * (cible - n))


if __name__ == "__main__":
    construire(*sys.argv[1:3])
