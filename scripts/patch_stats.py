#!/usr/bin/env python3
"""Tirer les STATISTIQUES des monstres (ZER-58, patch de la 1.7).

LE BON FICHIER. Le combat lit les stats d'un monstre dans
`data/prm/mon_moddata.nat` (research §91.1 : 600 PV ecrits la tiennent en
jeu) ; `mon_btldata.nat` porte les memes valeurs dans le jeu d'origine, et
c'est lui que lisent les especes tirees par le blob (research §94.4). Avant
ce module, `--stats` n'ecrivait que `mon_btldata` : sans effet sur les
especes d'une zone vanilla. On ecrit donc LES DEUX, identiques.

CE QUI EST TIRE (decision du joueur, 20/10/2026) : PV, PM, attaque, defense,
agilite, et les 21 resistances (7 elements, 14 alterations d'etat). Ni
l'experience, ni l'or. Des valeurs TIREES (pas un melange entre monstres),
boss compris. Deux options, comme toute regle d'equilibrage :

  borne (defaut)  chaque stat entre x0,5 et x2 de sa valeur d'origine
                  (tirage uniforme dans la plage) ;
                  une stat nulle reste nulle, des PM a 255 restent a 255 ;
                  chaque resistance bouge d'au plus UN cran parmi les valeurs
                  que le jeu utilise (une valeur hors de l'echelle, rare, ne
                  bouge pas) ;
  chaos           tirage brut sur toute la plage de la stat, sans regarder la
                  valeur d'origine : la plage des monstres du bestiaire pour
                  un monstre du bestiaire, celle des autres fiches (boss) pour
                  un boss ; chaque resistance n'importe ou sur son echelle.

JAMAIS TOUCHES (le verrou de « Creer sa ROM », levable la-bas) : les deux
especes du combat du prologue (290, 292, le heros y est seul au niveau 1),
Aquila et Corvus des cinematiques (800, 801, valeurs bouche-trou) et le
mannequin du tutoriel (900).

Le tirage a SON PROPRE generateur, derive de la graine : cocher les stats ne
change rien au reste de la ROM. Aucune taille de fichier ne bouge.
"""
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MOD = "/data/prm/mon_moddata.nat"
BTL = "/data/prm/mon_btldata.nat"
ENTETE, MOD_TAILLE, BTL_TAILLE = 4, 64, 132

STATS = ("pv", "pm", "attaque", "defense", "agilite")
# offsets u16 dans chaque fichier (l'ordre differe : mon_moddata range
# l'agilite avant l'attaque)
OFF_MOD = {"pv": 0x02, "pm": 0x04, "agilite": 0x06, "attaque": 0x08,
           "defense": 0x0A}
OFF_BTL = {"pv": 0x5C, "pm": 0x5E, "attaque": 0x60, "defense": 0x62,
           "agilite": 0x64}
# 7 elements, un octet toujours a 100, 14 alterations (24 octets avec le
# bourrage, recopies tels quels du meme bloc dans les deux fichiers)
RES_MOD, RES_BTL = 0x10, 0x6C
NB_ELEM, NB_ALT = 7, 14
OFF_ALT = NB_ELEM + 1
# 22 octets : les deux suivants de mon_btldata (+0x82/+0x83) portent les
# masques de la greffe des actions (patch_actions)
RES_TAILLE = OFF_ALT + NB_ALT

# Les plafonds du borne : un tirage ne depasse pas ces valeurs, sauf si la
# valeur d'origine les depasse deja.
PLAFOND = {"pv": 9999, "pm": 255, "attaque": 999, "defense": 999,
           "agilite": 999}
# Les echelles des resistances : les valeurs que le jeu utilise (mesure sur
# les 438 fiches : 0/50/75/100/125/150/200 pour les elements ; pour les
# alterations, 1, 30, 60, 150 et 200 n'apparaissent que 22 fois en tout et
# restent hors echelle).
ECHELLE_ELEM = (0, 50, 75, 100, 125, 150, 200)
ECHELLE_ALT = (0, 5, 10, 15, 25, 35, 50, 75, 100)

PROLOGUE = (290, 292)
CINEMATIQUES = (800, 801)
MANNEQUIN = 900
VERROUILLES = frozenset(PROLOGUE + CINEMATIQUES + (MANNEQUIN,))


def generateur(seed):
    """Le generateur des stats, independant de celui du reste."""
    return random.Random("stats:%d" % seed)


def _fid(rom, chemin):
    return rom.filenames.idOf(chemin.lstrip("/"))


def identifiants(rom):
    mod = rom.files[_fid(rom, MOD)]
    n = struct.unpack_from("<I", mod, 0)[0]
    return [struct.unpack_from("<H", mod, ENTETE + i * MOD_TAILLE)[0]
            for i in range(n)]


def verrouilles(rom):
    """Index des fiches que le randomizer ne touche jamais."""
    return frozenset(i for i, ident in enumerate(identifiants(rom))
                     if ident in VERROUILLES)


def bestiaire():
    from monstres_nommes import MONSTRES
    return frozenset(MONSTRES)


def lire(rom):
    """[{pv, pm, attaque, defense, agilite, elements[7], alterations[14]}]
    des 438 fiches, lues dans mon_moddata (celui que lit le combat)."""
    mod = rom.files[_fid(rom, MOD)]
    n = struct.unpack_from("<I", mod, 0)[0]
    out = []
    for i in range(n):
        o = ENTETE + i * MOD_TAILLE
        f = {s: struct.unpack_from("<H", mod, o + OFF_MOD[s])[0]
             for s in STATS}
        r = o + RES_MOD
        f["elements"] = list(mod[r:r + NB_ELEM])
        f["alterations"] = list(mod[r + OFF_ALT:r + OFF_ALT + NB_ALT])
        out.append(f)
    return out


def ecrire(rom, fiches):
    """Pose les fiches dans LES DEUX fichiers. Rend le nombre de fiches
    changees."""
    fm, fb = _fid(rom, MOD), _fid(rom, BTL)
    mod, btl = bytearray(rom.files[fm]), bytearray(rom.files[fb])
    avant = lire(rom)
    n = 0
    for i, f in enumerate(fiches):
        if f == avant[i]:
            continue
        n += 1
        om, ob = ENTETE + i * MOD_TAILLE, ENTETE + i * BTL_TAILLE
        for s in STATS:
            struct.pack_into("<H", mod, om + OFF_MOD[s], f[s])
            struct.pack_into("<H", btl, ob + OFF_BTL[s], f[s])
        for d, base in ((mod, om + RES_MOD), (btl, ob + RES_BTL)):
            d[base:base + NB_ELEM] = bytes(f["elements"])
            d[base + OFF_ALT:base + OFF_ALT + NB_ALT] = bytes(f["alterations"])
    rom.files[fm], rom.files[fb] = bytes(mod), bytes(btl)
    return n


def synchroniser(rom):
    """Recopie les stats, resistances, experience et or de mon_btldata dans
    mon_moddata (l'ancien chemin `--mode`, qui n'ecrit que mon_btldata)."""
    fm, fb = _fid(rom, MOD), _fid(rom, BTL)
    mod, btl = bytearray(rom.files[fm]), bytearray(rom.files[fb])
    n = struct.unpack_from("<I", mod, 0)[0]
    for i in range(n):
        om, ob = ENTETE + i * MOD_TAILLE, ENTETE + i * BTL_TAILLE
        for s in STATS:
            mod[om + OFF_MOD[s]:om + OFF_MOD[s] + 2] = \
                btl[ob + OFF_BTL[s]:ob + OFF_BTL[s] + 2]
        mod[om + RES_MOD:om + RES_MOD + RES_TAILLE] = \
            btl[ob + RES_BTL:ob + RES_BTL + RES_TAILLE]
        mod[om + 0x28:om + 0x30] = btl[ob + 0x08:ob + 0x10]   # exp, or
    rom.files[fm] = bytes(mod)


# --- le tirage ---------------------------------------------------------------
# LES PLAGES (joueur, 20/10/2026) : chaque stat d'un monstre se tire dans une
# plage [min, max], la meme que montrent la fenetre et « Creer sa ROM », ou
# le joueur peut la changer.

def plage_bornee(s, v):
    """[min, max] du tirage borne : x0,5 a x2, plafonnee ; une stat nulle et
    des PM a 255 ne bougent pas."""
    if v == 0 or (s == "pm" and v == 255):
        return v, v
    return max(1, round(v / 2)), min(max(v, PLAFOND[s]), 2 * v)


def plages_familles(fiches, garder=(), bestiaire_=None):
    """{famille: {stat: (min, max)}} des fiches tirables : True le
    bestiaire, False les autres (boss)."""
    best = bestiaire() if bestiaire_ is None else bestiaire_
    out = {}
    for fam in (True, False):
        grp = [i for i in range(len(fiches))
               if i not in garder and (i in best) == fam]
        if grp:
            out[fam] = {s: (max(min(fiches[i][s] for i in grp),
                                1 if s == "pv" else 0),
                            max(fiches[i][s] for i in grp)) for s in STATS}
    return out


def plages(fiches, chaos=False, garder=(), bestiaire_=None):
    """[{stat: (min, max)}] par fiche (None pour une fiche gardee)."""
    best = bestiaire() if bestiaire_ is None else bestiaire_
    fam = plages_familles(fiches, garder, best) if chaos else None
    out = []
    for i, f in enumerate(fiches):
        if i in garder:
            out.append(None)
        elif chaos:
            out.append(dict(fam[i in best]))
        else:
            out.append({s: plage_bornee(s, f[s]) for s in STATS})
    return out


def tirer_dans(rng, plage):
    """Une valeur par stat, dans l'ordre de STATS."""
    return {s: rng.randint(plage[s][0], plage[s][1]) for s in STATS}


def _cran(rng, echelle, v):
    if v not in echelle:
        return v
    k = echelle.index(v) + rng.randint(-1, 1)
    return echelle[max(0, min(len(echelle) - 1, k))]


def tirer(fiches, rng, chaos=False, garder=(), bestiaire_=None):
    """Rend de nouvelles fiches. `garder` : index jamais tires. En chaos, la
    plage d'une stat se calcule sur les fiches tirables de la meme famille
    (bestiaire / autres)."""
    pl = plages(fiches, chaos, garder, bestiaire_)
    out = [dict(f, elements=list(f["elements"]),
                alterations=list(f["alterations"])) for f in fiches]
    for i in range(len(fiches)):
        if pl[i] is None:
            continue
        f = out[i]
        f.update(tirer_dans(rng, pl[i]))
        if chaos:
            f["elements"] = [rng.choice(ECHELLE_ELEM) for _ in range(NB_ELEM)]
            f["alterations"] = [rng.choice(ECHELLE_ALT) for _ in range(NB_ALT)]
        else:
            f["elements"] = [_cran(rng, ECHELLE_ELEM, v) for v in f["elements"]]
            f["alterations"] = [_cran(rng, ECHELLE_ALT, v)
                                for v in f["alterations"]]
    return out


MONSTRES, BOSS = True, False        # les familles (bestiaire / les autres)


def hors_familles(n, familles):
    """Index des fiches qui ne sont dans aucune des `familles` demandees."""
    best = bestiaire()
    return frozenset(i for i in range(n) if (i in best) not in familles)


def patcher(rom, seed, chaos=False, journal=None, noms=None,
            familles=(MONSTRES, BOSS)):
    """Tire et ecrit. `familles` : les monstres du bestiaire, les boss (les
    autres fiches), ou les deux (deux options du lanceur, joueur
    20/10/2026). Rend le nombre de fiches changees."""
    avant = lire(rom)
    garder = verrouilles(rom) | hors_familles(len(avant), familles)
    apres = tirer(avant, generateur(seed), chaos=chaos, garder=garder)
    n = ecrire(rom, apres)
    if journal is not None:
        journal.write("=" * 78 + "\n")
        journal.write("STATISTIQUES DES %s (%s, ZER-58)\n"
                      % ("MONSTRES ET DES BOSS" if len(familles) == 2
                         else "MONSTRES" if MONSTRES in familles else "BOSS",
                         "chaos" if chaos else "x0,5 a x2"))
        journal.write("=" * 78 + "\n")
        journal.write("  idx  %-26s %13s %9s %9s %9s %9s\n"
                      % ("monstre", "PV", "PM", "ATT", "DEF", "AGI"))
        for i, (a, b) in enumerate(zip(avant, apres)):
            if a == b:
                continue
            nom = (noms or {}).get(i, "") or "#%d" % i
            journal.write("  %3d  %-26s" % (i, nom[:26])
                          + "".join(" %4d->%-4d" % (a[s], b[s])
                                    for s in STATS) + "\n")
        journal.write("\n")
    return n


# --- a chaque combat (ZER-96) --------------------------------------------------
# LE TIRAGE A CHAQUE COMBAT (joueur, 20/10/2026) : PV, PM, attaque, defense et
# agilite d'une espece se retirent dans sa plage au debut de chaque combat.
#
# LES PLAGES vivent dans la fiche `mon_btldata` : `+0x2C + 4k` le min, `+0x2E
# + 4k` le max, k = 0..4 dans l'ordre de STATS (celui des stats en +0x5C..).
# Ces 48 octets (+0x2C..+0x5B) sont a zero dans les 438 fiches d'origine, et
# le combat recopie la fiche entiere (0x84 o) dans sa copie : la greffe y lit
# les plages. Un max de PV nul = espece non tiree.
#
# PAS DE PLACE A PRENDRE DANS L'OVERLAY 0 : on REDIRIGE deux appels qui y
# sont deja, vers trois fragments libres de l'ARM9 (bourrage verifie par
# canari, liberes par l'abandon de la rotation et de la greffe C) :
#   0x02165B8C  `bl memcpy` des resistances, especes de la zone, apres la
#               recopie de leurs stats depuis mon_moddata -> CROCHET_ZONE ;
#   0x02165A30  `bl 0x02012FF4` (ou la greffe des actions, qui y est deja),
#               apres la construction de la copie de combat : toutes les
#               especes presentes, celles du blob comprises -> CROCHET_TOUTES,
#               qui rend la main a la cible d'avant.
# Les resistances ne se retirent pas a chaque combat (pas de place) : elles
# restent celles de la construction.
TIRER_COMBAT = 0x020F1E40          # 72 o (ROT_B)
CROCHET_TOUTES = 0x020E8888        # 40 o (GREFFE_C3)
CROCHET_SUITE = 0x020E7C78         # 40 o (GREFFE_C2) : fin du precedent,
CROCHET_ZONE = 0x020E7C78 + 8      #   puis le crochet des especes de la zone
PLACES_COMBAT = ((TIRER_COMBAT, 72), (CROCHET_TOUTES, 40), (CROCHET_SUITE, 40))
OVL_COMBAT = 0
SITE_ZONE = 0x02165B8C
SITE_TOUTES = 0x02165A30
MEMCPY = 0x02001A40
RAND_BELOW = 0x02032380            # r0 = [0, r0[ (patch_butin, patch_actions)
PLAGES_BTL = 0x2C


def _code_tirer():
    """r0 = une fiche de la copie de combat ; preserve r4-r11."""
    from patch_hasard import assembler
    a = TIRER_COMBAT
    boucle = a + 7 * 4
    return assembler([
        "push {r4, r5, r6, r7, r8, lr}",        # pair : pile alignee a 8
        "ldrh r1, [r0, #%#x]" % (PLAGES_BTL + 2),
        "cmp r1, #0",
        "popeq {r4, r5, r6, r7, r8, pc}",
        "add r4, r0, #%#x" % OFF_BTL["pv"],
        "add r5, r0, #%#x" % PLAGES_BTL,
        "mov r6, #%d" % len(STATS),
        "ldrh r7, [r5], #2",                    # boucle : min
        "ldrh r0, [r5], #2",                    # max
        "sub r0, r0, r7",
        "add r0, r0, #1",
        "bl #%d" % RAND_BELOW,
        "add r0, r0, r7",
        "strh r0, [r4], #2",
        "subs r6, r6, #1",
        "bne #%d" % boucle,
        "pop {r4, r5, r6, r7, r8, pc}",
    ], a)


def _code_toutes(cible):
    """Au site 0x02165A30 : r5 = la structure du combat ; [r5+0x400] le
    compte (12 bits bas), [r5+0x404] les fiches (0x84 o). Puis `cible`."""
    from patch_hasard import assembler
    a = CROCHET_TOUTES
    boucle = a + 4 * 4
    part1 = assembler([
        "push {r0, r1, r2, r3, r4, r6, r7, lr}",   # pair : pile alignee
        "ldr r6, [r5, #0x404]",
        "ldr r4, [r5, #0x400]",
        "lsls r4, r4, #20",
        "beq #%d" % CROCHET_SUITE,              # boucle
        "mov r0, r6",
        "bl #%d" % TIRER_COMBAT,
        "add r6, r6, #0x84",
        "subs r4, r4, #0x100000",
        "b #%d" % boucle,
    ], a)
    part2 = assembler([
        "pop {r0, r1, r2, r3, r4, r6, r7, lr}",
        "b #%d" % cible,
    ], CROCHET_SUITE)
    return part1, part2


def _code_zone():
    """Au site 0x02165B8C : la recopie des resistances, puis le tirage de
    la fiche r4 (registre de l'appelant)."""
    from patch_hasard import assembler
    return assembler([
        "push {r0, lr}",                        # pair : pile alignee
        "bl #%d" % MEMCPY,
        "mov r0, r4",
        "pop {r1, lr}",
        "b #%d" % TIRER_COMBAT,
    ], CROCHET_ZONE)


def _cible_bl(mot, adr):
    """La cible d'un `bl` (mot ARM) pose a `adr`."""
    off = mot & 0xFFFFFF
    if off & 0x800000:
        off -= 0x1000000
    return adr + 8 + 4 * off


def ecrire_plages(rom, plages_):
    """Pose les plages dans mon_btldata (+0x2C) ; None = pas de tirage a
    chaque combat (zeros)."""
    fb = _fid(rom, BTL)
    btl = bytearray(rom.files[fb])
    for i, pl in enumerate(plages_):
        o = ENTETE + i * BTL_TAILLE + PLAGES_BTL
        if pl is None:
            btl[o:o + 4 * len(STATS)] = bytes(4 * len(STATS))
            continue
        for k, s in enumerate(STATS):
            lo, hi = pl[s]
            if not 0 <= lo <= hi <= 0xFFFF or (s == "pv" and lo < 1):
                raise ValueError("fiche %d : plage %s %r" % (i, s, (lo, hi)))
            struct.pack_into("<HH", btl, o + 4 * k, lo, hi)
    rom.files[fb] = bytes(btl)


def lire_plages(rom):
    """[{stat: (min, max)} ou None] lues dans mon_btldata."""
    btl = rom.files[_fid(rom, BTL)]
    n = struct.unpack_from("<I", btl, 0)[0]
    out = []
    for i in range(n):
        o = ENTETE + i * BTL_TAILLE + PLAGES_BTL
        v = struct.unpack_from("<%dH" % (2 * len(STATS)), btl, o)
        out.append({s: (v[2 * k], v[2 * k + 1]) for k, s in enumerate(STATS)}
                   if v[1] else None)
    return out


def cible_toutes(rom):
    """La cible a laquelle le crochet de 0x02165A30 rend la main, ou None si
    la greffe n'est pas posee."""
    import ndspy.codeCompression as cc
    if not combat_pose(rom):
        return None
    arm9 = cc.decompress(bytes(rom.arm9))
    o9 = CROCHET_SUITE + 4 - 0x02000000
    return _cible_bl(struct.unpack_from("<I", arm9, o9)[0], CROCHET_SUITE + 4)


def combat_pose(rom):
    """La greffe du tirage a chaque combat est-elle posee ?"""
    o = rom.loadArm9Overlays()[OVL_COMBAT]
    k = SITE_ZONE - o.ramAddress
    mot = struct.unpack_from("<I", o.data, k)[0]
    return _cible_bl(mot, SITE_ZONE) == CROCHET_ZONE


def poser_combat(rom):
    """Pose la greffe (idempotent). A appeler APRES la greffe des actions :
    le crochet de 0x02165A30 rend la main a ce qui y etait."""
    import ndspy.code
    import ndspy.codeCompression as cc
    from patch_hasard import assembler, COMPRESSED_END
    if combat_pose(rom):
        retirer_combat(rom)
    ovl = rom.loadArm9Overlays()
    o = ovl[OVL_COMBAT]
    d = bytearray(o.data)
    kz, kt = SITE_ZONE - o.ramAddress, SITE_TOUTES - o.ramAddress
    mz = struct.unpack_from("<I", d, kz)[0]
    mt = struct.unpack_from("<I", d, kt)[0]
    if _cible_bl(mz, SITE_ZONE) != MEMCPY or (mz >> 24) != 0xEB:
        raise SystemExit("stats a chaque combat : 0x%08X n'est pas bl memcpy"
                         % SITE_ZONE)
    if (mt >> 24) != 0xEB:
        raise SystemExit("stats a chaque combat : 0x%08X n'est pas un bl"
                         % SITE_TOUTES)
    cible = _cible_bl(mt, SITE_TOUTES)
    arm9 = bytearray(cc.decompress(bytes(rom.arm9)))
    for adr, n in PLACES_COMBAT:
        if any(arm9[adr - 0x02000000:adr - 0x02000000 + n]):
            raise SystemExit("stats a chaque combat : la place 0x%08X n'est "
                             "pas vierge (--portier sans blob ?)" % adr)
    t1, t2 = _code_toutes(cible)
    for adr, code in ((TIRER_COMBAT, _code_tirer()), (CROCHET_TOUTES, t1),
                      (CROCHET_SUITE, t2), (CROCHET_ZONE, _code_zone())):
        arm9[adr - 0x02000000:adr - 0x02000000 + len(code)] = code
    assert len(_code_tirer()) <= 72 and len(t1) <= 40
    assert CROCHET_ZONE + len(_code_zone()) <= CROCHET_SUITE + 40
    struct.pack_into("<I", arm9, COMPRESSED_END, 0)
    rom.arm9 = bytes(arm9)
    d[kz:kz + 4] = assembler(["bl #%d" % CROCHET_ZONE], SITE_ZONE)
    d[kt:kt + 4] = assembler(["bl #%d" % CROCHET_TOUTES], SITE_TOUTES)
    o.data = bytes(d)
    rom.files[o.fileID] = o.save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)


def retirer_combat(rom):
    """Defait poser_combat : les deux sites reprennent leur cible d'avant,
    les fragments de l'ARM9 redeviennent vierges."""
    import ndspy.code
    import ndspy.codeCompression as cc
    from patch_hasard import assembler, COMPRESSED_END
    if not combat_pose(rom):
        return
    arm9 = bytearray(cc.decompress(bytes(rom.arm9)))
    o9 = CROCHET_SUITE + 4 - 0x02000000            # le `b cible`
    cible = _cible_bl(struct.unpack_from("<I", arm9, o9)[0], CROCHET_SUITE + 4)
    for adr, n in PLACES_COMBAT:
        arm9[adr - 0x02000000:adr - 0x02000000 + n] = bytes(n)
    struct.pack_into("<I", arm9, COMPRESSED_END, 0)
    rom.arm9 = bytes(arm9)
    ovl = rom.loadArm9Overlays()
    o = ovl[OVL_COMBAT]
    d = bytearray(o.data)
    kz, kt = SITE_ZONE - o.ramAddress, SITE_TOUTES - o.ramAddress
    d[kz:kz + 4] = assembler(["bl #%d" % MEMCPY], SITE_ZONE)
    d[kt:kt + 4] = assembler(["bl #%d" % cible], SITE_TOUTES)
    o.data = bytes(d)
    rom.files[o.fileID] = o.save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)


def patcher_combat(rom, seed=None, chaos=False, familles=(MONSTRES, BOSS)):
    """--stats-combat : les fiches tirables des `familles` recoivent leur
    plage (bornee, ou de leur famille en chaos), celles des autres gardent
    la leur, et la greffe est posee."""
    import ndspy.rom
    from rom_vanilla import chemin_vanilla
    fiches = lire(ndspy.rom.NintendoDSRom.fromFile(chemin_vanilla()))
    hors = hors_familles(len(fiches), familles)
    neuves = plages(fiches, chaos, verrouilles(rom) | hors)
    deja = lire_plages(rom)
    ecrire_plages(rom, [deja[i] if i in hors else neuves[i]
                        for i in range(len(fiches))])
    poser_combat(rom)
    return sum(1 for p in lire_plages(rom) if p)


def verifier(rom, vanilla=None):
    """Les deux fichiers d'accord sur les stats et les resistances ; l'octet
    constant a 100 ; avec la vanilla, les fiches verrouillees intactes."""
    mod = rom.files[_fid(rom, MOD)]
    btl = rom.files[_fid(rom, BTL)]
    n = struct.unpack_from("<I", mod, 0)[0]
    for i in range(n):
        om, ob = ENTETE + i * MOD_TAILLE, ENTETE + i * BTL_TAILLE
        for s in STATS:
            a = struct.unpack_from("<H", mod, om + OFF_MOD[s])[0]
            b = struct.unpack_from("<H", btl, ob + OFF_BTL[s])[0]
            if a != b:
                raise AssertionError("fiche %d : %s %d (moddata) / %d "
                                     "(btldata)" % (i, s, a, b))
        if (mod[om + RES_MOD:om + RES_MOD + RES_TAILLE]
                != btl[ob + RES_BTL:ob + RES_BTL + RES_TAILLE]):
            raise AssertionError("fiche %d : resistances differentes entre "
                                 "les deux fichiers" % i)
        if mod[om + RES_MOD + NB_ELEM] != 100:
            raise AssertionError("fiche %d : octet constant != 100" % i)
    if vanilla is not None:
        av, ap = lire(vanilla), lire(rom)
        for i in verrouilles(rom):
            if av[i] != ap[i]:
                raise AssertionError("fiche verrouillee %d modifiee" % i)
    # A CHAQUE COMBAT (ZER-96) : la greffe posee si et seulement si une
    # fiche porte une plage ; des plages valides.
    pl = lire_plages(rom)
    if any(pl) != combat_pose(rom):
        raise AssertionError("stats a chaque combat : %d plages, greffe %s"
                             % (sum(1 for p in pl if p),
                                "posee" if combat_pose(rom) else "absente"))
    for i, p in enumerate(pl):
        if p and any(not lo <= hi for lo, hi in p.values()):
            raise AssertionError("fiche %d : plage %r" % (i, p))
        if p and p["pv"][0] < 1:
            raise AssertionError("fiche %d : PV min nul" % i)
    if vanilla is not None:
        for i in verrouilles(rom):
            if pl[i]:
                raise AssertionError("fiche verrouillee %d tiree a chaque "
                                     "combat" % i)
    return True


if __name__ == "__main__":
    # python scripts/patch_stats.py <rom.nds>  : verifie et resume
    import ndspy.rom
    from rom_vanilla import chemin_vanilla
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    van = ndspy.rom.NintendoDSRom.fromFile(chemin_vanilla())
    verifier(rom, van)
    av, ap = lire(van), lire(rom)
    diff = [i for i in range(len(av)) if av[i] != ap[i]]
    print("deux fichiers d'accord ; %d fiche(s) differente(s) du vanilla"
          % len(diff))
    for i in diff[:12]:
        print("  %3d " % i + " ".join("%s %d->%d" % (s, av[i][s], ap[i][s])
                                      for s in STATS))
